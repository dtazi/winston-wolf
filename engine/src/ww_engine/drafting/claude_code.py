"""v1 Drafter: headless Claude Code on the subscription (research R4).

Shells out to `claude -p <prompt> --output-format json`, parses the assistant
text + token usage. No Anthropic API key. Behind the FR-015 seam — swappable.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from .base import (
    DraftError,
    DrafterCapReached,
    DraftRequest,
    DraftResult,
    violates_named_account_guard,
)

_CAP_SIGNALS = (
    "usage limit", "rate limit", "rate_limit", "usage_limit",
    "claude usage limit reached", "overloaded",
)


def _build_prompt(req: DraftRequest) -> str:
    facts = "\n".join(f"- {f}" for f in req.personalization.get("facts", [])) \
        or "- (no specific personalization available; keep the opening generic and recipient-first)"
    audience = (req.lead.get("audience") or "direct_buyer").lower()
    cta_block = (
        "CTA: invite them to visit the Richbond factory in Morocco "
        "(GPO/large operators audit suppliers; this is appropriate for them)."
        if audience == "gpo"
        else
        "CTA: offer to ship a sample to their facilities team, no call required."
    )
    spotlight = {
        "china_plus_one":
            "the China-alternative frame — supply-chain certainty after a "
            "decade of disruption, tariff exposure, lead-time volatility.",
        "60_years_experience":
            "Richbond's 60 years of institutional manufacturing and "
            "established credibility as a European-market alternative.",
        "trusted_by_heavyweights":
            "trusted-by-heavyweights credibility (unnamed) + the Morocco-US "
            "Free Trade Agreement / TAA-compliance closer.",
    }.get(req.value_angle, req.value_angle)
    subject_tone = (
        "specific and procurement-relevant (e.g., 'X for Y member contracts')"
        if audience == "gpo"
        else
        "oblique and recipient-relevant — never blunt frames like "
        "'China-alternative source' in the subject; lead with the recipient's "
        "situation instead"
    )
    return f"""You write one short B2B cold outreach email for Richbond, a \
60-year-old Moroccan institutional mattress/bedding manufacturer. Touch \
{req.touch_number} of 3.

PITCH TEMPLATE (every email must hit all of these):
  1. Subject + opening: personalized to the recipient using the lead context
     below. Subject tone is {subject_tone}. The opening is recipient-first
     ("We thought X would want to know"), never about us first.
  2. Credibility stack: 60-year-old company; you MAY name Simmons Beautyrest
     and Silentnight as brands Richbond has been trusted by (phrase as
     "trusted by brands such as Simmons Beautyrest and Silentnight" or
     similar). These are the ONLY two brand names permitted — every other
     named customer / partner / retailer is prohibited (no IKEA, no named
     hotel chains, no named hospitals). Also mention Richbond is a credible
     alternative for European institutions.
  3. China-alternative frame for buyers who have felt the past decade of
     supply-chain disruption (tariffs, lead-times, geopolitics).
  4. Soft intent: "make first contact" — never a hard pitch.
  5. {cta_block}
  6. Closer: collaboration is commercially clean — Morocco-US FTA in force,
     TAA-compliant origin.

SPOTLIGHT FOR THIS TOUCH (give this the most weight, ~40% of the body):
  {spotlight}

LEAD CONTEXT (use these facts; do not invent any):
{facts}

PITCH JSON: {json.dumps(req.pitch)[:1500]}
BRIEF JSON: {json.dumps(req.brief_excerpt)[:800]}

RULES:
- Plain text, 120-150 words MAXIMUM — be disciplined; do not pad.
- Sign every email exactly as:
    Djaafar Tazi
    Richbond Export
- NEVER name any reference customer/partner/retailer other than Simmons
  Beautyrest and Silentnight (the only two permitted names).
- Subject line is short, specific to the recipient, no clickbait.

Return STRICT JSON only: {{"subject": "...", "body": "..."}}"""


def _extract_json_obj(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise DraftError("drafter returned no JSON object")
    return json.loads(text[start : end + 1])


class ClaudeCodeDrafter:
    model = "claude-code:subscription"

    def __init__(self, claude_bin: str = "claude", timeout: int = 180) -> None:
        self._bin = claude_bin
        self._timeout = timeout

    def draft(self, req: DraftRequest) -> DraftResult:
        prompt = _build_prompt(req)
        try:
            proc = subprocess.run(
                [self._bin, "-p", prompt, "--output-format", "json"],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except FileNotFoundError as exc:
            raise DraftError(f"claude CLI not found: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise DraftError("claude CLI timed out") from exc

        blob = (proc.stdout or "") + " " + (proc.stderr or "")
        if proc.returncode != 0:
            if any(s in blob.lower() for s in _CAP_SIGNALS):
                raise DrafterCapReached(blob.strip()[:200])
            raise DraftError(f"claude exited {proc.returncode}: {blob[:200]}")

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise DraftError(f"claude JSON parse failed: {exc}") from exc

        if envelope.get("is_error") or envelope.get("subtype") in (
            "error_max_turns", "error_during_execution",
        ):
            if any(s in blob.lower() for s in _CAP_SIGNALS):
                raise DrafterCapReached(blob.strip()[:200])
            raise DraftError(f"claude error result: {str(envelope)[:200]}")

        result_text = envelope.get("result") or envelope.get("text") or ""
        obj = _extract_json_obj(result_text)
        subject = (obj.get("subject") or "").strip()
        body = (obj.get("body") or "").strip()
        if not subject or not body:
            raise DraftError("drafter produced empty subject/body")
        if violates_named_account_guard(subject + " " + body):
            raise DraftError("named-account guard tripped (FR-013)")

        usage = envelope.get("usage", {}) or {}
        token_usage = [{
            "stage": "drafting",
            "model": self.model,
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
        }]
        recipe = {
            "angle": req.value_angle,
            "touch": req.touch_number,
            "personalization_level": req.personalization.get("level", "thin"),
            "drafter": self.model,
        }
        return DraftResult(subject, body, recipe, token_usage)

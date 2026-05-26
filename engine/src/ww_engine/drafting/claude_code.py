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
    # CTA anchored in Josh Braun's cold-email research: the worst-performing
    # asks are time-commitment requests; the best are low-friction yes/no
    # interest gauges or asset offers. NEVER offer a physical mattress sample
    # (institutional mattresses are too large/expensive to ship as
    # speculative samples).
    cta_block = (
        "CTA: a soft yes/no interest gauge that opens the door to a "
        "factory audit when their next supplier-qualification cycle starts. "
        "Use phrasing like 'Worth being on the bidders list for the next "
        "furnishings re-bid?' or 'Open to an introductory technical brief "
        "by email — no call needed?'. Do NOT ask for a meeting time. Do "
        "NOT offer to ship a physical mattress."
        if audience == "gpo"
        else
        "CTA: a low-friction asset-offer in the Josh Braun style. Offer to "
        "send a one-page institutional capability brief (or a short factory "
        "tour link) BY EMAIL, no call required, framed as a yes/no interest "
        "gauge: 'Worth a one-pager by email?' or 'Open to a 2-minute factory "
        "tour link?'. Do NOT ask for a meeting time. Do NOT offer to ship "
        "a physical mattress (institutional mattresses are too large/"
        "expensive to ship speculatively)."
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
    # Subject style anchored in 2025 B2B cold-email research (Jason Bay /
    # Outbound Squad: "internal camouflage", <5 words, you-centric;
    # Belkins/Amplemarket 2025 data: 2-4 word subjects ~46% open rate;
    # avoid marketing jargon and "ASAP"/urgency tones).
    subject_tone = (
        "3-5 words, peer-to-peer tone (as if a colleague at MHEC/E&I wrote "
        "to another), refer to the recipient's procurement world not our "
        "product (good: 'supplier qualification thoughts', 'on Midwest "
        "sourcing'; bad: 'A China-alternative source for...')"
        if audience == "gpo"
        else
        "3-5 words AFTER the [Richbond] tag, peer-to-peer internal tone — "
        "as if a colleague in the recipient's own housing office wrote it. "
        "Refer to THEIR situation/topic, not our product. NO marketing "
        "language. Good: 'on your refresh cycle', 'dorm sourcing question', "
        "'a thought for fall'. Bad: 'Bedding refresh planning at...', "
        "'A China-alternative source...'"
    )
    return f"""You write one short B2B cold outreach email for Richbond, a \
60-year-old Moroccan institutional mattress/bedding manufacturer. Touch \
{req.touch_number} of 3.

PITCH TEMPLATE (every email must hit all of these):
  1. Subject + opening: personalized to the recipient using the lead context
     below. Subject tone is {subject_tone}. The opening is recipient-first
     ("We thought X would want to know"), never about us first.
  2. Credibility stack: 60-year-old institutional manufacturer. State
     Richbond's actual brand operations: "manufactures Simmons and
     Beautyrest in Morocco and operates Silentnight in Kenya" (or a close
     variant — these are owned/operated brand businesses, NOT customers
     who "trusted" us; the ownership framing is materially stronger and
     also legally accurate). Simmons, Beautyrest, and Silentnight are the
     ONLY three brand names permitted in any email; all other named
     customers/partners/retailers/competitors are prohibited (no IKEA, no
     named hotel chains, no named hospitals). Also mention Richbond is a
     credible alternative for European institutions.
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
- Sign every email exactly as (the URL is mandatory — recipients verify
  the company by clicking through, and the click is also our engagement
  signal):
    Djaafar Tazi
    Richbond Export
    https://richbondgroup.eu
- NEVER name any reference customer/partner/retailer/competitor other
  than Simmons, Beautyrest, and Silentnight (the only THREE permitted
  brand names — these are Richbond's owned/operated brand operations,
  not customers).
- Subject line is short, specific to the recipient, no clickbait.
- Subject MUST end with the subtle marker " · Richbond" (space, middle
  dot U+00B7, space, "Richbond" — no brackets, no quotes). This is a
  signature-style suffix that survives "Re:" cleanly and lets the operator
  recognise replies in their inbox without screaming "mass mail". Example:
  "a thought for your refresh cycle · Richbond".

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

"""KB-grounded drafter for the proof-of-life experiment (D6, contracts/drafter.md).

Unlike the 002 `ClaudeCodeDrafter` (a hardcoded Richbond pitch), this drafter is
driven entirely by operator-maintained inputs: the knowledge base (the only
authorized facts/offers, Article 17), the strategy library (it chooses 1+,
grounded in the research), the per-prospect research, the conclusions log, and
recent feedback. It emits the email AND a strategy/reasoning note so the operator
approves the judgment, not just the prose.

Behind the same Drafter Protocol seam — swappable for an API drafter later.
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
    strategies = "\n\n".join(
        f"### {s['name']}\n{s['text']}" for s in req.strategies
    ) or "(no strategy library provided — keep the email short and recipient-first)"
    research = json.dumps(req.research)[:2500] if req.research else "(none)"
    kb = req.knowledge_base.strip() or "(no knowledge base provided)"
    conclusions = req.conclusions.strip() or "(none yet)"
    feedback = "\n".join(f"- {c}" for c in req.feedback[:15]) or "(none yet)"
    tier_note = (
        f"\nThis is a FOLLOW-UP. Engagement so far: {req.engagement_tier}. "
        "Shape the angle accordingly (clicked → more direct; opened → light "
        "nudge; silent → a different angle). Reference nothing they did — the "
        "signal only guides your approach."
        if req.touch_number > 1 else ""
    )
    return f"""You write ONE short B2B cold outreach email, touch \
{req.touch_number}.{tier_note}

KNOWLEDGE BASE — the ONLY facts, capabilities, prices, and offers you are \
authorized to state. Every factual claim or offer in the email MUST be grounded \
here. Do NOT invent lead times, certifications, discounts, free samples, or any \
commitment that is not below:
{kb}

STRATEGY LIBRARY — choose one or more and ground the choice in the research:
{strategies}

PROSPECT RESEARCH:
{research}

WHAT'S WORKING (conclusions so far):
{conclusions}

RECENT OPERATOR FEEDBACK (apply these lessons):
{feedback}

Return STRICT JSON only:
{{
  "subject": "...",
  "body": "...",
  "reasoning": {{
    "strategies": ["names you chose"],
    "why": "why these strategies for THIS prospect, tied to the research",
    "how_applied": "how you applied them in the email",
    "claims": [
      {{"text": "each factual claim/offer you made",
        "source": "the KB anchor it came from, or null",
        "grounded": true}}
    ]
  }}
}}
Any claim you cannot source from the knowledge base MUST be marked \
"grounded": false with "source": null — do not present it as fact."""


def _extract_json_obj(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise DraftError("drafter returned no JSON object")
    return json.loads(text[start:end + 1])


class GroundedClaudeDrafter:
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

        obj = _extract_json_obj(envelope.get("result") or envelope.get("text") or "")
        return self._to_result(req, obj, envelope.get("usage", {}) or {})

    def _to_result(self, req: DraftRequest, obj: dict[str, Any],
                   usage: dict[str, Any]) -> DraftResult:
        subject = (obj.get("subject") or "").strip()
        body = (obj.get("body") or "").strip()
        if not subject or not body:
            raise DraftError("drafter produced empty subject/body")
        if violates_named_account_guard(subject + " " + body):
            raise DraftError("named-account guard tripped (FR-013)")

        reasoning = obj.get("reasoning") or {}
        recipe = {
            "strategies": reasoning.get("strategies", []),
            "why": reasoning.get("why", ""),
            "how_applied": reasoning.get("how_applied", ""),
            "claims": reasoning.get("claims", []),
            "engagement_tier": req.engagement_tier or None,
            "touch": req.touch_number,
            "drafter": self.model,
        }
        token_usage = [{
            "stage": "drafting", "model": self.model,
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
        }]
        return DraftResult(subject, body, recipe, token_usage)

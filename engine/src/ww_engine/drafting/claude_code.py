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
        or "- (no specific personalization available; keep the opening generic)"
    return f"""You write one short B2B cold outreach email for Richbond, a \
Moroccan institutional mattress/bedding manufacturer. Touch \
{req.touch_number} of 3.

VALUE ANGLE to lead with (use ONLY this angle): {req.value_angle}

Lead context:
{facts}

Pitch (offer): {json.dumps(req.pitch)[:1500]}
Audience note: {json.dumps(req.brief_excerpt)[:800]}

Rules:
- Plain text, < 130 words, professional industrialist tone.
- Personalized opening from the lead context above; never invent facts.
- Express exactly the value angle "{req.value_angle}".
- NEVER name or hint at any specific Richbond customer or reference account.
- One soft CTA (sample + short call).

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

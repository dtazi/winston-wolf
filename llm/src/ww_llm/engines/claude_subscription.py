"""Default engine: headless Claude Code on the user's subscription.

Shells out to `claude -p <prompt> --output-format json` and parses the assistant
text + token usage — the same pattern as ww-engine's ClaudeCodeDrafter. No API
key, so cost_usd is None (the subscription is flat-rate).
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from ..base import CompletionRequest, CompletionResult, EngineError, Usage

_CAP_SIGNALS = (
    "usage limit", "rate limit", "rate_limit", "usage_limit",
    "claude usage limit reached", "overloaded",
)


def _extract_json_obj(text: str) -> dict[str, Any] | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


class ClaudeSubscriptionEngine:
    def __init__(self, name: str = "claude_subscription",
                 claude_bin: str = "claude", timeout: int = 180) -> None:
        self.name = name
        self._bin = claude_bin
        self._timeout = timeout

    def complete(self, req: CompletionRequest) -> CompletionResult:
        prompt = req.prompt
        if req.system:
            prompt = f"{req.system}\n\n{prompt}"
        if req.response_schema is not None:
            prompt += "\n\nReturn STRICT JSON only, matching the requested shape."

        try:
            proc = subprocess.run(
                [self._bin, "-p", prompt, "--output-format", "json"],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except FileNotFoundError as exc:
            raise EngineError(f"claude CLI not found: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise EngineError("claude CLI timed out") from exc

        blob = f"{proc.stdout or ''} {proc.stderr or ''}".lower()
        if proc.returncode != 0:
            raise EngineError(f"claude exited {proc.returncode}: {blob[:200]}")

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise EngineError(f"claude JSON parse failed: {exc}") from exc

        if envelope.get("is_error") or envelope.get("subtype") in (
            "error_max_turns", "error_during_execution",
        ):
            raise EngineError(f"claude error result: {str(envelope)[:200]}")

        text = (envelope.get("result") or envelope.get("text") or "").strip()
        if not text:
            raise EngineError("claude produced empty result")

        parsed = _extract_json_obj(text) if req.response_schema is not None else None
        if req.response_schema is not None and parsed is None:
            raise EngineError("expected JSON result but none could be parsed")

        u = envelope.get("usage", {}) or {}
        usage = Usage(
            tokens_in=int(u.get("input_tokens", 0) or 0),
            tokens_out=int(u.get("output_tokens", 0) or 0),
            cost_usd=None,
        )
        return CompletionResult(text=text, usage=usage, engine=self.name, json=parsed)

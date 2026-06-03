"""Anthropic Messages API engine (opt-in, pay-per-use)."""

from __future__ import annotations

import json

import httpx

from ..base import CompletionRequest, CompletionResult, EngineError, Usage

_URL = "https://api.anthropic.com/v1/messages"
_DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicAPIEngine:
    def __init__(self, name: str, api_key: str, model: str | None = None,
                 timeout: float = 60.0) -> None:
        self.name = name
        self._key = api_key
        self._model = model or _DEFAULT_MODEL
        self._timeout = timeout

    def complete(self, req: CompletionRequest) -> CompletionResult:
        body: dict = {
            "model": self._model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if req.system:
            body["system"] = req.system
        try:
            resp = httpx.post(
                _URL, json=body, timeout=self._timeout,
                headers={
                    "x-api-key": self._key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EngineError(f"anthropic_api call failed: {exc}") from exc

        data = resp.json()
        parts = data.get("content") or []
        text = "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
        if not text:
            raise EngineError("anthropic_api returned empty content")
        u = data.get("usage", {}) or {}
        usage = Usage(
            tokens_in=int(u.get("input_tokens", 0) or 0),
            tokens_out=int(u.get("output_tokens", 0) or 0),
        )
        parsed = _maybe_json(text) if req.response_schema is not None else None
        if req.response_schema is not None and parsed is None:
            raise EngineError("anthropic_api: expected JSON, none parsed")
        return CompletionResult(text=text, usage=usage, engine=self.name, json=parsed)


def _maybe_json(text: str) -> dict | None:
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None

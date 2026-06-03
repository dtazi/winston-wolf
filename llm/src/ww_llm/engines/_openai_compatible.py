"""Shared base for OpenAI-compatible chat APIs (OpenAI, DeepSeek, …).

Both expose POST /chat/completions with the same request/response shape; only
the base URL, default model, and auth header value differ.
"""

from __future__ import annotations

import json

import httpx

from ..base import CompletionRequest, CompletionResult, EngineError, Usage


class OpenAICompatibleEngine:
    base_url: str = ""        # subclasses set
    default_model: str = ""   # subclasses set

    def __init__(self, name: str, api_key: str, model: str | None = None,
                 timeout: float = 60.0) -> None:
        self.name = name
        self._key = api_key
        self._model = model or self.default_model
        self._timeout = timeout

    def complete(self, req: CompletionRequest) -> CompletionResult:
        messages = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})
        body: dict = {
            "model": self._model,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.response_schema is not None:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions", json=body, timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EngineError(f"{self.name} call failed: {exc}") from exc

        data = resp.json()
        choices = data.get("choices") or []
        text = (choices[0]["message"]["content"] if choices else "").strip()
        if not text:
            raise EngineError(f"{self.name} returned empty content")
        u = data.get("usage", {}) or {}
        usage = Usage(
            tokens_in=int(u.get("prompt_tokens", 0) or 0),
            tokens_out=int(u.get("completion_tokens", 0) or 0),
        )
        parsed = None
        if req.response_schema is not None:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise EngineError(f"{self.name}: expected JSON, parse failed: {exc}") from exc
        return CompletionResult(text=text, usage=usage, engine=self.name, json=parsed)

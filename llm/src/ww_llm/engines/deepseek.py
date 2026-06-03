"""DeepSeek engine — opt-in, pay-per-use (OpenAI-compatible API)."""

from __future__ import annotations

from ._openai_compatible import OpenAICompatibleEngine


class DeepSeekEngine(OpenAICompatibleEngine):
    base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"

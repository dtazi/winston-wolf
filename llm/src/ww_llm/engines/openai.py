"""OpenAI (GPT) engine — opt-in, pay-per-use."""

from __future__ import annotations

from ._openai_compatible import OpenAICompatibleEngine


class OpenAIEngine(OpenAICompatibleEngine):
    base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o"

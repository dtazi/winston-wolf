"""Resolve a tool name to a live Engine instance.

`engine_for("scout")` returns the engine the config assigns to scout, or the
default. Fail-loud (EngineError) on an undefined engine name or a missing env
key — better to stop than to silently mis-route or leak a half-configured call.
"""

from __future__ import annotations

import os
from typing import Any

from .base import Engine, EngineError
from .config import EngineRoomConfig, load_config


def _build_engine(name: str, spec: dict[str, Any]) -> Engine:
    etype = spec.get("type")
    if etype == "claude_subscription":
        from .engines.claude_subscription import ClaudeSubscriptionEngine

        return ClaudeSubscriptionEngine(name=name)

    # API engines: require their env-named key to be present (FR-015, fail-loud).
    key_env = spec.get("api_key_env")
    if not key_env:
        raise EngineError(f"engine '{name}' ({etype}) is missing 'api_key_env'")
    api_key = os.environ.get(key_env)
    if not api_key:
        raise EngineError(
            f"engine '{name}' needs env var {key_env}, which is unset"
        )
    model = spec.get("model")

    if etype == "anthropic_api":
        from .engines.anthropic_api import AnthropicAPIEngine

        return AnthropicAPIEngine(name=name, api_key=api_key, model=model)
    if etype == "openai":
        from .engines.openai import OpenAIEngine

        return OpenAIEngine(name=name, api_key=api_key, model=model)
    if etype == "deepseek":
        from .engines.deepseek import DeepSeekEngine

        return DeepSeekEngine(name=name, api_key=api_key, model=model)

    raise EngineError(f"unknown engine type '{etype}' for engine '{name}'")


def load_registry(config: EngineRoomConfig | None = None) -> EngineRoomConfig:
    return config or load_config()


def engine_for(tool: str, config: EngineRoomConfig | None = None) -> Engine:
    cfg = load_registry(config)
    engine_name = cfg.engine_name_for_tool(tool)
    spec = cfg.engines.get(engine_name)
    if spec is None:
        raise EngineError(
            f"tool '{tool}' resolves to engine '{engine_name}', "
            f"which is not defined in the engine room"
        )
    return _build_engine(engine_name, spec)

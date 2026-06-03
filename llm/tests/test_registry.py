"""Registry resolution: default fallback, per-tool mapping, fail-loud."""

from __future__ import annotations

import pytest

from ww_llm.base import Engine, EngineError
from ww_llm.config import EngineRoomConfig
from ww_llm.registry import engine_for


def _cfg(tools=None, engines=None):
    return EngineRoomConfig(
        default="claude_subscription",
        engines=engines or {"claude_subscription": {"type": "claude_subscription"}},
        tools=tools or {},
    )


def test_unassigned_tool_falls_back_to_default():
    eng = engine_for("scout", _cfg())
    assert isinstance(eng, Engine)
    assert eng.name == "claude_subscription"


def test_assigned_tool_uses_its_engine(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    cfg = _cfg(
        tools={"scout": "deepseek"},
        engines={
            "claude_subscription": {"type": "claude_subscription"},
            "deepseek": {"type": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"},
        },
    )
    eng = engine_for("scout", cfg)
    assert eng.name == "deepseek"
    # a different, unassigned tool still gets the default
    assert engine_for("outreach", cfg).name == "claude_subscription"


def test_missing_api_key_is_fail_loud(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cfg = _cfg(
        tools={"scout": "deepseek"},
        engines={"deepseek": {"type": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"}},
    )
    with pytest.raises(EngineError, match="DEEPSEEK_API_KEY"):
        engine_for("scout", cfg)


def test_undefined_engine_is_fail_loud():
    cfg = _cfg(tools={"scout": "ghost"})
    with pytest.raises(EngineError, match="not defined"):
        engine_for("scout", cfg)

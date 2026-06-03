"""Engine-room config loading.

Reads `config/engines.yaml` (repo root) or the path in $WW_ENGINES_FILE. Keys
are env var NAMES (`api_key_env`), never literal secrets (FR-015). If no config
file exists, we fall back to a built-in default: the Claude subscription as the
sole engine — so nothing breaks before anything is configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_BUILTIN_DEFAULT: dict[str, Any] = {
    "default": "claude_subscription",
    "engines": {"claude_subscription": {"type": "claude_subscription"}},
    "tools": {},
}


@dataclass(slots=True)
class EngineRoomConfig:
    default: str
    engines: dict[str, dict[str, Any]]
    tools: dict[str, str] = field(default_factory=dict)

    def engine_name_for_tool(self, tool: str) -> str:
        """Engine assigned to `tool`, or the default when unassigned (FR-013)."""
        return self.tools.get(tool, self.default)


def config_path() -> Path:
    env = os.environ.get("WW_ENGINES_FILE")
    if env:
        return Path(env)
    # repo root = llm/src/ww_llm/config.py -> parents[3]
    return Path(__file__).resolve().parents[3] / "config" / "engines.yaml"


def load_config() -> EngineRoomConfig:
    path = config_path()
    raw = yaml.safe_load(path.read_text()) if path.exists() else _BUILTIN_DEFAULT
    if not isinstance(raw, dict) or "default" not in raw or "engines" not in raw:
        raise ValueError(f"malformed engine-room config at {path}")
    return EngineRoomConfig(
        default=raw["default"],
        engines=raw.get("engines", {}),
        tools=raw.get("tools", {}) or {},
    )

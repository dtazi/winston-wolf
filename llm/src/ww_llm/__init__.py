"""Winston Wolf LLM engine room.

A shared, per-tool LLM engine registry. Each module names the *tool* it is
(e.g. "scout"); the registry resolves that to an Engine (a provider adapter),
falling back to a configured default. Adding a provider is one adapter file +
a config entry + an env-supplied key — no module code changes.
"""

from .base import (
    CompletionRequest,
    CompletionResult,
    Engine,
    EngineError,
    Usage,
)
from .registry import engine_for, load_registry

__all__ = [
    "CompletionRequest",
    "CompletionResult",
    "Engine",
    "EngineError",
    "Usage",
    "engine_for",
    "load_registry",
]

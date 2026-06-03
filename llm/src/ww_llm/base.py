"""The engine seam: one interface every LLM provider implements.

Callers build a CompletionRequest, call engine.complete(req), and get back a
CompletionResult carrying the text, optional parsed JSON, and Usage (tokens +
cost). Usage is uniform across providers so cost reporting is engine-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


class EngineError(RuntimeError):
    """An engine could not produce a result (outage, bad config, parse error).

    Callers catch this at the module boundary and park the affected work item
    rather than letting it cascade (constitution Article 11).
    """


@dataclass(slots=True)
class CompletionRequest:
    prompt: str
    system: Optional[str] = None
    # When set, the engine must return JSON; `.json` on the result is the parsed object.
    response_schema: Optional[dict[str, Any]] = None
    max_tokens: int = 1024  # explicit budget — no unbounded calls (Article 4)
    temperature: float = 0.0


@dataclass(slots=True)
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Optional[float] = None  # None for the subscription engine (no per-call $)


@dataclass(slots=True)
class CompletionResult:
    text: str
    usage: Usage
    engine: str
    json: Optional[dict[str, Any]] = field(default=None)


@runtime_checkable
class Engine(Protocol):
    name: str

    def complete(self, req: CompletionRequest) -> CompletionResult: ...

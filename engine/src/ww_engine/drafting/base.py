"""The Drafter seam (FR-015). The ONLY place that knows how copy is made.

Everything else (selection, sending, detection, modes, cost) depends on this
contract, never on Claude Code. Swapping ClaudeCodeDrafter -> ApiDrafter later
changes nothing else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


class DraftError(Exception):
    """Drafting failed for this lead (caught at the module boundary)."""


class DrafterCapReached(Exception):
    """Subscription usage cap hit — stop drafting; resume next run (FR-006)."""


@dataclass
class DraftRequest:
    lead: dict[str, Any]
    pitch: dict[str, Any]
    brief_excerpt: dict[str, Any]
    value_angle: str
    touch_number: int
    personalization: dict[str, Any]  # {level, facts}


@dataclass
class DraftResult:
    subject: str
    body_text: str
    message_recipe: dict[str, Any]
    token_usage: list[dict[str, Any]] = field(default_factory=list)


class Drafter(Protocol):
    def draft(self, req: DraftRequest) -> DraftResult: ...


# FR-013/SC-009: named reference accounts must never appear. Enforced in code,
# not left to the model. Extend as Richbond grants written permission.
_FORBIDDEN_PATTERNS = [
    re.compile(r"\bikea\b", re.IGNORECASE),
]


def violates_named_account_guard(text: str) -> bool:
    return any(p.search(text) for p in _FORBIDDEN_PATTERNS)

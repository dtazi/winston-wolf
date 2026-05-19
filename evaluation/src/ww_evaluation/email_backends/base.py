"""EmailBackend protocol and EmailResult shape.

Email-finding is its own evaluation axis. Given (first_name, last_name, domain),
each backend returns its best guess at the person's email plus an optional
confidence score. The scorer compares against ground-truth emails recorded
on the contact YAML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class EmailResult:
    email: str | None
    score: float | None
    first_name: str
    last_name: str
    domain: str
    source: str
    raw: dict[str, Any] = field(default_factory=dict)


class EmailBackend(Protocol):
    name: str

    def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> EmailResult: ...

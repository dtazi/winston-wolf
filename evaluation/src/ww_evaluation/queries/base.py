"""Query model and the Pattern taxonomy used by the runner and scorer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Pattern(str, Enum):
    """The four evaluation patterns currently supported.

    Pattern D was added 2026-05-12 after Pattern C's structural failure on
    industrialist targets (find_similar over-anchors on the brand name in
    the reference URL). D derives a brand-agnostic ICP description from
    the URL via an LLM, then fires that description through every
    SearchBackend as a normal Pattern-B-shaped query.
    """

    PEOPLE_AT_TARGET = "A"
    COMPANY_DISCOVERY = "B"
    FIND_SIMILAR = "C"
    ICP_FROM_URL = "D"
    EMAIL_FROM_NAME_COMPANY = "E"


@dataclass(slots=True)
class Query:
    """A single test query.

    ``text`` is set for Patterns A and B (the search string).
    ``url`` is set for Patterns C and D (the reference URL).
    ``focus`` is set for Pattern D — the target business line we want
    competitors for. Required for diversified-conglomerate targets where
    a generic "find similar" returns adjacent-industry noise.
    The runner uses ``pattern`` to decide which backend method to call.
    """

    id: str
    pattern: Pattern
    description: str
    text: str | None = None
    url: str | None = None
    focus: str | None = None
    # Pattern E inputs — name + company domain for email lookup
    first_name: str | None = None
    last_name: str | None = None
    domain: str | None = None
    target_contact_ids: list[str] = field(default_factory=list)
    target_company_ids: list[str] = field(default_factory=list)
    country: str | None = None
    language: str | None = None

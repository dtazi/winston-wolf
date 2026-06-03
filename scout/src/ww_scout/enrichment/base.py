"""Swappable vendor adapter seams (mirrors the evaluation harness pattern).

SearchBackend finds a company domain + a role-matching person; EmailBackend
finds a verified email. The bake-off winner drops in as one adapter file. A
`NullBackend` lets the whole pipeline run end-to-end without API keys (returns
deterministic "not_found"), so everything is testable before vendors are wired.

Backends NEVER raise for "not found" — they return a status. They MAY raise
BackendError on a genuine outage, which the caller turns into a parked lead
(Article 11). Adapters must not log prospect PII (Article 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


class BackendError(RuntimeError):
    """A vendor call failed (outage/transport) — caller parks the lead."""


@dataclass(slots=True)
class DomainResult:
    domain: Optional[str]
    confidence: float
    status: str  # "found" | "not_found"
    detail: str = ""


@dataclass(slots=True)
class PersonResult:
    first_name: Optional[str]
    last_name: Optional[str]
    title: Optional[str]
    source_url: Optional[str]
    status: str  # "found" | "not_found"
    detail: str = ""


@dataclass(slots=True)
class EmailResult:
    email: Optional[str]
    status: str  # "verified" | "unverified" | "not_found" (caller maps confidence)
    confidence: float
    cost_usd: Optional[float] = None
    detail: str = ""


@runtime_checkable
class SearchBackend(Protocol):
    name: str

    def find_domain(self, company_name: str, region: Optional[str]) -> DomainResult: ...

    def find_person(self, domain: str, target_roles: list[str]) -> PersonResult: ...


@runtime_checkable
class EmailBackend(Protocol):
    name: str

    def find_email(self, *, first_name: str, last_name: str, domain: str) -> EmailResult: ...


class NullBackend:
    """Keyless stub: finds nothing, never errors. For dry-runs and tests."""

    name = "null"

    def find_domain(self, company_name: str, region: Optional[str]) -> DomainResult:
        return DomainResult(None, 0.0, "not_found", "null backend")

    def find_person(self, domain: str, target_roles: list[str]) -> PersonResult:
        return PersonResult(None, None, None, None, "not_found", "null backend")

    def find_email(self, *, first_name: str, last_name: str, domain: str) -> EmailResult:
        return EmailResult(None, "not_found", 0.0, None, "null backend")

"""SearchBackend and SimilarityBackend protocols and the SearchResult shape.

Every vendor adapter implements ``SearchBackend``. A vendor that additionally
supports URL-based similarity (currently only Exa) also implements
``SimilarityBackend``. The runner detects the latter via a simple
``hasattr(backend, 'find_similar')`` check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    raw: dict[str, Any] = field(default_factory=dict)


class SearchBackend(Protocol):
    name: str

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
    ) -> list[SearchResult]: ...


class SimilarityBackend(Protocol):
    name: str

    def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
    ) -> list[SearchResult]: ...

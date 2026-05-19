"""Exa backend adapter — implements both SearchBackend and SimilarityBackend.

Uses Exa's ``auto`` search type (their balanced default) with highlights
enabled — highlights are query-relevant excerpts, keeping token usage
predictable and the recommended content mode for LLM workflows.

``find_similar`` is the differentiated capability: given a reference URL,
Exa returns pages whose embeddings are nearest in vector space. Used for
Pattern C of the evaluation.
"""

from __future__ import annotations

import os
from typing import Any

from exa_py import Exa

from .base import SearchResult


class ExaBackend:
    name = "exa"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("EXA_API_KEY")
        if not key:
            raise ValueError("EXA_API_KEY is not set")
        self._client = Exa(api_key=key)

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,  # Exa has no country param; ignored
        language: str | None = None,  # Exa has no language param; ignored
    ) -> list[SearchResult]:
        response = self._client.search_and_contents(
            query,
            type="auto",
            num_results=num_results,
            highlights=True,
        )
        return [
            SearchResult(
                title=getattr(r, "title", "") or "",
                url=getattr(r, "url", "") or "",
                snippet=_snippet(r),
                source=self.name,
                raw=_as_dict(r),
            )
            for r in response.results
        ]

    def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
    ) -> list[SearchResult]:
        response = self._client.find_similar_and_contents(
            url,
            num_results=num_results,
            highlights=True,
            exclude_source_domain=True,
        )
        return [
            SearchResult(
                title=getattr(r, "title", "") or "",
                url=getattr(r, "url", "") or "",
                snippet=_snippet(r),
                source=self.name,
                raw=_as_dict(r),
            )
            for r in response.results
        ]


def _snippet(result: Any) -> str:
    highlights = getattr(result, "highlights", None)
    if highlights:
        return " … ".join(highlights)
    text = getattr(result, "text", None)
    if text:
        return text[:500]
    return ""


def _as_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
    return {}

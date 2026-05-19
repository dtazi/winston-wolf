"""Tavily backend adapter.

Uses Tavily's standard `search` with `search_depth='advanced'` to maximise
recall — the difference vs `basic` is more thorough crawling and richer
snippets, paid for in latency. Acceptable for evaluation runs.
"""

from __future__ import annotations

import os
from typing import Any

from tavily import TavilyClient

from .base import SearchResult


class TavilyBackend:
    name = "tavily"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise ValueError("TAVILY_API_KEY is not set")
        self._client = TavilyClient(api_key=key)

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
    ) -> list[SearchResult]:
        # Tavily expects full country names ('Morocco', not 'ma'). For the
        # evaluation harness, the query text already encodes country context,
        # so we drop the param rather than maintain an ISO-to-name map for
        # only one backend. Revisit if country biasing turns out to matter.
        kwargs: dict[str, Any] = {
            "query": query,
            "max_results": num_results,
            "search_depth": "advanced",
        }
        response = self._client.search(**kwargs)
        items = response.get("results", []) if isinstance(response, dict) else []
        return [
            SearchResult(
                title=item.get("title", "") or "",
                url=item.get("url", "") or "",
                snippet=item.get("content", "") or "",
                source=self.name,
                raw=item,
            )
            for item in items
        ]

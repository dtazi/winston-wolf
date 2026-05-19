"""Brave Search backend adapter.

Brave has no first-party Python SDK; we hit the REST endpoint directly.
`safesearch=off` is required because B2B research queries can be mis-flagged
by Brave's default moderate setting. `text_decorations=False` strips highlight
HTML from snippets, keeping them clean for downstream LLM consumption.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .base import SearchResult

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Brave's supported `country` enum, verified 2026-05-12 against API errors.
# Notable absences: Morocco, the rest of the Maghreb, most of Africa.
_BRAVE_SUPPORTED_COUNTRIES = frozenset({
    "AR", "AU", "AT", "BE", "BR", "CA", "CL", "DK", "FI", "FR",
    "DE", "GR", "HK", "IN", "ID", "IT", "JP", "KR", "MY", "MX",
    "NL", "NZ", "NO", "CN", "PL", "PT", "PH", "RU", "SA", "ZA",
    "ES", "SE", "CH", "TR", "GB", "US",
})


class BraveBackend:
    name = "brave"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("BRAVE_API_KEY")
        if not key:
            raise ValueError("BRAVE_API_KEY is not set")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-Subscription-Token": key,
                "Accept": "application/json",
            }
        )

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
    ) -> list[SearchResult]:
        # Brave expects lowercase 'false' / 'true' for boolean query params;
        # requests serialises Python booleans as 'False' / 'True' which 422s.
        params: dict[str, Any] = {
            "q": query,
            "count": num_results,
            "safesearch": "off",
            "text_decorations": "false",
        }
        # Brave's `country` param is a strict enum that does NOT include Morocco
        # (verified 2026-05-12 via API 422 response). Mapping unsupported
        # countries silently to None preserves a real result instead of 422-ing.
        # The query text encodes country context anyway.
        if country and country.upper() in _BRAVE_SUPPORTED_COUNTRIES:
            params["country"] = country.upper()
        if language:
            params["search_lang"] = language

        response = self._session.get(BRAVE_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        items = (data.get("web") or {}).get("results", []) or []
        return [
            SearchResult(
                title=item.get("title", "") or "",
                url=item.get("url", "") or "",
                snippet=item.get("description", "") or "",
                source=self.name,
                raw=item,
            )
            for item in items
        ]

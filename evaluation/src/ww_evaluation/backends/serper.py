"""Serper backend adapter.

Serper is a thin wrapper over Google's SERP — we get Google's index and
ranking via a structured JSON response. No first-party Python SDK; we hit
the REST endpoint directly. `gl` biases by country, `hl` by language.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .base import SearchResult

SERPER_URL = "https://google.serper.dev/search"


class SerperBackend:
    name = "serper"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("SERPER_API_KEY")
        if not key:
            raise ValueError("SERPER_API_KEY is not set")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-KEY": key,
                "Content-Type": "application/json",
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
        body: dict[str, Any] = {"q": query, "num": num_results}
        if country:
            body["gl"] = country
        if language:
            body["hl"] = language

        response = self._session.post(SERPER_URL, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()

        items = data.get("organic", []) or []
        return [
            SearchResult(
                title=item.get("title", "") or "",
                url=item.get("link", "") or "",
                snippet=item.get("snippet", "") or "",
                source=self.name,
                raw=item,
            )
            for item in items
        ]

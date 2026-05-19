"""Perplexity backend adapter.

Architectural note: Perplexity does not return "a list of results" the way
the other vendors do — it returns a synthesised prose answer plus a list of
source URLs ("citations"). To make Perplexity comparable in our scorer,
each citation URL becomes one SearchResult; the prose answer goes into
every result's `snippet` (truncated) and the full response into `raw`.

This mapping is intentionally lossy. It lets recall scoring work
("did the right person's name appear anywhere in Perplexity's output?")
without pretending Perplexity is shaped like keyword search.

Uses `sonar-pro` by default — the balanced quality tier. Cheaper `sonar`
is too thin for B2B research; `sonar-reasoning` overlaps with what our
own agent loop will do and locks reasoning into Perplexity's LLM.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .base import SearchResult

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar-pro"
MAX_SNIPPET_CHARS = 600


class PerplexityBackend:
    name = "perplexity"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        if not key:
            raise ValueError("PERPLEXITY_API_KEY is not set")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
        )
        self._model = model

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
    ) -> list[SearchResult]:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": query}],
            "return_citations": True,
        }

        response = self._session.post(PERPLEXITY_URL, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()

        prose = ""
        try:
            prose = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            prose = ""

        citations = _extract_citations(data)
        snippet = prose[:MAX_SNIPPET_CHARS]

        if not citations:
            # No citations returned: surface the prose itself as a single synthetic result,
            # so the scorer still sees any names Perplexity mentioned.
            return [
                SearchResult(
                    title="Perplexity synthesised answer",
                    url="",
                    snippet=snippet,
                    source=self.name,
                    raw=data,
                )
            ]

        results: list[SearchResult] = []
        for entry in citations[:num_results]:
            url, title = _normalise_citation(entry)
            results.append(
                SearchResult(
                    title=title or url,
                    url=url,
                    snippet=snippet,
                    source=self.name,
                    raw={"citation": entry, "answer": prose, "full": data},
                )
            )
        return results


def _extract_citations(data: dict[str, Any]) -> list[Any]:
    """Pull citations out of Perplexity's response.

    The exact field name has moved over time (`citations`, `search_results`,
    `references`). We check the known locations and fall back to an empty list.
    """
    for key in ("citations", "search_results", "references"):
        value = data.get(key)
        if value:
            return list(value)
    try:
        message = data["choices"][0]["message"]
        for key in ("citations", "search_results", "references"):
            value = message.get(key)
            if value:
                return list(value)
    except (KeyError, IndexError, TypeError):
        pass
    return []


def _normalise_citation(entry: Any) -> tuple[str, str]:
    """Citations may be plain URL strings or {url, title} dicts. Normalise."""
    if isinstance(entry, str):
        return entry, ""
    if isinstance(entry, dict):
        url = entry.get("url") or entry.get("link") or ""
        title = entry.get("title") or entry.get("name") or ""
        return url, title
    return "", ""

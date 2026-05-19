"""Runner — fires the query set through backends, persists raw responses.

Pattern routing:
  A, B   → ``backend.search(query.text, ...)``
  C      → ``backend.find_similar(query.url)`` if the backend implements it,
           else skipped (recorded, not failed).
  D      → URL → fetch content → LLM extracts a brand-agnostic ICP description →
           that description is fired through ``backend.search(...)`` like a
           Pattern B query. The derived text is recorded once per Pattern D
           query, then reused across all backends in the same run.

One run produces one timestamped subdirectory under ``results/raw/<customer>/``.
Each backend gets its own subdirectory; each query gets its own JSON file.
Per-query failures are captured so a single error doesn't abort the run.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from tavily import TavilyClient

from .backends.base import SearchBackend
from .email_backends.base import EmailBackend
from .llm.base import ICPExtractor
from .queries.base import Pattern, Query

FETCH_TIMEOUT_SECONDS = 20
FETCH_USER_AGENT = (
    "Mozilla/5.0 (compatible; WinstonWolfEval/0.1; +https://github.com/winston-wolf)"
)


def run(
    backends: Iterable[SearchBackend],
    queries: Iterable[Query],
    output_dir: Path,
    *,
    extractor: ICPExtractor | None = None,
    email_backends: Iterable[EmailBackend] | None = None,
) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    queries = list(queries)

    # Pattern D preprocessing — fetch each Pattern D URL once, run LLM extraction once,
    # cache the derived ICP description so every backend in this run sees the same query.
    pattern_d_text: dict[str, str] = {}
    pattern_d_errors: dict[str, str] = {}
    pattern_d_source: dict[str, str] = {}
    for q in queries:
        if q.pattern is not Pattern.ICP_FROM_URL:
            continue
        if not q.url:
            pattern_d_errors[q.id] = "Pattern D query is missing url"
            continue
        if extractor is None:
            pattern_d_errors[q.id] = "Pattern D requires an ICP extractor — none supplied"
            continue
        try:
            content = _fetch_text(q.url)
            pattern_d_source[q.id] = content[:1000]
            pattern_d_text[q.id] = extractor.extract_icp(
                content,
                source_url=q.url,
                focus=q.focus,
            )
        except Exception as exc:  # noqa: BLE001 — never let extraction kill the whole run
            pattern_d_errors[q.id] = f"{type(exc).__name__}: {exc}"

    # Write a single-extraction record so the derived ICP is preserved alongside results.
    if any(q.pattern is Pattern.ICP_FROM_URL for q in queries):
        meta_dir = run_dir / "_pattern_d_meta"
        meta_dir.mkdir(exist_ok=True)
        for q in queries:
            if q.pattern is not Pattern.ICP_FROM_URL:
                continue
            (meta_dir / f"{q.id}.json").write_text(
                json.dumps(
                    {
                        "query_id": q.id,
                        "source_url": q.url,
                        "focus": q.focus,
                        "extractor": getattr(extractor, "name", None),
                        "extractor_model": getattr(extractor, "model", None),
                        "derived_text": pattern_d_text.get(q.id),
                        "source_excerpt": pattern_d_source.get(q.id),
                        "error": pattern_d_errors.get(q.id),
                    },
                    indent=2,
                    default=str,
                )
            )

    # Search backends handle Patterns A, B, C, D. Pattern E is skipped here
    # and dispatched to email_backends below.
    search_queries = [q for q in queries if q.pattern is not Pattern.EMAIL_FROM_NAME_COMPANY]
    email_queries = [q for q in queries if q.pattern is Pattern.EMAIL_FROM_NAME_COMPANY]

    for backend in backends:
        backend_dir = run_dir / backend.name
        backend_dir.mkdir(exist_ok=True)
        for query in search_queries:
            payload = _execute(backend, query, pattern_d_text, pattern_d_errors)
            (backend_dir / f"{query.id}.json").write_text(
                json.dumps(payload, indent=2, default=str)
            )

    if email_queries and email_backends:
        for eb in email_backends:
            eb_dir = run_dir / eb.name
            eb_dir.mkdir(exist_ok=True)
            for query in email_queries:
                payload = _execute_email(eb, query)
                (eb_dir / f"{query.id}.json").write_text(
                    json.dumps(payload, indent=2, default=str)
                )

    return run_dir


def _execute_email(backend: EmailBackend, query: Query) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query_id": query.id,
        "pattern": query.pattern.value,
        "backend": backend.name,
        "first_name": query.first_name,
        "last_name": query.last_name,
        "domain": query.domain,
        "email": None,
        "score": None,
        "raw": None,
        "error": None,
    }
    try:
        if not (query.first_name and query.last_name and query.domain):
            raise ValueError("Pattern E query missing first_name / last_name / domain")
        result = backend.find_email(query.first_name, query.last_name, query.domain)
        base["email"] = result.email
        base["score"] = result.score
        base["raw"] = result.raw
    except Exception as exc:  # noqa: BLE001
        base["error"] = f"{type(exc).__name__}: {exc}"
    return base


def _execute(
    backend: SearchBackend,
    query: Query,
    pattern_d_text: dict[str, str],
    pattern_d_errors: dict[str, str],
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query_id": query.id,
        "pattern": query.pattern.value,
        "backend": backend.name,
        "text": query.text,
        "url": query.url,
        "results": [],
        "error": None,
        "skipped": None,
        "derived_text": None,
    }

    try:
        if query.pattern is Pattern.FIND_SIMILAR:
            if not hasattr(backend, "find_similar"):
                base["skipped"] = "backend does not support find_similar"
                return base
            assert query.url, "Pattern C query missing url"
            results = backend.find_similar(query.url)  # type: ignore[attr-defined]
        elif query.pattern is Pattern.ICP_FROM_URL:
            if query.id in pattern_d_errors:
                base["error"] = f"pattern D preprocessing failed: {pattern_d_errors[query.id]}"
                return base
            derived = pattern_d_text.get(query.id)
            if not derived:
                base["error"] = "pattern D produced no derived text"
                return base
            base["derived_text"] = derived
            results = backend.search(
                derived,
                country=query.country,
                language=query.language,
            )
        else:
            assert query.text, f"Pattern {query.pattern.value} query missing text"
            results = backend.search(
                query.text,
                country=query.country,
                language=query.language,
            )
        base["results"] = [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "raw": r.raw,
            }
            for r in results
        ]
    except Exception as exc:  # noqa: BLE001
        base["error"] = f"{type(exc).__name__}: {exc}"

    return base


def _fetch_text(url: str) -> str:
    """Pull the page content for Pattern D extraction.

    Tavily's extract endpoint handles JavaScript-rendered pages (Drupal,
    React, etc.) and returns clean readable text — exactly what we need
    to feed into the LLM. Many corporate sites (e.g. grouperichbond.ma)
    are Drupal-built and serve no body content in static HTML, so a raw
    requests.get is not viable as the default fetch path.

    Falls back to raw requests if Tavily is unavailable or rejects the URL.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            client = TavilyClient(api_key=tavily_key)
            result = client.extract(urls=[url])
            # Tavily returns {'results': [{'url': ..., 'raw_content': '...'}], 'failed_results': [...]}
            if isinstance(result, dict):
                items = result.get("results") or []
                if items:
                    raw = items[0].get("raw_content") or items[0].get("content") or ""
                    if raw.strip():
                        return raw
        except Exception:  # noqa: BLE001 — fall back to raw fetch on any extraction failure
            pass

    response = requests.get(
        url,
        headers={"User-Agent": FETCH_USER_AGENT},
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text

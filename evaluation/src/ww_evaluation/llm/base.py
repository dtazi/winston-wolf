"""ICPExtractor protocol.

Pattern D needs an LLM step that turns a reference URL's content into a
brand-agnostic ICP description. The protocol lets us swap LLM providers
without touching the rest of the harness, mirroring the SearchBackend
adapter pattern.
"""

from __future__ import annotations

from typing import Protocol


class ICPExtractor(Protocol):
    name: str
    model: str

    def extract_icp(
        self,
        content: str,
        *,
        source_url: str | None = None,
        focus: str | None = None,
    ) -> str:
        """Given page content (and an optional business-line focus), return a
        brand-agnostic ICP description suitable as a search query."""
        ...

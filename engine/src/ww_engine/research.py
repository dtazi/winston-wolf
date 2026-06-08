"""Per-prospect research (D7, contracts/research.md).

Researches ONLY the operator-provided lead (no acquisition, FR-001). Produces a
structured summary + the trigger signals the drafter grounds the opener in, plus
the recipient's IANA timezone for the per-recipient send window (D2).

The researcher is behind a seam (like the Drafter) so tests inject a fake and
the engine never hard-couples to a browsing backend. The default implementation
shells out to headless Claude Code (which can browse), mirroring the drafter.

Article 3: no prospect PII is logged here. Article 15: no inbox/reply access.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Protocol


class ResearchError(Exception):
    """Research failed for this lead (caught at the boundary → thin draft)."""


@dataclass
class ResearchResult:
    summary: str = ""
    signals: list[dict[str, Any]] = field(default_factory=list)
    send_timezone: str | None = None
    confidence: str = "thin"  # high | medium | thin
    sources: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "summary": self.summary, "signals": self.signals,
            "send_timezone": self.send_timezone, "confidence": self.confidence,
            "sources": self.sources,
        })

    @classmethod
    def from_json(cls, blob: str | None) -> "ResearchResult":
        if not blob:
            return cls()
        d = json.loads(blob)
        return cls(
            summary=d.get("summary", ""), signals=d.get("signals", []),
            send_timezone=d.get("send_timezone"),
            confidence=d.get("confidence", "thin"), sources=d.get("sources", []),
        )


class Researcher(Protocol):
    def research(self, lead: dict[str, Any]) -> ResearchResult: ...


def _build_prompt(lead: dict[str, Any]) -> str:
    company = (lead.get("company_name") or "").strip()
    person = (lead.get("person_name") or "").strip()
    title = (lead.get("person_title") or "").strip()
    notes = (lead.get("notes") or "").strip()
    return f"""Research this B2B sales prospect so a colleague can write one \
deeply-personalized cold email. Use web search: the company site, recent news, \
and LinkedIn where possible.

PROSPECT:
  Company: {company}
  Person:  {person} ({title})
  Operator notes: {notes or "(none)"}

Return STRICT JSON only:
{{
  "summary": "2-4 paragraph synthesis of who they are and what's going on",
  "signals": [{{"type": "expansion|leadership|funding|sourcing|...",
                "detail": "the specific trigger", "source_url": "..."}}],
  "send_timezone": "IANA tz of the company HQ, e.g. America/Chicago, or null",
  "confidence": "high|medium|thin",
  "sources": ["url", "url"]
}}
Ground every signal in a real source. If you cannot find much, say so with \
confidence \"thin\" rather than inventing detail."""


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ResearchError("researcher returned no JSON object")
    return json.loads(text[start:end + 1])


class ClaudeCodeResearcher:
    """Headless Claude Code with web access (mirrors ClaudeCodeDrafter)."""

    def __init__(self, claude_bin: str = "claude", timeout: int = 240) -> None:
        self._bin = claude_bin
        self._timeout = timeout

    def research(self, lead: dict[str, Any]) -> ResearchResult:
        try:
            proc = subprocess.run(
                [self._bin, "-p", _build_prompt(lead), "--output-format", "json"],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except FileNotFoundError as exc:
            raise ResearchError(f"claude CLI not found: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ResearchError("claude CLI timed out") from exc
        if proc.returncode != 0:
            raise ResearchError(f"claude exited {proc.returncode}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ResearchError(f"claude JSON parse failed: {exc}") from exc
        obj = _extract_json(envelope.get("result") or envelope.get("text") or "")
        return ResearchResult(
            summary=(obj.get("summary") or "").strip(),
            signals=obj.get("signals") or [],
            send_timezone=obj.get("send_timezone"),
            confidence=(obj.get("confidence") or "thin").strip(),
            sources=obj.get("sources") or [],
        )


def store_research(conn, lead_id: str, result: ResearchResult) -> None:
    """Persist the research JSON on the lead and set its send_timezone (D7/D2)."""
    conn.execute(
        "UPDATE leads SET research=?, send_timezone=COALESCE(?, send_timezone), "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (result.to_json(), result.send_timezone, lead_id),
    )
    conn.commit()

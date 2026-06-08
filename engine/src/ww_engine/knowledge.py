"""File-based knowledge for the proof-of-life experiment (004).

Three operator-maintained inputs + one system-appended log, all under the data
directory next to leads.db:

  data/knowledge/<tenant>-kb.md   — grounded facts/offers (Article 17 source)
  data/strategies/*.md            — one cold-email strategy per file
  data/conclusions/<tenant>.md    — system-appended dated observations

Plus the most recent operator feedback comments, read from the DB. All loaders
degrade gracefully (missing file → empty), so a thin day-one setup never crashes
the draft pass; the drafter just has less to ground in.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ww_core.db import DEFAULT_DB_PATH


def data_dir() -> Path:
    """Resolve the data directory: $WW_DATA_DIR or the dir holding leads.db."""
    env = os.environ.get("WW_DATA_DIR")
    return Path(env) if env else Path(DEFAULT_DB_PATH).resolve().parent


def kb_path(tenant: str = "richbond") -> Path:
    return data_dir() / "knowledge" / f"{tenant}-kb.md"


def strategies_dir() -> Path:
    return data_dir() / "strategies"


def conclusions_path(tenant: str = "richbond") -> Path:
    return data_dir() / "conclusions" / f"{tenant}.md"


def load_kb(tenant: str = "richbond") -> str:
    p = kb_path(tenant)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def load_strategies() -> list[dict[str, str]]:
    """Return [{name, text}] for each data/strategies/*.md, sorted by name."""
    d = strategies_dir()
    if not d.is_dir():
        return []
    out: list[dict[str, str]] = []
    for f in sorted(d.glob("*.md")):
        out.append({"name": f.stem, "text": f.read_text(encoding="utf-8")})
    return out


def load_conclusions(tenant: str = "richbond") -> str:
    p = conclusions_path(tenant)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def append_conclusion(text: str, tenant: str = "richbond") -> Path:
    """Append a dated observation (append-only; never rewrites history)."""
    p = conclusions_path(tenant)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with p.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {stamp}\n\n{text.strip()}\n")
    return p


def recent_comments(conn: sqlite3.Connection, campaign_id: str,
                    limit: int = 30) -> list[str]:
    """Most recent operator verdict comments for this campaign (newest first)."""
    rows = conn.execute(
        "SELECT comment FROM send_drafts WHERE campaign_id=? "
        "AND comment IS NOT NULL AND TRIM(comment)!='' "
        "ORDER BY updated_at DESC LIMIT ?",
        (campaign_id, limit),
    ).fetchall()
    return [r["comment"] for r in rows]

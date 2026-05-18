"""Connection to the shared lead database + tracking-specific reads/writes.

The schema is owned by ww-core (`ww-core init` creates every table, including
`tracked_links`). This module only reads `sends` / `tracked_links` and appends
to `events`. It deliberately does not import ww_core so the tracking service
stays independently deployable.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_data_dir() -> Path:
    env = os.environ.get("WW_DATA_DIR")
    return Path(env) if env else _REPO_ROOT / "data"


def db_path() -> Path:
    return get_data_dir() / "leads.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def lookup_send_by_pixel(conn: sqlite3.Connection, pixel_token: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT id, lead_id, sent_at FROM sends WHERE pixel_token = ?",
        (pixel_token,),
    ).fetchone()


def lookup_tracked_link(conn: sqlite3.Connection, click_token: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT send_id, lead_id, original_url FROM tracked_links WHERE id = ?",
        (click_token,),
    ).fetchone()


def record_event(
    conn: sqlite3.Connection,
    lead_id: str,
    event_type: str,
    timestamp: datetime,
    send_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO events (lead_id, send_id, event_type, timestamp, payload)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            send_id,
            event_type,
            timestamp.isoformat(sep=" ", timespec="seconds"),
            json.dumps(payload or {}, default=str),
        ),
    )
    conn.commit()


def parse_db_timestamp(value: str) -> Optional[datetime]:
    """SQLite CURRENT_TIMESTAMP is 'YYYY-MM-DD HH:MM:SS'; tolerate ISO 'T' too."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None

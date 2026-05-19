"""DB access for ww-engine: reuse ww-core's connection, apply idempotent
migrations (conditional ADD COLUMN + the CREATE/INDEX script)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ww_core.db import DEFAULT_DB_PATH, get_connection  # re-exported for callers

__all__ = ["DEFAULT_DB_PATH", "get_connection", "apply_migrations"]

_SCHEMA_SQL = Path(__file__).resolve().parents[2] / "schema_engine.sql"

# table -> (column, definition). Applied only if the column is absent
# (SQLite lacks ADD COLUMN IF NOT EXISTS). Must run BEFORE the index script
# so indexes on new columns succeed.
_ADD_COLUMNS: list[tuple[str, str, str]] = [
    ("campaigns", "mode",
     "mode TEXT NOT NULL DEFAULT 'review' "
     "CHECK (mode IN ('review','autonomous'))"),
    ("leads", "rotation_group", "rotation_group INTEGER"),
    ("leads", "sequence_state",
     "sequence_state TEXT DEFAULT 'active' "
     "CHECK (sequence_state IN "
     "('active','halted_reply','halted_bounce','completed'))"),
    ("leads", "current_touch", "current_touch INTEGER NOT NULL DEFAULT 0"),
    ("sends", "touch_number", "touch_number INTEGER"),
    ("sends", "value_angle", "value_angle TEXT"),
    ("sends", "message_recipe", "message_recipe TEXT"),
    ("sends", "marker_token", "marker_token TEXT"),
    ("sends", "conversation_id", "conversation_id TEXT"),
    ("sends", "internet_message_id", "internet_message_id TEXT"),
]


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    """Idempotently bring the DB up to the engine schema. Returns the list of
    columns actually added (empty on a no-op re-run)."""
    added: list[str] = []
    for table, col, ddl in _ADD_COLUMNS:
        if col not in _columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            added.append(f"{table}.{col}")
    conn.executescript(_SCHEMA_SQL.read_text())
    conn.commit()
    return added

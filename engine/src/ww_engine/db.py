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
    ("leads", "audience",
     "audience TEXT NOT NULL DEFAULT 'direct_buyer' "
     "CHECK (audience IN ('direct_buyer','gpo'))"),
    # 004 proof-of-life experiment: per-recipient send timezone (D2) +
    # persisted research payload (D7, JSON: summary/signals/confidence/sources).
    ("leads", "send_timezone", "send_timezone TEXT"),
    ("leads", "research", "research TEXT"),
    # 004: per-campaign sequencing config (D3) + per-recipient tz fallback.
    # Column DEFAULTS are the legacy 002 values (3/14) so pre-existing campaigns
    # are unchanged; the proof-of-life experiment campaign sets 2/7 explicitly
    # at setup (quickstart). Avoids silently re-capping old campaigns.
    ("campaigns", "max_touches", "max_touches INTEGER NOT NULL DEFAULT 3"),
    ("campaigns", "touch_gap_days",
     "touch_gap_days INTEGER NOT NULL DEFAULT 14"),
    ("campaigns", "send_tz_default",
     "send_tz_default TEXT NOT NULL DEFAULT 'America/New_York'"),
    ("sends", "touch_number", "touch_number INTEGER"),
    ("sends", "value_angle", "value_angle TEXT"),
    ("sends", "message_recipe", "message_recipe TEXT"),
    ("sends", "marker_token", "marker_token TEXT"),
    ("sends", "conversation_id", "conversation_id TEXT"),
    ("sends", "internet_message_id", "internet_message_id TEXT"),
]


# Columns on tables CREATED BY schema_engine.sql (e.g. send_drafts). These must
# be added AFTER the schema script runs (the table does not exist before it). On
# a fresh DB the CREATE TABLE already includes them, so the guard skips; on an
# existing DB this upgrades it. 004: feedback comment (D1).
_ADD_COLUMNS_POST: list[tuple[str, str, str]] = [
    ("send_drafts", "comment", "comment TEXT"),
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
    for table, col, ddl in _ADD_COLUMNS_POST:
        if col not in _columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            added.append(f"{table}.{col}")
    conn.commit()
    return added

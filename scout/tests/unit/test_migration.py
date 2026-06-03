"""ww-core migration is idempotent and adds the 003 columns/tables (T012)."""

from __future__ import annotations

import sqlite3

from ww_core import db as core_db

_ENRICH_COLS = {"domain_status", "person_status", "person_email_status", "enrichment_state"}
_NEW_TABLES = {"campaign_target_profiles", "qualification_verdicts", "enrichment_ledger"}


def _cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_migration_adds_columns_and_tables(tmp_path):
    p = tmp_path / "leads.db"
    core_db.init_database(p)
    conn = sqlite3.connect(p)
    assert _ENRICH_COLS.issubset(_cols(conn, "leads"))
    assert _NEW_TABLES.issubset(_tables(conn))
    conn.close()


def test_migration_is_idempotent(tmp_path):
    p = tmp_path / "leads.db"
    core_db.init_database(p)
    # second run must not raise (no duplicate-column error) and must change nothing
    core_db.init_database(p)
    conn = sqlite3.connect(p)
    added = core_db.migrate_schema(conn)  # third, direct call
    assert added == []  # everything already present
    conn.close()


def test_existing_leads_default_to_new_state(tmp_path):
    p = tmp_path / "leads.db"
    core_db.init_database(p)
    conn = sqlite3.connect(p)
    conn.execute("INSERT OR IGNORE INTO customers (id, name) VALUES ('c','C')")
    conn.execute("INSERT OR IGNORE INTO campaigns (id, customer_id, name) VALUES ('camp','c','x')")
    conn.execute(
        "INSERT INTO leads (id, customer_id, campaign_id, niche_id, source_channel_id) "
        "VALUES ('L1','c','camp','n','manual')"
    )
    conn.commit()
    row = conn.execute("SELECT enrichment_state, domain_status FROM leads WHERE id='L1'").fetchone()
    assert row[0] == "new" and row[1] == "pending"
    conn.close()

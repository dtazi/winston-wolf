from ww_core import db as core_db

from ww_engine import db as engine_db


def _cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_migration_adds_columns_and_tables(db_path):  # happy path
    conn = core_db.get_connection(db_path)
    try:
        assert "mode" in _cols(conn, "campaigns")
        assert {"rotation_group", "sequence_state", "current_touch"} <= _cols(conn, "leads")
        assert {"message_recipe", "marker_token", "conversation_id"} <= _cols(conn, "sends")
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"send_drafts", "token_ledger", "engine_runs"} <= tables
    finally:
        conn.close()


def test_migration_is_idempotent(db_path):  # error/edge: re-run is a no-op
    conn = core_db.get_connection(db_path)
    try:
        added_again = engine_db.apply_migrations(conn)
        assert added_again == []  # nothing added the second time
    finally:
        conn.close()

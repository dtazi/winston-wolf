from ww_core import db as core_db

from ww_engine import rotation, selection


def _enroll(conn, campaign):
    for r in conn.execute("SELECT id FROM leads WHERE campaign_id=?", (campaign,)):
        conn.execute(
            "UPDATE leads SET rotation_group=?, sequence_state='active' WHERE id=?",
            (rotation.group_for_lead(r["id"]), r["id"]),
        )
    conn.commit()


def test_enrolled_active_leads_are_eligible(seeded):  # happy path
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn, "camp1")
        rows = selection.eligible_leads(conn, "camp1")
        assert len(rows) == 9
        assert selection.is_still_eligible(conn, "lead0") is True
    finally:
        conn.close()


def test_replied_lead_is_excluded_and_unenrolled_ignored(seeded):  # error path
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn, "camp1")
        conn.execute(
            "INSERT INTO events (lead_id, event_type, timestamp) "
            "VALUES ('lead0','replied',CURRENT_TIMESTAMP)"
        )
        conn.execute("UPDATE leads SET rotation_group=NULL WHERE id='lead1'")
        conn.commit()
        ids = {r["id"] for r in selection.eligible_leads(conn, "camp1")}
        assert "lead0" not in ids  # hard stop
        assert "lead1" not in ids  # not enrolled
        assert selection.is_still_eligible(conn, "lead0") is False
    finally:
        conn.close()

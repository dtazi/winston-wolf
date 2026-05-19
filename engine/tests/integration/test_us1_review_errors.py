"""US1 error paths: unapproved never sent; outside-window no-op; thin flagged."""

from ww_core import db as core_db

from ww_engine import cli, rotation, sender
from ww_engine.drafting.base import DraftRequest, DraftResult


class FakeDrafter:
    def draft(self, req: DraftRequest) -> DraftResult:
        return DraftResult(f"S{req.touch_number}", f"B {req.value_angle}",
                           {"angle": req.value_angle}, [])


class FakeTransport:
    def send(self, message):
        return {"message_id": "m", "conversation_id": "c",
                "internet_message_id": "<i@x>"}


def _enroll(conn):
    for r in conn.execute("SELECT id FROM leads WHERE campaign_id='camp1'"):
        conn.execute(
            "UPDATE leads SET rotation_group=?, sequence_state='active' WHERE id=?",
            (rotation.group_for_lead(r["id"]), r["id"]))
    conn.commit()


def test_unapproved_drafts_never_deliver_in_review_mode(seeded, monkeypatch):
    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        cli.run_draft(conn, "camp1", 9, FakeDrafter())  # all pending
        counts = cli.run_deliver(conn, "camp1", FakeTransport())
        assert counts["delivered"] == 0
        assert conn.execute("SELECT COUNT(*) c FROM sends").fetchone()["c"] == 0
    finally:
        conn.close()


def test_deliver_outside_window_is_noop(seeded, monkeypatch):
    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: False)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        cli.run_draft(conn, "camp1", 9, FakeDrafter())
        conn.execute("UPDATE send_drafts SET review_state='approved'")
        conn.commit()
        counts = cli.run_deliver(conn, "camp1", FakeTransport())
        assert counts["delivered"] == 0  # window closed
        assert conn.execute("SELECT COUNT(*) c FROM sends").fetchone()["c"] == 0
    finally:
        conn.close()


def test_thin_personalization_is_flagged(seeded, monkeypatch):
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        # strip all context from one lead → thin
        conn.execute("UPDATE leads SET person_title=NULL, company_name=NULL, "
                     "company_region=NULL, company_size_band=NULL WHERE id='lead0'")
        _enroll(conn)
        cli.run_draft(conn, "camp1", 9, FakeDrafter())
        lvl = conn.execute(
            "SELECT personalization_level FROM send_drafts WHERE lead_id='lead0'"
        ).fetchone()["personalization_level"]
        assert lvl == "thin"
    finally:
        conn.close()

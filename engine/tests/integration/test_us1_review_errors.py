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


def test_transport_failure_leaves_db_clean_for_retry(seeded, monkeypatch):
    """Graph refusing the send (expired token, 5xx) must fail loud (Art 11)
    with NO sends row, NO 'sent' event, and the draft still approved — so the
    next deliver pass retries it instead of losing it or double-recording."""
    import pytest

    class RefusingTransport:
        def send(self, message):
            raise RuntimeError("Graph sendMail failed: 401 InvalidAuthenticationToken")

    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        cli.run_draft(conn, "camp1", 9, FakeDrafter())
        conn.execute("UPDATE send_drafts SET review_state='approved'")
        conn.commit()

        with pytest.raises(RuntimeError, match="401"):
            cli.run_deliver(conn, "camp1", RefusingTransport())

        assert conn.execute("SELECT COUNT(*) c FROM sends").fetchone()["c"] == 0
        assert conn.execute(
            "SELECT COUNT(*) c FROM events WHERE event_type='sent'"
        ).fetchone()["c"] == 0
        states = {r["review_state"] for r in conn.execute(
            "SELECT review_state FROM send_drafts")}
        assert states == {"approved"}  # nothing falsely marked delivered
        outcome = conn.execute(
            "SELECT outcome FROM engine_runs WHERE pass='deliver' "
            "ORDER BY id DESC LIMIT 1").fetchone()["outcome"]
        assert outcome == "error"  # recorded, not swallowed (FR-023)
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

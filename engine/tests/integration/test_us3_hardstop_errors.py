"""US3 error paths: auto-reply ignored; Graph failure → error + refuse to
advance follow-ups; reply between draft and deliver cancels the send."""

import pytest
from ww_core import db as core_db

from ww_engine import cli, detector, rotation, runs, sender
from ww_engine.drafting.base import DraftRequest, DraftResult


class FakeDrafter:
    def draft(self, req: DraftRequest) -> DraftResult:
        return DraftResult(f"S{req.touch_number}", f"B {req.value_angle}",
                           {"angle": req.value_angle}, [])


class FakeTransport:
    def __init__(self):
        self.n = 0

    def send(self, message):
        self.n += 1
        return {"message_id": f"m{self.n}", "conversation_id": f"cv{self.n}",
                "internet_message_id": f"<i{self.n}@x>"}


class ExplodingReader:
    def fetch(self):
        raise RuntimeError("Graph unreachable")


def _enroll(conn):
    for r in conn.execute("SELECT id FROM leads WHERE campaign_id='camp1'"):
        conn.execute("UPDATE leads SET rotation_group=?, sequence_state='active' "
                     "WHERE id=?", (rotation.group_for_lead(r["id"]), r["id"]))
    conn.commit()


def test_autoreply_is_not_a_reply(seeded, monkeypatch):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
        monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
        cli.run_draft(conn, "camp1", 1, FakeDrafter())
        conn.execute("UPDATE send_drafts SET review_state='approved'")
        conn.commit()
        cli.run_deliver(conn, "camp1", FakeTransport())
        conv = conn.execute("SELECT conversation_id FROM sends LIMIT 1"
                            ).fetchone()["conversation_id"]

        class R:
            def fetch(self):
                return [{"id": "a1", "conversation_id": conv,
                         "from_addr": "buyer@org.com",
                         "headers": {"auto-submitted": "auto-replied"},
                         "body": "I am on vacation", "refs": []}]

        counts = detector.run_detect(conn, "camp1", R())
        assert counts["replied"] == 0 and counts["skipped"] == 1
        states = {r["sequence_state"] for r in conn.execute(
            "SELECT sequence_state FROM leads WHERE campaign_id='camp1'")}
        assert states == {"active"}  # nothing halted by an OOO
    finally:
        conn.close()


def test_graph_failure_records_error_and_blocks_followups(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        with pytest.raises(RuntimeError):
            detector.run_detect(conn, "camp1", ExplodingReader())
        last = conn.execute(
            "SELECT outcome FROM engine_runs WHERE pass='detect' "
            "ORDER BY id DESC LIMIT 1").fetchone()
        assert last["outcome"] == "error"
        assert runs.detect_is_fresh(conn, "camp1") is False
        # a lead awaiting touch 2 must NOT be delivered while detect is stale
        conn.execute("UPDATE leads SET current_touch=1 WHERE id='lead0'")
        conn.execute(
            "INSERT INTO send_drafts (id,customer_id,campaign_id,lead_id,"
            "touch_number,value_angle,subject,body_text,body_text_original,"
            "message_recipe,personalization_level,review_state) VALUES "
            "('d2','richbond','camp1','lead0',2,'china_plus_one','s','b','b',"
            "'{}','dataset','approved')")
        conn.commit()
        counts = cli.run_deliver(conn, "camp1",
                                 type("T", (), {"send": lambda *a: {}})())
        assert counts["delivered"] == 0  # refuses blind follow-up
    finally:
        conn.close()


def test_reply_between_draft_and_deliver_cancels_send(seeded, monkeypatch):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
        monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
        cli.run_draft(conn, "camp1", 1, FakeDrafter())
        conn.execute("UPDATE send_drafts SET review_state='approved' "
                     "WHERE lead_id='lead0'")
        # reply lands before deliver runs
        conn.execute("INSERT INTO events (lead_id,event_type,timestamp) "
                     "VALUES ('lead0','replied',CURRENT_TIMESTAMP)")
        conn.commit()
        counts = cli.run_deliver(conn, "camp1", FakeTransport())
        assert counts["delivered"] == 0
        assert conn.execute("SELECT COUNT(*) c FROM sends WHERE lead_id='lead0'"
                            ).fetchone()["c"] == 0
    finally:
        conn.close()

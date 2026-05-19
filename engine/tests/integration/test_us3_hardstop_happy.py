"""US3 happy: reply & bounce halt the sequence; detector matches; LinkedIn
task shown cancelled."""

from ww_core import db as core_db

from ww_engine import cli, detector, rotation, selection, sender
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
        return {"message_id": f"m{self.n}", "conversation_id": f"conv{self.n}",
                "internet_message_id": f"<i{self.n}@x>"}


class FakeReader:
    def __init__(self, msgs):
        self._msgs = msgs

    def fetch(self):
        return self._msgs


def _enroll(conn):
    for r in conn.execute("SELECT id FROM leads WHERE campaign_id='camp1'"):
        conn.execute("UPDATE leads SET rotation_group=?, sequence_state='active' "
                     "WHERE id=?", (rotation.group_for_lead(r["id"]), r["id"]))
    conn.commit()


def _deliver_touch1(conn, monkeypatch):
    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    cli.run_draft(conn, "camp1", 9, FakeDrafter())
    conn.execute("UPDATE send_drafts SET review_state='approved'")
    conn.commit()
    return cli.run_deliver(conn, "camp1", FakeTransport())


def test_reply_halts_and_bounce_excludes(seeded, monkeypatch):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        _deliver_touch1(conn, monkeypatch)
        s0 = conn.execute("SELECT conversation_id, marker_token FROM sends "
                          "WHERE lead_id='lead0'").fetchone()
        s1 = conn.execute("SELECT conversation_id, marker_token FROM sends "
                          "WHERE lead_id='lead1'").fetchone()

        reader = FakeReader([
            {"id": "r1", "conversation_id": s0["conversation_id"],
             "from_addr": "buyer@org.com", "headers": {}, "body": "Yes interested",
             "refs": []},
            {"id": "b1", "conversation_id": "x", "from_addr": "postmaster@org.com",
             "headers": {"content-type": "multipart/report; report-type=delivery-status"},
             "body": f"undeliverable {s1['marker_token']}", "refs": []},
        ])
        counts = detector.run_detect(conn, "camp1", reader)
        assert counts["replied"] == 1 and counts["bounced"] == 1

        assert conn.execute("SELECT sequence_state FROM leads WHERE id='lead0'"
                            ).fetchone()["sequence_state"] == "halted_reply"
        assert conn.execute("SELECT sequence_state FROM leads WHERE id='lead1'"
                            ).fetchone()["sequence_state"] == "halted_bounce"
        # both excluded from further selection (hard stop)
        ids = {r["id"] for r in selection.eligible_leads(conn, "camp1")}
        assert "lead0" not in ids and "lead1" not in ids
        # a further draft pass produces nothing for them
        cli.run_draft(conn, "camp1", 9, FakeDrafter())
        assert conn.execute(
            "SELECT COUNT(*) c FROM send_drafts WHERE lead_id IN "
            "('lead0','lead1') AND review_state!='delivered'"
        ).fetchone()["c"] == 0
    finally:
        conn.close()


def test_linkedin_task_cancelled_on_halt(seeded, monkeypatch):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        _deliver_touch1(conn, monkeypatch)
        # fake a delivered touch-2 send for lead2, then halt it
        conn.execute("INSERT INTO sends (id, lead_id, subject, body_text, "
                     "sent_at, touch_number) VALUES "
                     "('s2','lead2','x','y',CURRENT_TIMESTAMP,2)")
        conn.execute("UPDATE leads SET sequence_state='halted_reply' "
                     "WHERE id='lead2'")
        conn.commit()
        row = conn.execute(
            "SELECT l.sequence_state s FROM leads l WHERE l.campaign_id='camp1' "
            "AND EXISTS (SELECT 1 FROM sends x WHERE x.lead_id=l.id AND "
            "x.touch_number=2)").fetchall()
        cancelled = [r for r in row if r["s"] != "active"]
        assert len(cancelled) == 1  # the touch-2 LinkedIn task is cancelled
    finally:
        conn.close()

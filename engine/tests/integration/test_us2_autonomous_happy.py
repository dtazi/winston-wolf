"""US2 happy: autonomous mode advances touch 1→2→3 with the lead's rotation
angles, no operator action, never touch 4."""

from ww_core import db as core_db

from ww_engine import cli, detector, modes, rotation, sender
from ww_engine.drafting.base import DraftRequest, DraftResult


class FakeDrafter:
    def draft(self, req: DraftRequest) -> DraftResult:
        return DraftResult(f"S{req.touch_number}", f"B {req.value_angle}",
                           {"angle": req.value_angle, "touch": req.touch_number},
                           [{"stage": "drafting", "model": "fake",
                             "input_tokens": 10, "output_tokens": 5}])


class FakeTransport:
    def __init__(self):
        self.n = 0

    def send(self, message):
        self.n += 1
        return {"message_id": f"m{self.n}", "conversation_id": f"cv{self.n}",
                "internet_message_id": f"<i{self.n}@x>"}


class EmptyReader:
    def fetch(self):
        return []


def test_autonomous_runs_three_touches_no_operator_action(seeded, monkeypatch):
    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        # enrol one lead, go autonomous
        conn.execute("UPDATE leads SET rotation_group=?, sequence_state='active' "
                     "WHERE id='lead0'", (rotation.group_for_lead("lead0"),))
        conn.execute("UPDATE leads SET rotation_group=NULL WHERE id!='lead0' "
                     "AND campaign_id='camp1'")
        conn.commit()
        modes.set_mode(conn, "camp1", "autonomous")
        grp = rotation.group_for_lead("lead0")
        ft = FakeTransport()

        for touch in (1, 2, 3):
            detector.run_detect(conn, "camp1", EmptyReader())  # keep detect fresh
            c = cli.run_draft(conn, "camp1", 5, FakeDrafter())
            assert c["drafted"] == 1
            # autonomous ⇒ draft is already approved, no operator step
            st = conn.execute(
                "SELECT review_state FROM send_drafts WHERE lead_id='lead0' "
                "AND touch_number=?", (touch,)).fetchone()["review_state"]
            assert st == "approved"
            d = cli.run_deliver(conn, "camp1", ft)
            assert d["delivered"] == 1
            sent = conn.execute(
                "SELECT value_angle, touch_number FROM sends WHERE "
                "lead_id='lead0' AND touch_number=?", (touch,)).fetchone()
            assert sent["value_angle"] == rotation.angle_for(grp, touch)
            # back-date the send so the next touch is due (>=14d)
            conn.execute(
                "UPDATE sends SET sent_at=datetime('now','-15 days') "
                "WHERE lead_id='lead0' AND touch_number=?", (touch,))
            conn.execute("UPDATE leads SET updated_at=datetime('now','-15 days') "
                         "WHERE id='lead0'")
            conn.commit()

        assert conn.execute("SELECT sequence_state FROM leads WHERE id='lead0'"
                            ).fetchone()["sequence_state"] == "completed"
        # never a 4th touch
        cli.run_draft(conn, "camp1", 5, FakeDrafter())
        assert conn.execute(
            "SELECT COUNT(*) c FROM send_drafts WHERE lead_id='lead0'"
        ).fetchone()["c"] == 3
        angles = [r["value_angle"] for r in conn.execute(
            "SELECT value_angle FROM sends WHERE lead_id='lead0' "
            "ORDER BY touch_number")]
        assert sorted(angles) == sorted(rotation.ANGLES)
    finally:
        conn.close()

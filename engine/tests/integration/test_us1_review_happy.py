"""US1 happy path: draft → review → reject/edit/approve-all → deliver."""

from ww_core import db as core_db

from ww_engine import cli, rotation, sender
from ww_engine.drafting.base import DraftRequest, DraftResult


class FakeDrafter:
    def draft(self, req: DraftRequest) -> DraftResult:
        return DraftResult(
            subject=f"Hello (touch {req.touch_number})",
            body_text=f"Body for {req.value_angle}",
            message_recipe={"angle": req.value_angle, "touch": req.touch_number,
                            "personalization_level": req.personalization["level"]},
            token_usage=[{"stage": "drafting", "model": "fake",
                          "input_tokens": 200, "output_tokens": 50}],
        )


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return {"message_id": f"m{len(self.sent)}",
                "conversation_id": f"c{len(self.sent)}",
                "internet_message_id": f"<i{len(self.sent)}@x>"}


def _enroll(conn, campaign):
    for r in conn.execute("SELECT id FROM leads WHERE campaign_id=?", (campaign,)):
        conn.execute(
            "UPDATE leads SET rotation_group=?, sequence_state='active' WHERE id=?",
            (rotation.group_for_lead(r["id"]), r["id"]))
    conn.commit()


def test_review_cycle_end_to_end(seeded, monkeypatch):
    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn, "camp1")
        counts = cli.run_draft(conn, "camp1", batch=9, drafter=FakeDrafter())
        assert counts["drafted"] == 9

        drafts = conn.execute(
            "SELECT id, lead_id FROM send_drafts WHERE campaign_id='camp1' "
            "ORDER BY lead_id").fetchall()
        # nothing delivered yet (review mode, all pending)
        assert conn.execute("SELECT COUNT(*) c FROM sends").fetchone()["c"] == 0

        # reject one, edit one, approve the rest
        cli.modes.set_review_state(conn, drafts[0]["id"], "rejected")
        cli.modes.set_review_state(conn, drafts[1]["id"], "edited",
                                   "Operator rewrote this.")
        conn.execute("UPDATE send_drafts SET review_state='approved' WHERE "
                     "campaign_id='camp1' AND review_state='pending'")
        conn.commit()

        ft = FakeTransport()
        dcounts = cli.run_deliver(conn, "camp1", ft)
        assert dcounts["delivered"] == 8  # 9 minus the rejected one

        # rejected lead never sent
        assert conn.execute(
            "SELECT COUNT(*) c FROM sends WHERE lead_id=?",
            (drafts[0]["lead_id"],)).fetchone()["c"] == 0
        # edited body used
        edited = conn.execute(
            "SELECT body_text FROM sends WHERE lead_id=?",
            (drafts[1]["lead_id"],)).fetchone()
        assert edited["body_text"] == "Operator rewrote this."
        # recipe + sent event + marker header written
        srow = conn.execute(
            "SELECT message_recipe, marker_token, conversation_id FROM sends "
            "WHERE lead_id=?", (drafts[1]["lead_id"],)).fetchone()
        assert srow["message_recipe"] and srow["marker_token"]
        assert srow["conversation_id"]
        assert conn.execute(
            "SELECT COUNT(*) c FROM events WHERE event_type='sent'"
        ).fetchone()["c"] == 8
        assert any(h["name"] == "X-WW-Send"
                   for m in ft.sent for h in m["internetMessageHeaders"])
        # lead advanced to touch 1
        assert conn.execute(
            "SELECT current_touch FROM leads WHERE id=?",
            (drafts[1]["lead_id"],)).fetchone()["current_touch"] == 1
    finally:
        conn.close()

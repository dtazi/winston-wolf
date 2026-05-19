"""US2 error/edge: <14d no follow-up; double draft run no duplicates;
cap mid-batch → capped, resumes remaining next run."""

from ww_core import db as core_db

from ww_engine import cli, modes, rotation, sender
from ww_engine.drafting.base import DraftRequest, DraftResult, DrafterCapReached


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


class CappingDrafter:
    """Drafts `limit` leads then signals the subscription cap."""

    def __init__(self, limit):
        self.limit = limit
        self.calls = 0

    def draft(self, req: DraftRequest) -> DraftResult:
        if self.calls >= self.limit:
            raise DrafterCapReached("usage limit")
        self.calls += 1
        return DraftResult(f"S{req.touch_number}", f"B {req.value_angle}",
                           {"angle": req.value_angle}, [])


def _enroll(conn):
    for r in conn.execute("SELECT id FROM leads WHERE campaign_id='camp1'"):
        conn.execute("UPDATE leads SET rotation_group=?, sequence_state='active' "
                     "WHERE id=?", (rotation.group_for_lead(r["id"]), r["id"]))
    conn.commit()


def test_followup_not_due_before_14_days(seeded, monkeypatch):
    monkeypatch.setattr(sender, "in_send_window", lambda *a, **k: True)
    monkeypatch.setattr(sender, "next_window_slot", lambda *a, **k: None)
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        modes.set_mode(conn, "camp1", "autonomous")
        cli.run_draft(conn, "camp1", 9, FakeDrafter())
        cli.run_deliver(conn, "camp1", FakeTransport())
        # sends are fresh (now) → touch 2 not due
        c = cli.run_draft(conn, "camp1", 9, FakeDrafter())
        assert c["drafted"] == 0  # nothing within 14 days
    finally:
        conn.close()


def test_double_draft_run_is_idempotent(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        modes.set_mode(conn, "camp1", "autonomous")
        c1 = cli.run_draft(conn, "camp1", 9, FakeDrafter())
        c2 = cli.run_draft(conn, "camp1", 9, FakeDrafter())
        assert c1["drafted"] == 9
        assert c2["drafted"] == 0  # all already have a live draft
        assert conn.execute(
            "SELECT COUNT(*) c FROM send_drafts WHERE campaign_id='camp1'"
        ).fetchone()["c"] == 9
    finally:
        conn.close()


def test_cap_midbatch_then_resume(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        _enroll(conn)
        modes.set_mode(conn, "camp1", "autonomous")
        cli.run_draft(conn, "camp1", 9, CappingDrafter(limit=4))  # caps after 4
        made = conn.execute(
            "SELECT COUNT(*) c FROM send_drafts WHERE campaign_id='camp1'"
        ).fetchone()["c"]
        assert made == 4
        last = conn.execute(
            "SELECT outcome FROM engine_runs WHERE pass='draft' "
            "ORDER BY id DESC LIMIT 1").fetchone()["outcome"]
        assert last == "capped"
        # next run (cap lifted) resumes exactly the remaining 5, no dupes
        c = cli.run_draft(conn, "camp1", 9, FakeDrafter())
        assert c["drafted"] == 5
        assert conn.execute(
            "SELECT COUNT(*) c FROM send_drafts WHERE campaign_id='camp1'"
        ).fetchone()["c"] == 9
    finally:
        conn.close()

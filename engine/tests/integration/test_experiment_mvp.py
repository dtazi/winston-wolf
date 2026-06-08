"""MVP loop for the 004 proof-of-life experiment (T011/T012/T020/T021 + US3):
research → grounded draft + reasoning note → review file → verdict+comment →
per-recipient-local deliver → manual reply flag suppresses. All against fakes
(no live M365/LLM)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from ww_core import db as core_db

from ww_engine import cli, feedback, intake, modes, research, selection
from ww_engine.drafting.base import DraftError, DraftResult


# ── fakes ──────────────────────────────────────────────────────────────────

class FakeResearcher:
    def __init__(self, tz="America/Chicago", confidence="high"):
        self.tz, self.confidence = tz, confidence

    def research(self, lead):
        return research.ResearchResult(
            summary="They announced a new wing.",
            signals=[{"type": "expansion", "detail": "new wing"}],
            send_timezone=self.tz, confidence=self.confidence,
            sources=["http://x"])


class FailResearcher:
    def research(self, lead):
        raise research.ResearchError("no sources")


class FakeGroundedDrafter:
    def __init__(self, unsourced=False):
        self.unsourced = unsourced

    def draft(self, req):
        claims = [{"text": "12-week lead time", "source": "kb#lead", "grounded": True}]
        if self.unsourced:
            claims.append({"text": "free sample", "source": None, "grounded": False})
        recipe = {"strategies": ["trigger-opener"], "why": "signal-led",
                  "how_applied": "opened on the wing news", "claims": claims,
                  "engagement_tier": req.engagement_tier or None,
                  "touch": req.touch_number, "drafter": "fake"}
        return DraftResult("Subject line",
                           "Visit https://richbondgroup.eu today", recipe,
                           [{"stage": "drafting", "model": "fake",
                             "input_tokens": 1, "output_tokens": 1}])


class FailDrafter:
    def draft(self, req):
        raise DraftError("drafter failed")


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return {"message_id": "", "conversation_id": "", "internet_message_id": ""}


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture()
def experiment(seeded, tmp_path, monkeypatch):
    """A campaign configured 2/7 with two imported prospects; data dir isolated."""
    monkeypatch.setenv("WW_DATA_DIR", str(tmp_path))
    conn = core_db.get_connection(seeded["db_path"])
    plist = tmp_path / "prospects.yaml"
    plist.write_text(
        "- company: Acme Senior Living\n"
        "  person_name: Jane Doe\n"
        "  person_email: jane@acme.test\n"
        "  notes: announced a new wing\n"
        "- company: Beacon Care\n"
        "  person_name: Bob Roe\n"
        "  person_email: bob@beacon.test\n")
    intake.import_prospects(conn, plist, "camp1")
    conn.execute("UPDATE campaigns SET max_touches=2, touch_gap_days=7 "
                 "WHERE id='camp1'")
    conn.commit()
    return {"conn": conn, "campaign": "camp1", "tmp": tmp_path,
            "db_path": seeded["db_path"]}


# ── US1: research → grounded draft + reasoning note + review file ───────────

def test_us1_draft_writes_grounded_note_and_review_file(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    counts = cli.run_experiment_draft(
        conn, camp, 15, FakeResearcher(), FakeGroundedDrafter())
    assert counts["drafted"] == 2 and counts["researched"] == 2

    d = conn.execute(
        "SELECT * FROM send_drafts WHERE campaign_id=? LIMIT 1", (camp,)
    ).fetchone()
    assert d["review_state"] == "pending"
    import json
    recipe = json.loads(d["message_recipe"])
    assert recipe["strategies"] == ["trigger-opener"] and recipe["why"]

    # research persisted + send_timezone derived onto the lead
    lead = conn.execute("SELECT research, send_timezone FROM leads WHERE id=?",
                        (d["lead_id"],)).fetchone()
    assert lead["send_timezone"] == "America/Chicago" and "new wing" in lead["research"]

    # a markdown review file exists and shows the reasoning note
    rf = feedback.reviews_dir() / f"{d['id']}.md"
    assert rf.exists()
    assert "Reasoning note" in rf.read_text() and "trigger-opener" in rf.read_text()


def test_us1_record_verdict_and_comment(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    cli.run_experiment_draft(conn, camp, 15, FakeResearcher(), FakeGroundedDrafter())
    d = conn.execute("SELECT id FROM send_drafts WHERE campaign_id=? LIMIT 1",
                     (camp,)).fetchone()
    assert modes.set_review_state(conn, d["id"], "approved",
                                  comment="great opener, send it")
    row = conn.execute("SELECT review_state, comment FROM send_drafts WHERE id=?",
                       (d["id"],)).fetchone()
    assert row["review_state"] == "approved" and "great opener" in row["comment"]


def test_us1_unsourced_claim_flagged_and_thin_research(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    # researcher fails (thin) + drafter emits an unsourced claim (Art 17)
    cli.run_experiment_draft(conn, camp, 1, FailResearcher(),
                             FakeGroundedDrafter(unsourced=True))
    d = conn.execute("SELECT id FROM send_drafts WHERE campaign_id=? LIMIT 1",
                     (camp,)).fetchone()
    rf = (feedback.reviews_dir() / f"{d['id']}.md").read_text()
    assert "UNSOURCED" in rf  # the Article-17 flag is surfaced at approval
    assert "thin" in rf       # thin research is flagged, never faked


def test_us1_draft_error_is_skipped(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    counts = cli.run_experiment_draft(conn, camp, 15, FakeResearcher(), FailDrafter())
    assert counts["drafted"] == 0 and counts["skipped"] == 2


# ── US2: per-recipient-local deliver ───────────────────────────────────────

def _draft_and_approve(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    cli.run_experiment_draft(conn, camp, 1, FakeResearcher(tz="America/Chicago"),
                             FakeGroundedDrafter())
    d = conn.execute("SELECT id, lead_id FROM send_drafts WHERE campaign_id=? "
                     "LIMIT 1", (camp,)).fetchone()
    modes.set_review_state(conn, d["id"], "approved")
    conn.execute("UPDATE send_drafts SET scheduled_send_at=NULL WHERE id=?",
                 (d["id"],))
    conn.commit()
    return d


def test_us2_delivers_in_recipient_window(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    d = _draft_and_approve(experiment)
    transport = FakeTransport()
    tue_noon = datetime(2026, 5, 19, 12, 0, tzinfo=ZoneInfo("America/Chicago"))
    counts = cli.run_experiment_deliver(conn, camp, transport, now=tue_noon)
    assert counts["delivered"] == 1
    assert conn.execute("SELECT review_state FROM send_drafts WHERE id=?",
                        (d["id"],)).fetchone()["review_state"] == "delivered"
    # click link wrapped + tracked_links written
    assert "/c/" in transport.sent[0]["body"]["content"]
    assert conn.execute("SELECT COUNT(*) c FROM tracked_links WHERE lead_id=?",
                        (d["lead_id"],)).fetchone()["c"] == 1


def test_us2_outside_window_is_noop(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    _draft_and_approve(experiment)
    mon = datetime(2026, 5, 18, 12, 0, tzinfo=ZoneInfo("America/Chicago"))
    counts = cli.run_experiment_deliver(conn, camp, FakeTransport(), now=mon)
    assert counts["delivered"] == 0 and counts["skipped"] == 1


def test_us2_replied_lead_not_sent(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    d = _draft_and_approve(experiment)
    conn.execute("INSERT INTO events (lead_id, event_type, timestamp) "
                 "VALUES (?, 'replied', CURRENT_TIMESTAMP)", (d["lead_id"],))
    conn.commit()
    tue_noon = datetime(2026, 5, 19, 12, 0, tzinfo=ZoneInfo("America/Chicago"))
    counts = cli.run_experiment_deliver(conn, camp, FakeTransport(), now=tue_noon)
    assert counts["delivered"] == 0 and counts["skipped"] == 1


# ── US3: manual reply flag halts + suppresses (no mail read) ───────────────

def test_us3_flag_replied_halts_and_voids(experiment):
    conn, camp = experiment["conn"], experiment["campaign"]
    cli.run_experiment_draft(conn, camp, 15, FakeResearcher(), FakeGroundedDrafter())
    lead_id = conn.execute("SELECT lead_id FROM send_drafts WHERE campaign_id=? "
                           "LIMIT 1", (camp,)).fetchone()["lead_id"]

    cli.flag_replied(lead=lead_id, category="interested",
                     db_path=experiment["db_path"])

    # halted, reply event recorded with category, drafts voided — all via a
    # fresh connection (flag_replied committed on its own).
    chk = core_db.get_connection(experiment["db_path"])
    try:
        assert chk.execute("SELECT sequence_state FROM leads WHERE id=?",
                           (lead_id,)).fetchone()["sequence_state"] == "halted_reply"
        ev = chk.execute("SELECT payload FROM events WHERE lead_id=? AND "
                         "event_type='replied'", (lead_id,)).fetchone()
        assert ev and "interested" in ev["payload"]
        assert chk.execute(
            "SELECT review_state FROM send_drafts WHERE lead_id=?",
            (lead_id,)).fetchone()["review_state"] == "rejected"
        # no longer eligible for further outreach
        ids = [r["id"] for r in selection.eligible_leads(chk, camp)]
        assert lead_id not in ids
    finally:
        chk.close()


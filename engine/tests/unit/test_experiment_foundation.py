"""Foundational tests for the 004 proof-of-life experiment (T010):
knowledge loaders, config-driven selection + engagement tier, sender tracking
fixes (pixel path + click link-wrapping)."""

from __future__ import annotations

from ww_core import db as core_db

from ww_engine import knowledge, selection, sender


# ── knowledge loaders ──────────────────────────────────────────────────────

def test_knowledge_loaders_happy(tmp_path, monkeypatch):
    monkeypatch.setenv("WW_DATA_DIR", str(tmp_path))
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "knowledge" / "richbond-kb.md").write_text("12-week lead time")
    (tmp_path / "strategies").mkdir()
    (tmp_path / "strategies" / "trigger-opener.md").write_text("open on a signal")
    (tmp_path / "strategies" / "sub-80-words.md").write_text("keep it short")

    assert "12-week" in knowledge.load_kb()
    strats = knowledge.load_strategies()
    assert [s["name"] for s in strats] == ["sub-80-words", "trigger-opener"]

    p = knowledge.append_conclusion("openers beat credibility-first")
    assert "openers beat" in knowledge.load_conclusions()
    assert p.exists()


def test_knowledge_loaders_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("WW_DATA_DIR", str(tmp_path))
    assert knowledge.load_kb() == ""
    assert knowledge.load_strategies() == []
    assert knowledge.load_conclusions() == ""


def test_recent_comments(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        conn.execute(
            "INSERT INTO send_drafts (id, customer_id, campaign_id, lead_id, "
            "touch_number, value_angle, subject, body_text, body_text_original, "
            "message_recipe, personalization_level, review_state, comment) "
            "VALUES ('d1','richbond','camp1','lead0',1,'a','s','b','b','{}',"
            "'web','rejected','wrong tone for this industry')",
        )
        conn.commit()
        assert "wrong tone" in knowledge.recent_comments(conn, "camp1")[0]
    finally:
        conn.close()


# ── selection: config-driven cap/gap + engagement tier ─────────────────────

def test_campaign_sequencing_reads_config(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        # default migration value is the legacy 3/14
        assert selection.campaign_sequencing(conn, "camp1") == (3, 14)
        conn.execute(
            "UPDATE campaigns SET max_touches=2, touch_gap_days=7 WHERE id='camp1'")
        conn.commit()
        assert selection.campaign_sequencing(conn, "camp1") == (2, 7)
    finally:
        conn.close()


def test_engagement_tier(seeded):
    conn = core_db.get_connection(seeded["db_path"])
    try:
        assert selection.engagement_tier(conn, "lead0") == "silent"
        conn.execute(
            "INSERT INTO events (lead_id, event_type, timestamp) "
            "VALUES ('lead0','opened',CURRENT_TIMESTAMP)")
        conn.commit()
        assert selection.engagement_tier(conn, "lead0") == "opened"
        conn.execute(
            "INSERT INTO events (lead_id, event_type, timestamp) "
            "VALUES ('lead0','clicked',CURRENT_TIMESTAMP)")
        conn.commit()
        assert selection.engagement_tier(conn, "lead0") == "clicked"  # click wins
    finally:
        conn.close()


# ── sender: tracking fixes (D10) ───────────────────────────────────────────

def test_html_uses_real_pixel_route_and_wraps_links(monkeypatch):
    monkeypatch.setattr(sender, "_TRACK_BASE", "https://track.test")
    body = "See https://richbondgroup.eu for more.\nThanks"
    links = sender._build_link_map(body)
    assert "https://richbondgroup.eu" in links
    href_map = {u: c for u, (_t, c) in links.items()}
    html = sender._html(body, "PIX", "MARK", href_map)
    assert "https://track.test/p/PIX.gif" in html        # real pixel route
    assert "/c/" in html and 'href="https://track.test/c/' in html  # wrapped
    assert "<!-- ww-marker: MARK -->" in html


class _FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return {"message_id": "", "conversation_id": "", "internet_message_id": ""}


def test_deliver_writes_tracked_links(seeded, monkeypatch):
    monkeypatch.setattr(sender, "_TRACK_BASE", "https://track.test")
    conn = core_db.get_connection(seeded["db_path"])
    try:
        conn.execute(
            "INSERT INTO send_drafts (id, customer_id, campaign_id, lead_id, "
            "touch_number, value_angle, subject, body_text, body_text_original, "
            "message_recipe, personalization_level, review_state) "
            "VALUES ('d1','richbond','camp1','lead0',1,'a','Hi',"
            "'Visit https://richbondgroup.eu today','x','{}','web','approved')")
        conn.commit()
        draft = conn.execute(
            "SELECT * FROM send_drafts WHERE id='d1'").fetchone()
        transport = _FakeTransport()
        sender.deliver_draft(conn, draft, transport)

        # tracked_links row written, pointing at the original url
        link = conn.execute(
            "SELECT original_url, send_id FROM tracked_links WHERE lead_id='lead0'"
        ).fetchone()
        assert link["original_url"] == "https://richbondgroup.eu"
        # the sent HTML wrapped that url through the click redirector
        html = transport.sent[0]["body"]["content"]
        assert f'href="https://track.test/c/' in html
        # draft delivered + sent event recorded
        assert conn.execute(
            "SELECT review_state FROM send_drafts WHERE id='d1'"
        ).fetchone()["review_state"] == "delivered"
    finally:
        conn.close()

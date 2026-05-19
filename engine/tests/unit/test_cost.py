from ww_core import db as core_db

from ww_engine import cost


def test_ledger_records_and_rolls_up(seeded):  # happy path
    conn = core_db.get_connection(seeded["db_path"])
    try:
        cost.record(conn, customer_id="richbond", campaign_id="camp1",
                    stage="research_personalization", model="claude-code:subscription",
                    input_tokens=100, output_tokens=20,
                    lead_id="lead0", send_draft_id="d1")
        cost.record(conn, customer_id="richbond", campaign_id="camp1",
                    stage="drafting", model="claude-code:subscription",
                    input_tokens=300, output_tokens=80,
                    lead_id="lead0", send_draft_id="d1")
        stages = {r["stage"]: r for r in cost.per_stage(conn, "camp1")}
        assert stages["drafting"]["in_tok"] == 300
        pe = cost.per_email(conn, "camp1")
        assert pe["emails"] == 1
        assert pe["tokens_per_email"] == 500.0
    finally:
        conn.close()


def test_per_email_zero_when_no_drafts(seeded):  # error/edge
    conn = core_db.get_connection(seeded["db_path"])
    try:
        assert cost.per_email(conn, "camp1") == {
            "emails": 0, "tokens_per_email": 0.0, "cost_per_email": 0.0}
    finally:
        conn.close()

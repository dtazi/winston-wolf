"""enrichment_ledger writer + rollup (T012)."""

from __future__ import annotations

from ww_scout import cost


def test_record_and_rollup(factory, conn):
    lead = factory.add_lead()
    cost.record(conn, customer_id="richbond", campaign_id=factory.campaign_id,
                lead_id=lead, stage="judge", provider="claude_subscription",
                tokens_in=100, tokens_out=20, status="ok")
    cost.record(conn, customer_id="richbond", campaign_id=factory.campaign_id,
                lead_id=lead, stage="email", provider="hunter",
                cost_usd=0.01, status="ok")
    rows = {r["stage"]: r for r in cost.rollup(conn, factory.campaign_id)}
    assert rows["judge"]["tokens_in"] == 100
    assert rows["email"]["cost_usd"] == 0.01
    assert rows["judge"]["ok"] == 1


def test_record_error_status(factory, conn):
    lead = factory.add_lead()
    cost.record(conn, customer_id="richbond", campaign_id=factory.campaign_id,
                lead_id=lead, stage="domain", provider="tavily",
                status="error", detail="timeout")
    rows = {r["stage"]: r for r in cost.rollup(conn, factory.campaign_id)}
    assert rows["domain"]["errors"] == 1

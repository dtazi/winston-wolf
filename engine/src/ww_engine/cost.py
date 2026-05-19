"""Per-stage token & cost accounting (FR-026/027, SC-011).

Records every model call tagged by stage so the operator can read true
cost-per-email and per-stage, and decide subscription-vs-API from data.
"""

from __future__ import annotations

import sqlite3

# Editable rate table (USD per 1M tokens). 0 while on the Claude Code
# subscription — the point is to measure tokens now, price later.
RATES: dict[str, tuple[float, float]] = {
    "claude-code:subscription": (0.0, 0.0),
}


def record(conn: sqlite3.Connection, *, customer_id: str, campaign_id: str,
           stage: str, model: str, input_tokens: int, output_tokens: int,
           lead_id: str | None = None, send_draft_id: str | None = None) -> None:
    in_rate, out_rate = RATES.get(model, (0.0, 0.0))
    est = (input_tokens / 1e6) * in_rate + (output_tokens / 1e6) * out_rate
    conn.execute(
        """INSERT INTO token_ledger
           (customer_id, campaign_id, lead_id, send_draft_id, stage, model,
            input_tokens, output_tokens, est_cost_usd)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (customer_id, campaign_id, lead_id, send_draft_id, stage, model,
         input_tokens, output_tokens, est),
    )
    conn.commit()


def per_stage(conn: sqlite3.Connection, campaign_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT stage,
                  COUNT(*) AS calls,
                  SUM(input_tokens) AS in_tok,
                  SUM(output_tokens) AS out_tok,
                  ROUND(SUM(est_cost_usd), 4) AS cost_usd
           FROM token_ledger WHERE campaign_id=? GROUP BY stage ORDER BY stage""",
        (campaign_id,),
    ).fetchall()


def per_email(conn: sqlite3.Connection, campaign_id: str) -> dict[str, float]:
    """Average tokens & cost per drafted email (a draft = one email)."""
    row = conn.execute(
        """SELECT COUNT(DISTINCT send_draft_id) AS emails,
                  SUM(input_tokens + output_tokens) AS tok,
                  SUM(est_cost_usd) AS cost
           FROM token_ledger
           WHERE campaign_id=? AND send_draft_id IS NOT NULL""",
        (campaign_id,),
    ).fetchone()
    emails = row["emails"] or 0
    if not emails:
        return {"emails": 0, "tokens_per_email": 0.0, "cost_per_email": 0.0}
    return {
        "emails": emails,
        "tokens_per_email": round((row["tok"] or 0) / emails, 1),
        "cost_per_email": round((row["cost"] or 0.0) / emails, 6),
    }

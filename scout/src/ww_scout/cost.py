"""The enrichment_ledger: one row per paid/AI action (Article 4/10, SC-003).

Engine- and vendor-agnostic — LLM stages record tokens (+ optional cost) from
ww_llm.Usage; search/email stages record vendor cost. `detail` carries a short
reason and MUST NOT contain prospect PII (Article 3).
"""

from __future__ import annotations

import sqlite3
from typing import Optional


def record(
    conn: sqlite3.Connection,
    *,
    customer_id: str,
    campaign_id: str,
    lead_id: Optional[str],
    stage: str,  # 'domain' | 'person' | 'judge' | 'reflection' | 'email'
    provider: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost_usd: Optional[float] = None,
    status: str = "ok",  # 'ok' | 'not_found' | 'error'
    detail: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO enrichment_ledger
            (customer_id, campaign_id, lead_id, stage, provider,
             tokens_in, tokens_out, cost_usd, status, detail)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (customer_id, campaign_id, lead_id, stage, provider,
         tokens_in, tokens_out, cost_usd, status, detail),
    )
    conn.commit()


def rollup(conn: sqlite3.Connection, campaign_id: str) -> list[sqlite3.Row]:
    """Per-stage spend summary for a campaign."""
    return conn.execute(
        """
        SELECT stage,
               COUNT(*)               AS calls,
               SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END)        AS ok,
               SUM(CASE WHEN status='not_found' THEN 1 ELSE 0 END) AS not_found,
               SUM(CASE WHEN status='error' THEN 1 ELSE 0 END)     AS errors,
               COALESCE(SUM(tokens_in), 0)  AS tokens_in,
               COALESCE(SUM(tokens_out), 0) AS tokens_out,
               COALESCE(SUM(cost_usd), 0.0) AS cost_usd
          FROM enrichment_ledger
         WHERE campaign_id = ?
         GROUP BY stage
         ORDER BY stage
        """,
        (campaign_id,),
    ).fetchall()

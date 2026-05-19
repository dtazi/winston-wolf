"""Deterministic lead eligibility (FR-001/002/003/007/009). Pure SQL/code —
no LLM (Article 4 code-first)."""

from __future__ import annotations

import sqlite3

TOUCH_GAP_DAYS = 14
MAX_TOUCHES = 3


def eligible_leads(conn: sqlite3.Connection, campaign_id: str,
                   limit: int | None = None) -> list[sqlite3.Row]:
    """Leads whose next touch is due:
      - enrolled (rotation_group set) and sequence_state='active'
      - current_touch < 3
      - no replied/bounced event (hard stop — FR-007)
      - never sent OR last delivered touch >= 14 days ago (FR-003)
    Ordered oldest-activity first for fair draining; capped by `limit`.
    """
    rows = conn.execute(
        """
        SELECT l.*
        FROM leads l
        WHERE l.campaign_id = ?
          AND l.rotation_group IS NOT NULL
          AND l.sequence_state = 'active'
          AND l.current_touch < ?
          AND NOT EXISTS (
              SELECT 1 FROM events e
              WHERE e.lead_id = l.id
                AND e.event_type IN ('replied','bounced')
          )
          AND (
              l.current_touch = 0
              OR (
                  SELECT MAX(s.sent_at) FROM sends s WHERE s.lead_id = l.id
              ) <= datetime('now', ?)
          )
        ORDER BY l.updated_at ASC
        """,
        (campaign_id, MAX_TOUCHES, f"-{TOUCH_GAP_DAYS} days"),
    ).fetchall()
    return rows if limit is None else rows[:limit]


def is_still_eligible(conn: sqlite3.Connection, lead_id: str) -> bool:
    """Re-check immediately before delivery (FR-009): a reply/bounce or a
    halted state between draft and send cancels the send."""
    row = conn.execute(
        "SELECT sequence_state FROM leads WHERE id=?", (lead_id,)
    ).fetchone()
    if not row or row["sequence_state"] != "active":
        return False
    halted = conn.execute(
        "SELECT 1 FROM events WHERE lead_id=? AND event_type IN "
        "('replied','bounced') LIMIT 1",
        (lead_id,),
    ).fetchone()
    return halted is None

"""Deterministic lead eligibility (FR-001/002/003/007/009). Pure SQL/code —
no LLM (Article 4 code-first)."""

from __future__ import annotations

import sqlite3

# Defaults if a campaign predates the 004 config columns (002 used 3/14;
# the proof-of-life experiment campaigns store max_touches=2, touch_gap_days=7).
TOUCH_GAP_DAYS = 14
MAX_TOUCHES = 3


def campaign_sequencing(conn: sqlite3.Connection,
                        campaign_id: str) -> tuple[int, int]:
    """(max_touches, touch_gap_days) from the campaign row, falling back to the
    002 defaults when the columns are absent/NULL (D3)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(campaigns)")}
    if "max_touches" not in cols or "touch_gap_days" not in cols:
        return MAX_TOUCHES, TOUCH_GAP_DAYS
    row = conn.execute(
        "SELECT max_touches, touch_gap_days FROM campaigns WHERE id=?",
        (campaign_id,),
    ).fetchone()
    if not row:
        return MAX_TOUCHES, TOUCH_GAP_DAYS
    return (row["max_touches"] or MAX_TOUCHES,
            row["touch_gap_days"] or TOUCH_GAP_DAYS)


def eligible_leads(conn: sqlite3.Connection, campaign_id: str,
                   limit: int | None = None) -> list[sqlite3.Row]:
    """Leads whose next touch is due:
      - enrolled (rotation_group set) and sequence_state='active'
      - current_touch < campaign max_touches
      - no replied/bounced event (hard stop — FR-007)
      - never sent OR last delivered touch >= touch_gap_days ago (FR-003)
    Ordered oldest-activity first for fair draining; capped by `limit`.
    """
    max_touches, gap_days = campaign_sequencing(conn, campaign_id)
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
        (campaign_id, max_touches, f"-{gap_days} days"),
    ).fetchall()
    return rows if limit is None else rows[:limit]


def engagement_tier(conn: sqlite3.Connection, lead_id: str) -> str:
    """Strongest engagement signal for a lead: 'clicked' > 'opened' > 'silent'
    (D5). Shapes a follow-up's angle; NEVER an eligibility gate (FR-016b) —
    open tracking is noisy (MPP/proxy prefetch)."""
    for evt in ("clicked", "opened"):
        hit = conn.execute(
            "SELECT 1 FROM events WHERE lead_id=? AND event_type=? LIMIT 1",
            (lead_id, evt),
        ).fetchone()
        if hit:
            return evt
    return "silent"


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

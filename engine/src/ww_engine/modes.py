"""Campaign mode + per-email approval state machine (FR-004/021, Article 6).

Default `review`. `autonomous` only via explicit operator action; reversible.
"""

from __future__ import annotations

import sqlite3

VALID_MODES = ("review", "autonomous")
_TERMINAL = "delivered"


def get_mode(conn: sqlite3.Connection, campaign_id: str) -> str:
    row = conn.execute(
        "SELECT mode FROM campaigns WHERE id=?", (campaign_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"no such campaign: {campaign_id}")
    return row["mode"]


def set_mode(conn: sqlite3.Connection, campaign_id: str, mode: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError(f"invalid mode: {mode}")
    conn.execute(
        "UPDATE campaigns SET mode=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (mode, campaign_id),
    )
    conn.commit()


def set_review_state(conn: sqlite3.Connection, draft_id: str, state: str,
                     new_body: str | None = None) -> bool:
    """Apply an operator decision to one draft. Returns False if the draft is
    missing or already terminal (cannot re-decide a delivered/rejected draft)."""
    row = conn.execute(
        "SELECT review_state FROM send_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if not row or row["review_state"] in (_TERMINAL, "rejected"):
        return False
    if state == "edited" and new_body is not None:
        conn.execute(
            "UPDATE send_drafts SET body_text=?, review_state='edited', "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_body, draft_id),
        )
    else:
        conn.execute(
            "UPDATE send_drafts SET review_state=?, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (state, draft_id),
        )
    conn.commit()
    return True


def deliverable_states(mode: str) -> tuple[str, ...]:
    """Which review_states the deliver pass may send. Identical in both modes
    (autonomous simply auto-creates drafts already `approved`); review mode
    just never reaches `approved` without an operator action."""
    return ("approved", "edited")

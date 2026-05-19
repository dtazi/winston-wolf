"""engine_runs lifecycle: idempotency anchor, resume, fail-loud (Articles 11/12).

A run wraps a cron pass (draft/deliver/detect). Cap or error is recorded so the
operator sees it (Article 11) and so the next run can resume cleanly (FR-006).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from . import logging

# A detect run must have succeeded within this window or draft/deliver refuse
# to advance (never follow up blind — FR-009b).
DETECT_FRESHNESS = timedelta(hours=36)


@contextmanager
def run(conn: sqlite3.Connection, campaign_id: str, pass_name: str):
    """Context manager yielding a mutable counts dict. On clean exit →
    'completed'; on DrafterCapReached → 'capped'; any other exception →
    'error' (re-raised after recording)."""
    cur = conn.execute(
        "INSERT INTO engine_runs (campaign_id, pass, outcome) VALUES (?,?,NULL)",
        (campaign_id, pass_name),
    )
    run_id = cur.lastrowid
    conn.commit()
    counts: dict[str, int] = {}
    logging.log("run_start", campaign_id=campaign_id, pass_name=pass_name,
                run_id=run_id)
    try:
        yield counts
    except Exception as exc:  # noqa: BLE001 - boundary; recorded then re-raised
        outcome = "capped" if exc.__class__.__name__ == "DrafterCapReached" \
            else "error"
        _finish(conn, run_id, outcome, counts, detail=type(exc).__name__)
        logging.log("run_end", campaign_id=campaign_id, pass_name=pass_name,
                    run_id=run_id, outcome=outcome, counts=counts)
        if outcome == "capped":
            return  # capped is an expected stop, not a failure
        raise
    else:
        _finish(conn, run_id, "completed", counts)
        logging.log("run_end", campaign_id=campaign_id, pass_name=pass_name,
                    run_id=run_id, outcome="completed", counts=counts)


def _finish(conn: sqlite3.Connection, run_id: int, outcome: str,
            counts: dict, detail: str | None = None) -> None:
    conn.execute(
        "UPDATE engine_runs SET finished_at=CURRENT_TIMESTAMP, outcome=?, "
        "counts=?, detail=? WHERE id=?",
        (outcome, json.dumps(counts), detail, run_id),
    )
    conn.commit()


def detect_is_fresh(conn: sqlite3.Connection, campaign_id: str) -> bool:
    row = conn.execute(
        "SELECT finished_at FROM engine_runs WHERE campaign_id=? AND pass='detect' "
        "AND outcome='completed' ORDER BY finished_at DESC LIMIT 1",
        (campaign_id,),
    ).fetchone()
    if not row or row[0] is None:
        return False
    finished = row[0]
    if isinstance(finished, str):
        finished = datetime.fromisoformat(finished.replace(" ", "T"))
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - finished <= DETECT_FRESHNESS

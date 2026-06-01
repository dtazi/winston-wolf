"""Connection to the shared lead database + lead-writer with idempotent dedup.

Schema is owned by ww-core. Scout only writes to `leads` and reads `customers`,
`campaigns`, `source_channels` for FK validation. Stays independent of ww-core
as a package so this module is deployable on its own.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Iterable

from .sources.base import IngestedLead

_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_data_dir() -> Path:
    env = os.environ.get("WW_DATA_DIR")
    return Path(env) if env else _REPO_ROOT / "data"


def db_path() -> Path:
    return get_data_dir() / "leads.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def write_leads(
    conn: sqlite3.Connection,
    *,
    customer_id: str,
    campaign_id: str,
    niche_id: str,
    source_channel_id: str,
    leads_iter: Iterable[IngestedLead],
    access_difficulty: str = "free",
) -> tuple[int, int]:
    """Insert new leads, skip dedupe matches. Returns (inserted, skipped).

    Dedup natural key: (campaign_id, source_channel_id, source_record_id).
    """
    inserted = 0
    skipped = 0
    for ingested in leads_iter:
        existing = conn.execute(
            """
            SELECT id FROM leads
             WHERE campaign_id = ?
               AND source_channel_id = ?
               AND source_record_id = ?
            """,
            (campaign_id, source_channel_id, ingested.source_record_id),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        lead_id = f"L-{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO leads (
                id, customer_id, campaign_id, niche_id,
                source_channel_id, source_record_id, access_difficulty,
                company_name, company_domain, company_country, company_region,
                company_size_band,
                person_first_name, person_last_name, person_title,
                person_phone, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id, customer_id, campaign_id, niche_id,
                source_channel_id, ingested.source_record_id, access_difficulty,
                ingested.company_name, ingested.company_domain,
                ingested.company_country, ingested.company_region,
                ingested.company_size_band,
                ingested.person_first_name, ingested.person_last_name,
                ingested.person_title,
                ingested.person_phone, ingested.notes,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted, skipped

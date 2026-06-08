"""Manual prospect intake (D8, FR-001).

Ingests the operator's hand-built list (YAML) into `leads` rows, enrolled and
ready for the nightly draft pass. WW does NOT discover prospects in this phase —
it researches the ones the operator chose.

YAML shape (a list of):
  - company: Acme Senior Living
    person_name: Jane Doe
    person_email: jane@acme.com
    title: Director of Procurement      # optional
    country: United States              # optional (helps tz/research)
    notes: just announced a new wing    # optional
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import yaml

from . import logging, rotation


def import_prospects(conn: sqlite3.Connection, file_path: Path,
                     campaign_id: str) -> dict[str, int]:
    """Insert leads from the YAML list. Idempotent on (campaign, email)."""
    cust = conn.execute(
        "SELECT customer_id FROM campaigns WHERE id=?", (campaign_id,)
    ).fetchone()
    if not cust:
        raise ValueError(f"no such campaign: {campaign_id}")
    customer_id = cust["customer_id"]

    rows = yaml.safe_load(Path(file_path).read_text(encoding="utf-8")) or []
    if not isinstance(rows, list):
        raise ValueError("prospect file must be a YAML list")

    imported = skipped = 0
    for r in rows:
        email = (r.get("person_email") or "").strip()
        if not email:
            skipped += 1
            continue
        exists = conn.execute(
            "SELECT 1 FROM leads WHERE campaign_id=? AND person_email=?",
            (campaign_id, email),
        ).fetchone()
        if exists:
            skipped += 1
            continue
        lead_id = uuid.uuid4().hex
        conn.execute(
            """INSERT INTO leads
                 (id, customer_id, campaign_id, niche_id, source_channel_id,
                  access_difficulty, company_name, company_country,
                  person_first_name, person_title, person_email, email_method,
                  status, rotation_group, sequence_state, current_touch, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lead_id, customer_id, campaign_id, "manual", "manual", "manual",
             (r.get("company") or "").strip() or None,
             (r.get("country") or "").strip() or None,
             (r.get("person_name") or "").strip() or None,
             (r.get("title") or "").strip() or None,
             email, "manual", "cold",
             rotation.group_for_lead(lead_id), "active", 0,
             (r.get("notes") or "").strip() or None),
        )
        imported += 1
    conn.commit()
    logging.log("import_prospects", campaign_id=campaign_id,
                imported=imported, skipped=skipped)
    return {"imported": imported, "skipped": skipped}

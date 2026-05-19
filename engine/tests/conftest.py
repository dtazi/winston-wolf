"""Shared test fixtures: a temp leads.db seeded via ww-core, plus engine migrations."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from ww_core import db as core_db

from ww_engine import db as engine_db


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """A fresh leads.db with ww-core schema + ww-engine migrations applied."""
    p = tmp_path / "leads.db"
    core_db.init_database(p)
    conn = core_db.get_connection(p)
    try:
        engine_db.apply_migrations(conn)
    finally:
        conn.close()
    return p


@pytest.fixture()
def seeded(db_path: Path):
    """A customer + campaign + a handful of leads, ready to enrol."""
    conn = core_db.get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO customers (id, name) VALUES (?, ?)",
            ("richbond", "Richbond"),
        )
        conn.execute(
            "INSERT INTO campaigns (id, customer_id, name) VALUES (?, ?, ?)",
            ("camp1", "richbond", "Pilot"),
        )
        for i in range(9):
            conn.execute(
                """INSERT INTO leads
                   (id, customer_id, campaign_id, niche_id, source_channel_id,
                    company_name, person_email, person_title)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"lead{i}", "richbond", "camp1", "hc_assisted_living",
                    "manual", f"Org {i}", f"buyer{i}@example.com", "Facilities Director",
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return {"db_path": db_path, "customer_id": "richbond", "campaign_id": "camp1"}


def new_id() -> str:
    return uuid.uuid4().hex

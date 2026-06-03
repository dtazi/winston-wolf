"""Shared fixtures: a tmp leads.db seeded via ww-core + factories."""

from __future__ import annotations

import sqlite3
import uuid

import pytest
from ww_core import db as core_db


@pytest.fixture()
def db_path(tmp_path):
    p = tmp_path / "leads.db"
    core_db.init_database(p)  # schema + migrate (003 columns) + seed channels
    return p


@pytest.fixture()
def conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON;")
    yield c
    c.close()


@pytest.fixture()
def factory(conn):
    """Insert customer + campaign, then leads. Returns a small helper object."""

    class _Factory:
        customer_id = "richbond"
        campaign_id = "camp-test"

        def __init__(self) -> None:
            conn.execute(
                "INSERT OR IGNORE INTO customers (id, name) VALUES (?, ?)",
                (self.customer_id, "Richbond"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO campaigns (id, customer_id, name) VALUES (?, ?, ?)",
                (self.campaign_id, self.customer_id, "Test campaign"),
            )
            conn.commit()

        def add_lead(self, *, company_name="Acme Care Center", region="MT",
                     niche="hc_skilled_nursing", size_band="large",
                     domain=None, title=None, **cols) -> str:
            lead_id = f"L-{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO leads (id, customer_id, campaign_id, niche_id,
                    source_channel_id, source_record_id, company_name,
                    company_region, company_size_band, company_domain, person_title)
                VALUES (?, ?, ?, ?, 'manual', ?, ?, ?, ?, ?, ?)
                """,
                (lead_id, self.customer_id, self.campaign_id, niche,
                 lead_id, company_name, region, size_band, domain, title),
            )
            for k, v in cols.items():
                conn.execute(f"UPDATE leads SET {k} = ? WHERE id = ?", (v, lead_id))
            conn.commit()
            return lead_id

    return _Factory()

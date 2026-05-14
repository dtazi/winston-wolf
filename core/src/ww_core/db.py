"""SQLite connection, schema initialization, and source-channel seeding."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_data_dir() -> Path:
    env = os.environ.get("WW_DATA_DIR")
    return Path(env) if env else _REPO_ROOT / "data"


DEFAULT_DB_PATH = get_data_dir() / "leads.db"


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema_sql = (Path(__file__).parent / "schema.sql").read_text()
    conn.executescript(schema_sql)
    conn.commit()


SOURCE_CHANNELS_SEED: list[tuple[str, str, str, str, str | None, str | None]] = [
    # ---- Education ----
    ("ipeds", "IPEDS — Integrated Postsecondary Education Data System",
     "public_record", "free",
     "Federal database of every US postsecondary institution; bed counts, addresses, enrollment.",
     "https://nces.ed.gov/ipeds/"),
    ("acuhoi_directory", "ACUHO-I member directory",
     "directory", "paid_approx",
     "Association of College & University Housing Officers — housing directors at ~900 universities.",
     "https://www.acuho-i.org/"),
    ("tabs_directory", "TABS — The Association of Boarding Schools",
     "directory", "free",
     "Public directory of ~300 boarding schools globally.",
     "https://www.boardingschools.com/"),
    ("nais_directory", "NAIS — National Association of Independent Schools",
     "directory", "paid_approx",
     "Independent schools directory (~1,600), partial public access.",
     "https://www.nais.org/"),
    # ---- Multi-family ----
    ("nmhc_directory", "NMHC — National Multifamily Housing Council",
     "directory", "paid_approx",
     "Top operator rankings + research reports for multi-family operators.",
     "https://www.nmhc.org/"),
    ("shb_top25", "Student Housing Business Top 25",
     "publication", "free",
     "Annual ranking of top student housing operators in North America.",
     "https://studenthousingbusiness.com/"),
    ("coliv_directory", "Co-Liv Association directory",
     "directory", "paid_approx",
     "Global co-living operator directory.",
     "https://www.coliv.io/"),
    # ---- Senior ----
    ("asha_directory", "ASHA — American Seniors Housing Association",
     "directory", "paid",
     "Senior housing operator directory; large operators (premium).",
     "https://www.seniorshousing.org/"),
    ("argentum_directory", "Argentum member directory",
     "directory", "paid_approx",
     "Assisted living + memory care operator directory.",
     "https://www.argentum.org/"),
    ("leadingage_directory", "LeadingAge member directory",
     "directory", "paid_approx",
     "Nonprofit-leaning senior housing, AL, hospice operators.",
     "https://leadingage.org/"),
    ("senior_housing_news_rankings", "Senior Housing News annual rankings",
     "publication", "free",
     "ARGENTUM Top 100 + Top 50 Senior Living Companies, published annually.",
     "https://seniorhousingnews.com/"),
    # ---- Healthcare ----
    ("cms_nursing_home_compare", "CMS Nursing Home Compare",
     "public_record", "free",
     "Federal dataset of every US skilled nursing facility; downloadable in bulk.",
     "https://data.cms.gov/provider-data/topics/nursing-homes"),
    ("state_al_licensure", "State licensure databases (Assisted Living)",
     "public_record", "free",
     "Per-state public records of licensed AL facilities. Quality varies by state.",
     None),
    ("ahca_directory", "AHCA/NCAL — American Health Care Association",
     "directory", "paid_approx",
     "SNF + AL operator directory; bulk data often paid.",
     "https://www.ahcancal.org/"),
    # ---- Cross-cutting signals ----
    ("linkedin_job_postings", "LinkedIn job postings",
     "signal", "free",
     "Operators hiring facilities/procurement roles = active facility = active buyer.",
     "https://www.linkedin.com/jobs/"),
    ("building_permits", "State / local building permit records",
     "signal", "free",
     "New construction signal — property opening in 12-18 months means upcoming bedding buy.",
     None),
    # ---- Catch-all ----
    ("manual", "Manual research",
     "directory", "free",
     "Catch-all for leads added by hand without an external source.",
     None),
]


def seed_source_channels(conn: sqlite3.Connection) -> int:
    cursor = conn.executemany(
        """
        INSERT OR IGNORE INTO source_channels (id, name, type, access_tier, description, url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        SOURCE_CHANNELS_SEED,
    )
    conn.commit()
    return cursor.rowcount


def init_database(db_path: Path = DEFAULT_DB_PATH) -> tuple[Path, int]:
    conn = get_connection(db_path)
    try:
        init_schema(conn)
        new_channels = seed_source_channels(conn)
    finally:
        conn.close()
    return db_path, new_channels

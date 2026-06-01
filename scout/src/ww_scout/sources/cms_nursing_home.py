"""CMS Nursing Home Compare ingester.

Reads CMS's public "Provider Information" CSV and yields one IngestedLead per
facility. Person fields are left blank — CMS provides facility-level data; the
procurement decision-maker is found later by enrichment.

CSV column names vary slightly across CMS releases, so column lookup is
case-insensitive and tolerant of alternative names.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator, Optional

from .base import IngestedLead


_CCN_NAMES = [
    "cms certification number (ccn)",
    "federal provider number",
    "provider id",
    "provnum",
]
_NAME_NAMES = ["provider name", "facility name"]
_CITY_NAMES = ["provider city", "city"]
_STATE_NAMES = ["provider state", "state"]
_BEDS_NAMES = ["number of certified beds", "certified beds", "bedcert"]
_OWNERSHIP_NAMES = ["ownership type", "ownership"]
_PHONE_NAMES = ["provider phone number", "phone"]


class CMSNursingHomeIngester:
    source_channel_id = "cms_nursing_home_compare"

    def __init__(self, csv_path: Path, region_filter: Optional[set[str]] = None):
        self.csv_path = csv_path
        self.region_filter = (
            {s.upper() for s in region_filter} if region_filter else None
        )

    def ingest(self) -> Iterator[IngestedLead]:
        with self.csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = {c.lower(): c for c in (reader.fieldnames or [])}
            for row in reader:
                ccn = _get(row, cols, _CCN_NAMES)
                name = _get(row, cols, _NAME_NAMES)
                if not ccn or not name:
                    continue
                state = _get(row, cols, _STATE_NAMES)
                if self.region_filter and (state or "").upper() not in self.region_filter:
                    continue
                yield IngestedLead(
                    source_record_id=ccn,
                    company_name=name.strip(),
                    company_country="US",
                    company_region=state.upper() if state else None,
                    company_size_band=_beds_to_band(_get(row, cols, _BEDS_NAMES)),
                    person_phone=_get(row, cols, _PHONE_NAMES),
                    notes=_build_notes(row, cols),
                )


def _get(row: dict, cols: dict, candidates: list[str]) -> Optional[str]:
    for n in candidates:
        actual = cols.get(n.lower())
        if actual is not None:
            v = row.get(actual)
            if v is not None and str(v).strip():
                return str(v).strip()
    return None


def _build_notes(row: dict, cols: dict) -> Optional[str]:
    parts = []
    city = _get(row, cols, _CITY_NAMES)
    beds = _get(row, cols, _BEDS_NAMES)
    ownership = _get(row, cols, _OWNERSHIP_NAMES)
    if city:
        parts.append(f"City: {city}")
    if beds:
        parts.append(f"Beds: {beds}")
    if ownership:
        parts.append(f"Ownership: {ownership}")
    return " | ".join(parts) if parts else None


def _beds_to_band(beds: Optional[str]) -> Optional[str]:
    if not beds:
        return None
    try:
        n = int(beds)
    except (TypeError, ValueError):
        return None
    if n < 50:
        return "small"
    if n < 150:
        return "mid"
    return "large"

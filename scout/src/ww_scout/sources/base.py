"""Source ingester protocol + the IngestedLead payload shape.

Every Scout source (CMS Nursing Home Compare, IPEDS, TABS, etc.) implements
SourceIngester. The contract is fixed so adding a new source = adding one class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional, Protocol


@dataclass(slots=True)
class IngestedLead:
    """One company-level lead produced by a source ingester.

    Person fields are intentionally optional — most public datasets are
    facility-level, with no named procurement contact. Enrichment fills those in.
    """
    source_record_id: str
    company_name: str
    company_domain: Optional[str] = None
    company_country: Optional[str] = None
    company_region: Optional[str] = None
    company_size_band: Optional[str] = None
    person_first_name: Optional[str] = None
    person_last_name: Optional[str] = None
    person_title: Optional[str] = None
    person_phone: Optional[str] = None
    notes: Optional[str] = None


class SourceIngester(Protocol):
    source_channel_id: str

    def ingest(self) -> Iterator[IngestedLead]:
        ...

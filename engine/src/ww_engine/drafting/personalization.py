"""Layered personalization context (FR-010).

Floor: official public datasets already mapped in the brief/lead row.
Bonus: the org's own public site / public web (best-effort, deferred fetch).
Richest: LinkedIn (manual during review mode in v1).
If nothing usable: level='thin' so the draft is flagged, never faked.
"""

from __future__ import annotations

from typing import Any


def gather(lead: dict[str, Any]) -> dict[str, Any]:
    """Return {level, facts}. Layered:
      - dataset floor from the lead row (company/title/region/size)
      - sharp facts from `lead.notes` (operator-curated or web-sourced)
    level escalates to 'web' when notes are present, 'thin' when nothing is.
    """
    facts: list[str] = []

    title = (lead.get("person_title") or "").strip()
    company = (lead.get("company_name") or "").strip()
    region = (lead.get("company_region") or "").strip()
    size = (lead.get("company_size_band") or "").strip()

    if company:
        facts.append(f"organization: {company}")
    if title:
        facts.append(f"role: {title}")
    if region:
        facts.append(f"region: {region}")
    if size and size != "unknown":
        facts.append(f"size band: {size}")

    level = "dataset"
    notes = (lead.get("notes") or "").strip()
    if notes:
        for line in notes.splitlines():
            line = line.strip()
            if line:
                facts.append(f"context: {line}")
        level = "web"

    if not facts:
        return {"level": "thin", "facts": []}
    return {"level": level, "facts": facts}

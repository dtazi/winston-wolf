"""Value-angle rotation (FR-011/012, research R6).

Every lead gets all three angles, one per touch. The starting order is one of
three rotation groups, assigned by a stable hash of the lead id so each angle
lands in each touch position ~equally (SC-006) — deterministic, no state,
idempotent re-enrolment.
"""

from __future__ import annotations

import hashlib

ANGLES = ("china_plus_one", "60_years_experience", "trusted_by_heavyweights")

# group -> ordered angles for touches 1,2,3
GROUPS: dict[int, tuple[str, str, str]] = {
    0: ("china_plus_one", "60_years_experience", "trusted_by_heavyweights"),
    1: ("60_years_experience", "trusted_by_heavyweights", "china_plus_one"),
    2: ("trusted_by_heavyweights", "china_plus_one", "60_years_experience"),
}


def group_for_lead(lead_id: str) -> int:
    h = hashlib.sha256(lead_id.encode()).hexdigest()
    return int(h, 16) % 3


def angle_for(rotation_group: int, touch_number: int) -> str:
    """touch_number is 1-based (1..3)."""
    return GROUPS[rotation_group][touch_number - 1]

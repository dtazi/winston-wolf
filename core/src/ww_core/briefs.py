"""Brief YAML loader and light validator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_BRIEF_FIELDS = {
    "id", "customer", "name", "spine_pitch", "sub_niches",
}


def load_brief(path: Path) -> dict[str, Any]:
    """Load and validate a brief YAML. Returns the parsed dict."""
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Brief at {path} is not a YAML mapping")
    missing = REQUIRED_BRIEF_FIELDS - set(data.keys())
    if missing:
        raise ValueError(
            f"Brief at {path} missing required fields: {sorted(missing)}"
        )
    return data


def included_sub_niches(brief: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the sub-niches with included: true."""
    return [n for n in brief.get("sub_niches", []) if n.get("included")]

"""Pitch YAML loader and light validator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_PITCH_FIELDS = {
    "customer", "one_liner", "pains_solved", "differentiation", "cta",
}


def load_pitch(path: Path) -> dict[str, Any]:
    """Load and validate a pitch YAML. Returns the parsed dict."""
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Pitch at {path} is not a YAML mapping")
    missing = REQUIRED_PITCH_FIELDS - set(data.keys())
    if missing:
        raise ValueError(
            f"Pitch at {path} missing required fields: {sorted(missing)}"
        )
    return data

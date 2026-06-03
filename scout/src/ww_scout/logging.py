"""Structured logging for Scout (constitution Article 10).

Every significant action emits one structured record:
  {action, module:"scout", customer_id, campaign_id, lead_id?, ts, **extra}

Article 3: prospect PII (names, emails, domains, free text) must NEVER be
logged. `log_action` rejects a known set of PII keys to enforce this in code,
not by convention — a bug that tries to log an email raises rather than leaks.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_PII_KEYS = frozenset({
    "person_email", "email", "person_first_name", "person_last_name",
    "first_name", "last_name", "name", "company_name", "company_domain",
    "domain", "body", "notes", "description", "ai_reason", "rules_reason",
})

_logger = logging.getLogger("ww_scout")
if not _logger.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)


def log_action(
    action: str,
    *,
    customer_id: str | None = None,
    campaign_id: str | None = None,
    lead_id: str | None = None,
    **extra: Any,
) -> None:
    leaked = _PII_KEYS.intersection(extra)
    if leaked:
        raise ValueError(
            f"refusing to log PII keys {sorted(leaked)} (Article 3)"
        )
    record = {
        "action": action,
        "module": "scout",
        "customer_id": customer_id,
        "campaign_id": campaign_id,
        "lead_id": lead_id,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **extra,
    }
    _logger.info(json.dumps({k: v for k, v in record.items() if v is not None}))

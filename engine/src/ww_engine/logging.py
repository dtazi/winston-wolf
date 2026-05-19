"""Structured logging (constitution Article 10 + Article 3).

Every significant action emits one JSON line: action, module, customer_id,
campaign_id, optional lead_id/send_id, timestamp. Prospect PII (email, name,
body, subject) MUST NEVER be passed here — `log()` rejects suspicious keys so
the rule is enforced, not just documented.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

MODULE = "engine"

# Keys that would carry prospect PII — refused at the boundary (Article 3).
_FORBIDDEN_KEYS = {
    "email", "person_email", "to", "recipient", "name", "person_first_name",
    "person_last_name", "body", "body_text", "subject", "reply_text",
}


def log(action: str, *, customer_id: str | None = None,
        campaign_id: str | None = None, lead_id: str | None = None,
        send_id: str | None = None, **fields: Any) -> None:
    bad = _FORBIDDEN_KEYS & set(fields)
    if bad:
        raise ValueError(
            f"refusing to log prospect PII (Article 3): {sorted(bad)}"
        )
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "action": action,
        "customer_id": customer_id,
        "campaign_id": campaign_id,
        "lead_id": lead_id,
        "send_id": send_id,
        **fields,
    }
    print(json.dumps({k: v for k, v in record.items() if v is not None}),
          file=sys.stderr, flush=True)

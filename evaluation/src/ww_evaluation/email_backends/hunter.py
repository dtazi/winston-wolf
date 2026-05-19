"""Hunter.io email-finder backend adapter.

Hunter's `/v2/email-finder` endpoint takes (first_name, last_name, domain)
and returns its best email guess plus a calibrated confidence `score`
(documented to be useful — ≥90 usually correct, <50 coin flip).

Uses the REST API directly. No first-party Python SDK is officially supported.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .base import EmailResult

HUNTER_URL = "https://api.hunter.io/v2/email-finder"


class HunterBackend:
    name = "hunter"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("HUNTER_API_KEY")
        if not key:
            raise ValueError("HUNTER_API_KEY is not set")
        self._api_key = key
        self._session = requests.Session()

    def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> EmailResult:
        params = {
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
            "api_key": self._api_key,
        }
        response = self._session.get(HUNTER_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        data = (payload or {}).get("data") or {}
        return EmailResult(
            email=data.get("email"),
            score=data.get("score"),
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            source=self.name,
            raw=payload,
        )

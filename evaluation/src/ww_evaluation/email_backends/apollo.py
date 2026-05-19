"""Apollo.io email-finder backend adapter.

Apollo's `/v1/people/match` endpoint takes (first_name, last_name, domain)
and returns a matched person record including email. Apollo's database is
broader than Hunter's (full person+company records), but Hunter is the
focused email-finding specialist — both worth comparing head-to-head.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .base import EmailResult

APOLLO_URL = "https://api.apollo.io/v1/people/match"


class ApolloBackend:
    name = "apollo"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("APOLLO_API_KEY")
        if not key:
            raise ValueError("APOLLO_API_KEY is not set")
        self._api_key = key
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
                "Accept": "application/json",
                # Apollo accepts the key as a header (X-Api-Key) or POST body field;
                # header is cleaner and avoids leaking the key into request logs.
                "X-Api-Key": key,
            }
        )

    def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> EmailResult:
        body = {
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
            # Reveal email is gated behind a paid Apollo plan; we request
            # it anyway and let the response indicate availability.
            "reveal_personal_emails": False,
        }
        response = self._session.post(APOLLO_URL, json=body, timeout=30)
        response.raise_for_status()
        payload = response.json()
        person = (payload or {}).get("person") or {}
        email = person.get("email")
        return EmailResult(
            email=email,
            score=None,  # Apollo doesn't publish a numeric confidence score on match
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            source=self.name,
            raw=payload,
        )

"""Send a single email via Microsoft Graph."""

from __future__ import annotations

import requests

GRAPH_SEND_URL = "https://graph.microsoft.com/v1.0/me/sendMail"


def send_email(access_token: str, to: str, subject: str, body: str) -> None:
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        GRAPH_SEND_URL, headers=headers, json=payload, timeout=30
    )
    if response.status_code != 202:
        raise RuntimeError(
            f"Graph send failed: {response.status_code} {response.text}"
        )

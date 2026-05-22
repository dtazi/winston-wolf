"""Delivery: window gate, marker header, tracking injection, M365 send,
sends-row + sent-event write (FR-009c/016-019, research R3/R5).

The Graph call is behind a Transport so tests inject a fake (Article 11: no
network in unit/integration tests; engine never hard-couples to Graph).
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from . import logging

# Single configured US-business-hours window (FR-016/017). Env-overridable.
_TZ = ZoneInfo(os.environ.get("WW_SEND_TZ", "America/New_York"))
_DAYS = {1, 2, 3}  # Tue, Wed, Thu (Mon=0)
_HOUR_START = int(os.environ.get("WW_SEND_HOUR_START", "9"))
_HOUR_END = int(os.environ.get("WW_SEND_HOUR_END", "11"))
_TRACK_BASE = os.environ.get("WW_TRACKING_BASE_URL", "https://track.example.com")


def in_send_window(now: datetime | None = None) -> bool:
    now = (now or datetime.now(_TZ)).astimezone(_TZ)
    return now.weekday() in _DAYS and _HOUR_START <= now.hour < _HOUR_END


def next_window_slot(now: datetime | None = None) -> str:
    """First moment >= now that is inside the window (UTC ISO string)."""
    from datetime import timedelta

    cur = (now or datetime.now(_TZ)).astimezone(_TZ)
    for _ in range(0, 24 * 14):  # search up to two weeks of hours
        if cur.weekday() in _DAYS and _HOUR_START <= cur.hour < _HOUR_END:
            break
        cur += timedelta(hours=1)
        cur = cur.replace(minute=0, second=0, microsecond=0)
    # SQLite-friendly format (avoids the deprecated TIMESTAMP converter
    # choking on ISO timezone suffixes).
    return cur.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")


class Transport(Protocol):
    def send(self, message: dict[str, Any]) -> dict[str, str]:
        """Return {message_id, conversation_id, internet_message_id}."""
        ...


class GraphTransport:
    """Real Microsoft Graph: create a draft (so we can set a custom header and
    capture ids), then send it."""

    def __init__(self) -> None:
        import os as _os

        import requests
        from dotenv import load_dotenv
        from ww_outreach import auth

        load_dotenv()
        cid = _os.environ["AZURE_CLIENT_ID"]
        tid = _os.environ["AZURE_TENANT_ID"]
        token = auth.acquire_token_silent(cid, tid)
        if not token:
            raise RuntimeError("no M365 session — run `ww-outreach auth`")
        self._token = token
        self._requests = requests

    def send(self, message: dict[str, Any]) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self._token}",
             "Content-Type": "application/json"}
        r = self._requests.post(
            "https://graph.microsoft.com/v1.0/me/messages",
            headers=h, json=message, timeout=30)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Graph create failed: {r.status_code} {r.text}")
        m = r.json()
        s = self._requests.post(
            f"https://graph.microsoft.com/v1.0/me/messages/{m['id']}/send",
            headers=h, timeout=30)
        if s.status_code not in (200, 202):
            raise RuntimeError(f"Graph send failed: {s.status_code} {s.text}")
        return {"message_id": m.get("id", ""),
                "conversation_id": m.get("conversationId", ""),
                "internet_message_id": m.get("internetMessageId", "")}


def _html(body_text: str, pixel_token: str) -> str:
    pixel = f'<img src="{_TRACK_BASE}/pixel/{pixel_token}" width="1" height="1" alt="">'
    paras = "".join(f"<p>{ln}</p>" for ln in body_text.splitlines() if ln.strip())
    return f"<html><body>{paras}{pixel}</body></html>"


def deliver_draft(conn: sqlite3.Connection, draft: sqlite3.Row,
                  transport: Transport) -> str:
    """Send one approved draft. Writes sends + 'sent' event, advances the lead,
    marks the draft delivered. Returns the new send id."""
    send_id = uuid.uuid4().hex
    pixel_token = uuid.uuid4().hex
    marker = draft["id"]  # the draft id doubles as the unique X-WW-Send marker

    message = {
        "subject": draft["subject"],
        "body": {"contentType": "HTML",
                 "content": _html(draft["body_text"], pixel_token)},
        "toRecipients": [{"emailAddress": {"address": _lead_email(conn, draft["lead_id"])}}],
        "internetMessageHeaders": [{"name": "X-WW-Send", "value": marker}],
    }
    sent = transport.send(message)

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
        sep=" ", timespec="seconds")
    conn.execute(
        """INSERT INTO sends (id, lead_id, subject, body_text, sent_at,
               microsoft_message_id, pixel_token, touch_number, value_angle,
               message_recipe, marker_token, conversation_id,
               internet_message_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (send_id, draft["lead_id"], draft["subject"], draft["body_text"], now,
         sent.get("message_id"), pixel_token, draft["touch_number"],
         draft["value_angle"], draft["message_recipe"], marker,
         sent.get("conversation_id"), sent.get("internet_message_id")),
    )
    conn.execute(
        "INSERT INTO events (lead_id, send_id, event_type, timestamp, payload) "
        "VALUES (?,?,'sent',?,?)",
        (draft["lead_id"], send_id, now,
         f'{{"touch":{draft["touch_number"]}}}'),
    )
    conn.execute(
        "UPDATE send_drafts SET review_state='delivered', delivered_send_id=?, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (send_id, draft["id"]),
    )
    seq = "completed" if draft["touch_number"] >= 3 else "active"
    conn.execute(
        "UPDATE leads SET current_touch=?, sequence_state=?, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (draft["touch_number"], seq, draft["lead_id"]),
    )
    conn.commit()
    logging.log("deliver", campaign_id=draft["campaign_id"],
                lead_id=draft["lead_id"], send_id=send_id,
                touch=draft["touch_number"], angle=draft["value_angle"])
    return send_id


def _lead_email(conn: sqlite3.Connection, lead_id: str) -> str:
    return conn.execute(
        "SELECT person_email FROM leads WHERE id=?", (lead_id,)
    ).fetchone()["person_email"]

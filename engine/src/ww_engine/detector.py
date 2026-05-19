"""Reply/bounce detection (FR-009a/b, contracts/detector.md, research R1/R2).

Deterministic match of inbound mail to a send/lead. The mailbox reader is
injectable so tests run without Graph (Article 11).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Protocol

from . import logging

_BOUNCE_SENDERS = ("postmaster@", "mailer-daemon@", "mailerdaemon@")


class MailReader(Protocol):
    def fetch(self) -> list[dict[str, Any]]:
        """Return normalized inbound messages:
        {id, conversation_id, from_addr, headers:{lower:val}, body, refs:[...]}"""
        ...


class GraphMailReader:
    def __init__(self) -> None:
        import os

        import requests
        from dotenv import load_dotenv
        from ww_outreach import auth

        load_dotenv()
        token = auth.acquire_token_silent(os.environ["AZURE_CLIENT_ID"],
                                          os.environ["AZURE_TENANT_ID"])
        if not token:
            raise RuntimeError("no M365 session — run `ww-outreach auth`")
        self._h = {"Authorization": f"Bearer {token}"}
        self._requests = requests

    def fetch(self) -> list[dict[str, Any]]:
        r = self._requests.get(
            "https://graph.microsoft.com/v1.0/me/messages"
            "?$top=50&$orderby=receivedDateTime desc"
            "&$select=id,conversationId,from,internetMessageHeaders,body,"
            "internetMessageId",
            headers=self._h, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Graph read failed: {r.status_code} {r.text}")
        out = []
        for m in r.json().get("value", []):
            hdrs = {h["name"].lower(): h.get("value", "")
                    for h in (m.get("internetMessageHeaders") or [])}
            body = (m.get("body") or {}).get("content", "")
            out.append({
                "id": m.get("id", ""),
                "conversation_id": m.get("conversationId", ""),
                "from_addr": ((m.get("from") or {}).get("emailAddress")
                              or {}).get("address", "").lower(),
                "headers": hdrs,
                "body": body,
                "refs": [],
            })
        return out


def _is_autoreply(msg: dict) -> bool:
    h = msg["headers"]
    return (h.get("auto-submitted", "").lower().startswith("auto-replied")
            or "x-autoreply" in h
            or h.get("precedence", "").lower() in ("bulk", "auto_reply"))


def _is_bounce(msg: dict) -> bool:
    if any(msg["from_addr"].startswith(s) for s in _BOUNCE_SENDERS):
        return True
    ct = msg["headers"].get("content-type", "").lower()
    return "report-type=delivery-status" in ct or "multipart/report" in ct


def classify(conn: sqlite3.Connection, msg: dict) -> tuple[str, str] | None:
    """Return (event_type, lead_id) or None. Auto-replies are ignored."""
    if _is_autoreply(msg):
        return None

    by_conv = conn.execute(
        "SELECT lead_id, marker_token, internet_message_id FROM sends "
        "WHERE conversation_id=? AND conversation_id!=''",
        (msg["conversation_id"],)).fetchone()
    marker_hit = None
    blob = msg["body"] + " " + json.dumps(msg["headers"])
    if not by_conv:
        for s in conn.execute(
            "SELECT lead_id, marker_token, internet_message_id FROM sends "
            "WHERE marker_token IS NOT NULL"):
            if s["marker_token"] and s["marker_token"] in blob:
                marker_hit = s
                break
    hit = by_conv or marker_hit
    if not hit:
        return None
    return ("bounced" if _is_bounce(msg) else "replied"), hit["lead_id"]


def run_detect(conn: sqlite3.Connection, campaign_id: str,
                reader: MailReader) -> dict:
    from . import runs

    with runs.run(conn, campaign_id, "detect") as counts:
        counts.update(replied=0, bounced=0, skipped=0, unmatched=0)
        for msg in reader.fetch():
            res = classify(conn, msg)
            if res is None:
                counts["skipped" if _is_autoreply(msg) else "unmatched"] += 1
                continue
            event_type, lead_id = res
            dup = conn.execute(
                "SELECT 1 FROM events WHERE lead_id=? AND event_type=? AND "
                "payload LIKE ?",
                (lead_id, event_type, f'%"msg":"{msg["id"]}"%')).fetchone()
            if dup:
                continue
            conn.execute(
                "INSERT INTO events (lead_id, event_type, timestamp, payload) "
                "VALUES (?,?,CURRENT_TIMESTAMP,?)",
                (lead_id, event_type,
                 json.dumps({"msg": msg["id"], "rule": "conv_or_marker"})))
            conn.execute(
                "UPDATE leads SET sequence_state=?, updated_at=CURRENT_TIMESTAMP "
                "WHERE id=?",
                ("halted_reply" if event_type == "replied" else "halted_bounce",
                 lead_id))
            # void any non-delivered drafts for this lead (FR-009)
            conn.execute(
                "UPDATE send_drafts SET review_state='rejected', "
                "updated_at=CURRENT_TIMESTAMP WHERE lead_id=? AND "
                "review_state IN ('pending','approved','edited')", (lead_id,))
            conn.commit()
            counts[event_type] += 1
            logging.log("detect_match", campaign_id=campaign_id,
                        lead_id=lead_id, event_type=event_type)
    return counts

"""FastAPI tracking app — open pixel + click redirector.

All logic here is deterministic (no LLM, per constitution Article 4): token
lookups, a timing heuristic for Apple Mail Privacy Protection pre-fetches, and
an event insert.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response

from . import db

app = FastAPI(title="Winston Wolf Tracking", docs_url=None, redoc_url=None)

# 1x1 transparent GIF (43 bytes).
_TRANSPARENT_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)

# Opens firing within this many seconds of send are almost certainly Apple's
# Mail Privacy Protection proxy pre-fetching the image, not a human.
_APPLE_PROXY_WINDOW_SECONDS = 60


def _pixel_response() -> Response:
    return Response(
        content=_TRANSPARENT_GIF,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/p/{pixel_token}")
def pixel(pixel_token: str, request: Request) -> Response:
    # The email embeds /p/<token>.gif; strip the extension if present.
    token = pixel_token[:-4] if pixel_token.endswith(".gif") else pixel_token
    now = datetime.now(timezone.utc)

    conn = db.get_connection()
    try:
        send = db.lookup_send_by_pixel(conn, token)
        if send is not None:
            sent_at = db.parse_db_timestamp(send["sent_at"])
            apple_proxy_likely = False
            if sent_at is not None:
                if sent_at.tzinfo is None:
                    sent_at = sent_at.replace(tzinfo=timezone.utc)
                delta = (now - sent_at).total_seconds()
                apple_proxy_likely = 0 <= delta < _APPLE_PROXY_WINDOW_SECONDS
            db.record_event(
                conn,
                lead_id=send["lead_id"],
                event_type="opened",
                timestamp=now,
                send_id=send["id"],
                payload={
                    "user_agent": request.headers.get("user-agent", ""),
                    "ip": request.client.host if request.client else None,
                    "apple_proxy_likely": apple_proxy_likely,
                },
            )
    finally:
        conn.close()

    # Always return the pixel, even on unknown token — never leak match status.
    return _pixel_response()


@app.get("/c/{click_token}")
def click(click_token: str, request: Request) -> Response:
    now = datetime.now(timezone.utc)
    conn = db.get_connection()
    try:
        link = db.lookup_tracked_link(conn, click_token)
        if link is None:
            return Response(status_code=404, content="Unknown link")
        db.record_event(
            conn,
            lead_id=link["lead_id"],
            event_type="clicked",
            timestamp=now,
            send_id=link["send_id"],
            payload={
                "user_agent": request.headers.get("user-agent", ""),
                "ip": request.client.host if request.client else None,
                "url": link["original_url"],
            },
        )
        target = link["original_url"]
    finally:
        conn.close()

    return RedirectResponse(url=target, status_code=302)

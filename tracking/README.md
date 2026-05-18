# Winston Wolf Tracking

Open-pixel + click-redirector. Writes `opened` and `clicked` events into the
shared lead database (`data/leads.db`). Schema is owned by `ww-core` — run
`ww-core init` first (idempotent; creates the `tracked_links` table this
service depends on).

## Setup

From the `tracking/` directory:

    uv sync

## Run

    uv run ww-tracking serve --host 0.0.0.0 --port 8000

Endpoints:

- `GET /healthz` — liveness check, returns `{"status": "ok"}`.
- `GET /p/{pixel_token}.gif` — returns a 1×1 transparent GIF, logs an `opened`
  event for the matching send. Opens firing within 60s of send are flagged
  `apple_proxy_likely` (Apple Mail Privacy Protection pre-fetch, not a human).
- `GET /c/{click_token}` — logs a `clicked` event, then 302-redirects to the
  link's original URL.

Both endpoints fail safe: an unknown pixel token still returns the GIF (never
leaks whether a token matched); an unknown click token returns 404.

## Production deployment (later)

Not wired yet — these are the steps for when the mission goes live:

1. Small Richbond IT ask: CNAME `track.richbond.ma` → the VPS hostname.
2. On the VPS, front this service with Caddy (one config block, automatic
   Let's Encrypt HTTPS + cert renewal) reverse-proxying to `127.0.0.1:8000`.
3. Run `ww-tracking serve` under systemd so it restarts on reboot/crash.
4. Tracked links in outgoing emails then point at
   `https://track.richbond.ma/c/<token>` and the pixel at
   `https://track.richbond.ma/p/<token>.gif`.

## Not built yet

The send-side integration — rewriting links through the redirector and
injecting the pixel into outgoing email — lives in the Outreach module and is
deferred until the sending pipeline is wired (drafting/sending is last per the
build plan). This service is standalone and testable on its own until then.

# Operations — live state, credentials, what's deployed & done

What is actually true in production right now. **Check here before assuming a
capability doesn't exist** — this file exists because an agent once didn't know
WW had already sent email.

## Email sending (Microsoft 365 / Graph)
- WW **can and has** sent real email. Azure app **"Assistant Mail Djaafar
  (Winston Wolf Outreach)"** is registered by Richbond IT (single-tenant,
  delegated **Mail.Send + Mail.ReadBasic**, public client enabled). The
  `AZURE_CLIENT_ID`/`AZURE_TENANT_ID` live in `outreach/.env` (gitignored;
  public identifiers, not secrets).
- **Two send paths, both are WW:**
  - `ww-outreach send` — standalone, plain-text, **writes NO DB rows** (no
    `sends`/`events`). This is what early manual sends used.
  - engine `deliver` / `GraphTransport` — HTML body + tracking pixel + wrapped
    links + `X-WW-Send` header; **writes** `sends`/`events`/`tracked_links`.
- **History:** ~4 manual sends from Djaafar's Mac (standalone path, before the
  VPS migration) + 2 live smokes from the VPS engine path (2026-06-08).
- **OAuth token:** per-user device-code, stored at
  `~/.winston-wolf/outreach-token.json` (0600). Auto-refreshes on use; a refresh
  token dies after ~90 days unused. **The cron must run as the same OS user that
  ran `ww-outreach auth`** (currently `djaafar`, signed in as his richbond.ma
  mailbox) — the token is read from that user's home.
- Runbook: `specs/004-proof-of-life-experiment/quickstart.md`.

## Tracking
- Live at **https://track.richbondgroup.eu** (container `ww-tracking`), reads the
  bind-mounted `data/leads.db`. Open pixel `/p/<pixel_token>.gif`; click redirect
  `/c/<tracked_links.id>`.
- Tracker logs the **reverse-proxy IP** (172.18.0.1), not the real client IP (no
  `X-Forwarded-For` capture yet).

## Database
- Shared SQLite `data/leads.db` (ww-core schema + ww-engine migrations). Was on
  the **002 schema until 2026-06-08**, now migrated to the 004 schema. A `smoke`
  campaign (+1 lead, smoke sends/events) currently exists — **cleanup pending**.

## Host / edge
- VPS `187.124.209.121` (ssh port 2847). Repo at `/home/djaafar/winston-wolf`.
  Public edge = **traefik** (see architecture.md).

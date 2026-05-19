# Contract — `ww-engine` CLI surface

Typer app (`[project.scripts] ww-engine`), `rich` output, same conventions as `ww-core`/`ww-tracking`. All commands accept `--db PATH` (default `data/leads.db`) and exit non-zero on failure (Article 11 fail-loud). Every command emits structured logs (Article 10).

| Command | Purpose | Key behavior / exit |
|---|---|---|
| `ww-engine init` | Apply idempotent migrations from `schema_engine.sql` | Safe to re-run; reports columns/tables added. |
| `ww-engine enroll --campaign ID` | Assign `rotation_group` + `sequence_state=active` to that campaign's leads (FR-012) | Idempotent; never re-rolls an already-enrolled lead. Prints per-position balance. |
| `ww-engine draft --campaign ID [--batch N]` | **Draft pass** (R5): select eligible, draft via Drafter seam, write `send_drafts`, ledger tokens | Stops cleanly + records `engine_runs.outcome='capped'` on subscription cap; idempotent resume. |
| `ww-engine review --campaign ID` | List `pending` drafts: lead, touch, angle, personalization_level (thin flagged), full body | Read-only. |
| `ww-engine approve DRAFT_ID` / `reject DRAFT_ID` / `edit DRAFT_ID --body-file F` | Per-email decision (FR-021); records action | `edit` keeps `body_text_original`. |
| `ww-engine approve-all --campaign ID` | "Approve all remaining" shortcut | Only affects `pending`. |
| `ww-engine deliver --campaign ID` | **Deliver pass** (R5): inside the window, re-check eligibility, send via `ww-outreach`, inject pixel/click + `X-WW-Send`, write `sends`, log `sent` | No-op (exit 0) outside the window; refuses unapproved drafts in `review` mode; never sends to a halted lead. |
| `ww-engine detect --campaign ID` | **Detect pass** (R1/R2): poll mailbox, write `replied`/`bounced` events, set `sequence_state` | Fail-loud on Graph error → `engine_runs.outcome='error'`. |
| `ww-engine go-autonomous --campaign ID` / `go-review --campaign ID` | Flip `campaigns.mode` (FR-004); reversible | Explicit operator action only. |
| `ww-engine status --campaign ID` | Funnel: per touch/angle counts, sequence states, last run per pass, freshness of detect | Read-only. |
| `ww-engine costs --campaign ID` | Cost-per-email + per-stage rollup from `token_ledger` (SC-011) | Read-only. |

Cron wiring (operator host): `draft` 02:00–06:00 daily; `deliver` hourly; `detect` hourly. See quickstart.md.

# Phase 1 Data Model — Outreach Campaign Engine

All changes are **idempotent** (`ADD COLUMN` guarded by a pragma check; `CREATE TABLE IF NOT EXISTS`), applied by `ww-engine init` from `engine/schema_engine.sql`, layered on top of `ww-core`'s `schema.sql`. Every new table scopes by `customer_id` + `campaign_id` (Article 1; `customer_id` is the v1 tenant key). The existing `sends` / `events` `CHECK` constraints are **not** rebuilt (Article 2) — new lifecycle state lives in `send_drafts`; new event semantics reuse existing `event_type` values with structured `payload`.

## Modified existing tables (additive columns only)

### `campaigns` (+1 column)
| column | type | notes |
|---|---|---|
| `mode` | TEXT NOT NULL DEFAULT `'review'` CHECK (`review`,`autonomous`) | Set to `autonomous` only by explicit operator action; reversible (FR-004). |

### `leads` (+3 columns)
| column | type | notes |
|---|---|---|
| `rotation_group` | INTEGER | 0/1/2, assigned at enrolment (FR-012). NULL = not enrolled in the sequence. |
| `sequence_state` | TEXT DEFAULT `'active'` CHECK (`active`,`halted_reply`,`halted_bounce`,`completed`) | The hard stop sets `halted_*` (FR-007). |
| `current_touch` | INTEGER NOT NULL DEFAULT 0 | Highest delivered touch number (0–3). |

(Existing `leads.status` enum is left untouched; `sequence_state` is the engine's authoritative lifecycle field.)

### `sends` (+6 columns — written at delivery only)
| column | type | notes |
|---|---|---|
| `touch_number` | INTEGER | 1–3. |
| `value_angle` | TEXT CHECK (`china_plus_one`,`60_years_experience`,`trusted_by_heavyweights`) | FR-011. |
| `message_recipe` | TEXT (JSON) | ≥ `{angle, touch, rotation_group, personalization_level, drafter}` (FR-013/SC-004). |
| `marker_token` | TEXT UNIQUE | The `X-WW-Send` value (FR-009c). |
| `conversation_id` | TEXT | Graph conversationId, captured from send response (R1). |
| `internet_message_id` | TEXT | For NDR matching (R2). |

Index: `idx_sends_conversation (conversation_id)`, `idx_sends_marker (marker_token)`.

## New tables

### `send_drafts` — the review/queue lifecycle (avoids the `sends.sent_at NOT NULL` constraint)
| column | type | notes |
|---|---|---|
| `id` | TEXT PRIMARY KEY | UUID. |
| `customer_id` | TEXT NOT NULL | tenant scope (Art. 1). |
| `campaign_id` | TEXT NOT NULL REFERENCES campaigns(id) | |
| `lead_id` | TEXT NOT NULL REFERENCES leads(id) | |
| `touch_number` | INTEGER NOT NULL | |
| `value_angle` | TEXT NOT NULL | from the lead's rotation group + touch |
| `subject` | TEXT NOT NULL | drafted |
| `body_text` | TEXT NOT NULL | current text (operator edits overwrite) |
| `body_text_original` | TEXT NOT NULL | the LLM's original draft, kept for audit |
| `message_recipe` | TEXT NOT NULL (JSON) | |
| `personalization_level` | TEXT CHECK (`dataset`,`site`,`web`,`linkedin`,`thin`) | `thin` ⇒ flagged (FR-010, US1.4) |
| `review_state` | TEXT NOT NULL DEFAULT `'pending'` CHECK (`pending`,`approved`,`edited`,`rejected`,`delivered`) | FR-021 |
| `scheduled_send_at` | TIMESTAMP | next in-window slot (R5) |
| `delivered_send_id` | TEXT REFERENCES sends(id) | set when delivered |
| `created_at` / `updated_at` | TIMESTAMP | |

Uniqueness (idempotency, FR-005): **partial unique index** on `(lead_id, touch_number)` where `review_state != 'rejected'` — a lead can never have two live drafts for the same touch.

### `token_ledger` — per-stage cost accounting (FR-026/027)
| column | type | notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `customer_id` / `campaign_id` | TEXT NOT NULL | scope |
| `lead_id` | TEXT | nullable (run-level calls) |
| `send_draft_id` | TEXT | nullable |
| `stage` | TEXT NOT NULL CHECK (`research_personalization`,`drafting`,`classification`) | FR-026 |
| `model` | TEXT NOT NULL | e.g. `claude-code:opus` |
| `input_tokens` / `output_tokens` | INTEGER NOT NULL | |
| `est_cost_usd` | REAL | from a configurable rate table; 0 while on subscription |
| `occurred_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

Report view: cost per email = sum over stages grouped by `send_draft_id`; per-stage = grouped by `stage` (SC-011).

### `engine_runs` — idempotency, resume, fail-loud (Art. 10/11/12)
| column | type | notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `pass` | TEXT NOT NULL CHECK (`draft`,`deliver`,`detect`) | which cron pass |
| `started_at` / `finished_at` | TIMESTAMP | |
| `outcome` | TEXT CHECK (`completed`,`capped`,`error`) | `capped`/`error` ⇒ operator-visible |
| `counts` | TEXT (JSON) | `{selected, drafted, delivered, replied, bounced, skipped}` |
| `detail` | TEXT | error/diagnosis text (no PII) |

Selection rule (FR-009b safety): the **draft** and **deliver** passes refuse to advance any lead whose campaign has no `detect` run with `outcome='completed'` within the configured freshness window — never follow up blind.

## Eligibility (deterministic, `selection.py`, FR-001/002/003/007/009)

A lead is **eligible for touch N+1** iff: `sequence_state='active'` AND `current_touch = N` AND `N < 3` AND (no prior send OR last delivered touch ≥ 14 days ago) AND no `replied`/`bounced` event AND a fresh successful `detect` run exists. Re-checked again immediately before delivery.

## State transitions

```
lead.sequence_state:  active ──(replied)──▶ halted_reply        (terminal)
                       active ──(bounced)──▶ halted_bounce       (terminal)
                       active ──(touch 3 delivered)──▶ completed  (terminal)

send_draft.review_state:
  pending ─▶ approved ─▶ delivered
  pending ─▶ edited   ─▶ delivered
  pending ─▶ rejected            (terminal; never delivered)
  (autonomous mode: created directly as approved)
  any non-delivered ─▶ (lead halted) ⇒ draft voided, not delivered (FR-009)

campaign.mode:  review ⇄ autonomous   (explicit operator action only, reversible)
```

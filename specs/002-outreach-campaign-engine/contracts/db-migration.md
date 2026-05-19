# Contract — DB migration (`engine/schema_engine.sql`)

Applied by `ww-engine init`. **Idempotent**: re-running is a no-op. Layered on `ww-core/schema.sql`; does not rebuild existing `sends`/`events` CHECK constraints (Article 2).

## Additive columns (guarded — applied only if absent, via `PRAGMA table_info` check in `db.py`)

```
campaigns  + mode TEXT NOT NULL DEFAULT 'review'
                CHECK (mode IN ('review','autonomous'))

leads      + rotation_group  INTEGER
           + sequence_state  TEXT DEFAULT 'active'
                CHECK (sequence_state IN ('active','halted_reply','halted_bounce','completed'))
           + current_touch   INTEGER NOT NULL DEFAULT 0

sends      + touch_number          INTEGER
           + value_angle           TEXT
                CHECK (value_angle IN ('china_plus_one','60_years_experience','trusted_by_heavyweights'))
           + message_recipe        TEXT
           + marker_token          TEXT
           + conversation_id       TEXT
           + internet_message_id   TEXT
```

> SQLite cannot add a `UNIQUE`/`CHECK` to an existing table via `ADD COLUMN`; uniqueness for `sends.marker_token` is enforced by a separate unique index below, and the `value_angle` domain is enforced in code on write (documented deviation, Article 2 over a table rebuild).

## New tables (`CREATE TABLE IF NOT EXISTS`)

`send_drafts`, `token_ledger`, `engine_runs` — full column lists in [data-model.md](../data-model.md).

## Indexes (`CREATE INDEX IF NOT EXISTS`)

```
idx_sends_conversation        ON sends(conversation_id)
idx_sends_marker              ON sends(marker_token)
uq_sends_marker               UNIQUE ON sends(marker_token)        -- WHERE marker_token IS NOT NULL
idx_drafts_campaign_state     ON send_drafts(campaign_id, review_state)
uq_drafts_live_touch          UNIQUE ON send_drafts(lead_id, touch_number)
                                     WHERE review_state != 'rejected'   -- idempotency (FR-005)
idx_ledger_draft              ON token_ledger(send_draft_id)
idx_ledger_campaign_stage     ON token_ledger(campaign_id, stage)
idx_runs_campaign_pass        ON engine_runs(pass, started_at)
```

## Rollback
Additive-only; no destructive migration. A campaign can be abandoned by `sequence_state='completed'` without schema changes. No down-migration needed for v1.

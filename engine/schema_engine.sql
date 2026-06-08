-- ww-engine migrations. Idempotent: layered on ww-core/schema.sql.
-- ADD COLUMN statements are applied conditionally by db.py (SQLite has no
-- ADD COLUMN IF NOT EXISTS); the CREATE/INDEX statements below are safe to
-- re-run as-is.

CREATE TABLE IF NOT EXISTS send_drafts (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    lead_id TEXT NOT NULL REFERENCES leads(id),
    touch_number INTEGER NOT NULL,
    value_angle TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    body_text_original TEXT NOT NULL,
    message_recipe TEXT NOT NULL,
    personalization_level TEXT NOT NULL
        CHECK (personalization_level IN ('dataset','site','web','linkedin','thin')),
    review_state TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_state IN ('pending','approved','edited','rejected','delivered')),
    scheduled_send_at TIMESTAMP,
    delivered_send_id TEXT REFERENCES sends(id),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_drafts_campaign_state
    ON send_drafts(campaign_id, review_state);
-- Idempotency (FR-005): one live draft per (lead, touch).
CREATE UNIQUE INDEX IF NOT EXISTS uq_drafts_live_touch
    ON send_drafts(lead_id, touch_number)
    WHERE review_state != 'rejected';

CREATE TABLE IF NOT EXISTS token_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    lead_id TEXT,
    send_draft_id TEXT,
    stage TEXT NOT NULL
        CHECK (stage IN ('research_personalization','drafting','classification')),
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    est_cost_usd REAL DEFAULT 0,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ledger_draft ON token_ledger(send_draft_id);
CREATE INDEX IF NOT EXISTS idx_ledger_campaign_stage
    ON token_ledger(campaign_id, stage);

CREATE TABLE IF NOT EXISTS engine_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    pass TEXT NOT NULL CHECK (pass IN ('draft','deliver','detect')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    outcome TEXT CHECK (outcome IN ('completed','capped','error')),
    counts TEXT,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_campaign_pass
    ON engine_runs(campaign_id, pass, started_at);

CREATE INDEX IF NOT EXISTS idx_sends_conversation ON sends(conversation_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sends_marker
    ON sends(marker_token) WHERE marker_token IS NOT NULL;

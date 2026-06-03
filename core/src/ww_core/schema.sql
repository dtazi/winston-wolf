-- Winston Wolf lead database — v1 schema.
-- Idempotent: every CREATE uses IF NOT EXISTS so `init` can be re-run safely.

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    pitch_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    name TEXT NOT NULL,
    brief_path TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_campaigns_customer ON campaigns(customer_id);

CREATE TABLE IF NOT EXISTS source_channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL
        CHECK (type IN ('directory', 'public_record', 'publication', 'conference', 'signal')),
    access_tier TEXT NOT NULL
        CHECK (access_tier IN ('free', 'paid_approx', 'paid')),
    description TEXT,
    url TEXT
);

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    niche_id TEXT NOT NULL,
    source_channel_id TEXT NOT NULL REFERENCES source_channels(id),
    source_record_id TEXT,
    access_difficulty TEXT
        CHECK (access_difficulty IN ('free', 'scraped', 'paid', 'manual')),
    company_name TEXT,
    company_domain TEXT,
    company_country TEXT,
    company_region TEXT,
    company_size_band TEXT
        CHECK (company_size_band IN ('small', 'mid', 'large', 'unknown')),
    person_first_name TEXT,
    person_last_name TEXT,
    person_title TEXT,
    person_email TEXT,
    email_confidence INTEGER,
    email_method TEXT
        CHECK (email_method IN ('hunter_email_finder', 'hunter_domain_search_guess', 'directory_listed', 'manual')),
    person_phone TEXT,
    person_linkedin TEXT,
    status TEXT NOT NULL DEFAULT 'cold'
        CHECK (status IN ('cold', 'queued', 'sent', 'opened', 'clicked', 'replied', 'bounced', 'closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_campaign_status ON leads(campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_leads_customer ON leads(customer_id);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source_channel_id);
CREATE INDEX IF NOT EXISTS idx_leads_niche ON leads(niche_id);
CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(company_domain);

CREATE TABLE IF NOT EXISTS sends (
    id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL REFERENCES leads(id),
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    microsoft_message_id TEXT,
    pixel_token TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sends_lead ON sends(lead_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_sends_pixel ON sends(pixel_token);
CREATE INDEX IF NOT EXISTS idx_sends_msft_id ON sends(microsoft_message_id);

-- Tracked links: maps a click token (embedded in an email link) back to its
-- original destination URL, so the redirector can log the click and forward.
CREATE TABLE IF NOT EXISTS tracked_links (
    id TEXT PRIMARY KEY,
    send_id TEXT NOT NULL REFERENCES sends(id),
    lead_id TEXT NOT NULL REFERENCES leads(id),
    original_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracked_links_send ON tracked_links(send_id);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id TEXT NOT NULL REFERENCES leads(id),
    send_id TEXT REFERENCES sends(id),
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'created', 'enriched', 'queued', 'sent', 'opened', 'clicked',
            'replied', 'bounced', 'manual_note', 'status_changed'
        )),
    timestamp TIMESTAMP NOT NULL,
    payload TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_lead_time ON events(lead_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_send ON events(send_id);

-- ── Scout enrichment & qualification (feature 003) ──────────────────────────
-- New leads columns (domain_status, person_status, person_email_status,
-- enrichment_state) are added idempotently by db.migrate_schema(), since SQLite
-- has no "ADD COLUMN IF NOT EXISTS". The tables below are create-if-not-exists.

-- The per-campaign ideal-customer profile — the quality bar (FR-001).
CREATE TABLE IF NOT EXISTS campaign_target_profiles (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    target_roles TEXT NOT NULL,          -- JSON list of title keywords
    niche_id TEXT NOT NULL,
    size_metric TEXT,                    -- e.g. 'beds', 'rooms', 'students'
    size_min INTEGER,                    -- "big enough" threshold (per-campaign)
    regions TEXT NOT NULL,               -- JSON list of {country, state}
    description TEXT NOT NULL,            -- plain-language ICP, fed to the AI judge
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ctp_campaign ON campaign_target_profiles(campaign_id);

-- One live qualification verdict per lead (FR-004/005, R6 idempotency).
CREATE TABLE IF NOT EXISTS qualification_verdicts (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    lead_id TEXT NOT NULL REFERENCES leads(id),
    rules_outcome TEXT NOT NULL CHECK (rules_outcome IN ('pass', 'reject')),
    rules_reason TEXT,
    ai_score INTEGER CHECK (ai_score BETWEEN 0 AND 100),
    ai_confidence TEXT CHECK (ai_confidence IN ('low', 'medium', 'high')),
    ai_reason TEXT,
    engine_used TEXT,
    reflection_applied INTEGER NOT NULL DEFAULT 0,
    verdict TEXT NOT NULL CHECK (verdict IN ('qualified', 'rejected', 'needs_review')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_qv_lead ON qualification_verdicts(lead_id);

-- Per-action cost + audit ledger; engine/vendor-agnostic (Article 4/10, SC-003).
CREATE TABLE IF NOT EXISTS enrichment_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    lead_id TEXT REFERENCES leads(id),
    stage TEXT NOT NULL CHECK (stage IN ('domain', 'person', 'judge', 'reflection', 'email')),
    provider TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    status TEXT CHECK (status IN ('ok', 'not_found', 'error')),
    detail TEXT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ledger_campaign_stage ON enrichment_ledger(campaign_id, stage);

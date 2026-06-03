# Phase 1 Data Model — Scout Enrichment & Qualification

All schema changes are **idempotent** (`ADD COLUMN` guarded by a `PRAGMA
table_info` check; `CREATE TABLE IF NOT EXISTS`) and are **owned by `ww-core`**
(spec assumption): they live in `ww-core`'s `schema.sql` and are applied by
`ww-core init`. Scout reads/writes them but does not own the schema. Every new
table scopes by `customer_id` + `campaign_id` (Article 1; `customer_id` is the v1
tenant key).

## Modified existing table — `leads` (additive columns only)

`company_domain`, `person_first_name`, `person_last_name`, `person_title` already
exist (from the ingest MVP). Add:

| column | type | notes |
|---|---|---|
| `domain_status` | TEXT CHECK (`pending`,`found`,`not_found`) DEFAULT `'pending'` | R3; `not_found` carries a reason in `enrichment_ledger`. |
| `person_status` | TEXT CHECK (`pending`,`found`,`not_found`) DEFAULT `'pending'` | R4. |
| `person_email` | TEXT | filled only for qualified keepers (FR-007). |
| `person_email_status` | TEXT CHECK (`pending`,`verified`,`unverified`,`not_found`) DEFAULT `'pending'` | R5; never silently `verified`. |
| `enrichment_state` | TEXT CHECK (`new`,`enriched`,`qualified`,`rejected`,`needs_review`,`emailed`,`parked`) NOT NULL DEFAULT `'new'` | the authoritative lifecycle for this feature (R6). |

`leads.status` (the ingest enum) is left untouched; `enrichment_state` is this
feature's lifecycle field.

## New table — `campaign_target_profiles` (the ICP)

One row per campaign; the quality bar both layers read (FR-001).

| column | type | notes |
|---|---|---|
| `id` | TEXT PRIMARY KEY | UUID. |
| `customer_id` | TEXT NOT NULL | tenant scope (Art. 1). |
| `campaign_id` | TEXT NOT NULL REFERENCES campaigns(id) | unique per campaign. |
| `target_roles` | TEXT NOT NULL (JSON) | title keywords to match a contact, e.g. `["procurement","facilities","operations"]`. |
| `niche_id` | TEXT NOT NULL | the sub-niche this profile targets. |
| `size_metric` | TEXT | the yardstick, e.g. `"beds"`, `"rooms"`, `"students"`. |
| `size_min` | INTEGER | "big enough" threshold; per-campaign (not hardcoded). |
| `regions` | TEXT NOT NULL (JSON) | in-scope `[{country,state}]`. |
| `description` | TEXT NOT NULL | plain-language ideal-customer description (fed to the AI judge). |
| `created_at` / `updated_at` | TIMESTAMP | |

Unique index: `(campaign_id)` — one live profile per campaign. Validation
(FR-001 / US1.2): required = `target_roles`, `niche_id`, `regions`, `description`;
saving with any missing → error listing what's absent.

## New table — `qualification_verdicts`

One live verdict per lead (R6 idempotency).

| column | type | notes |
|---|---|---|
| `id` | TEXT PRIMARY KEY | UUID. |
| `customer_id` / `campaign_id` | TEXT NOT NULL | scope. |
| `lead_id` | TEXT NOT NULL REFERENCES leads(id) | |
| `rules_outcome` | TEXT NOT NULL CHECK (`pass`,`reject`) | the free deterministic layer (FR-004). |
| `rules_reason` | TEXT | which rule failed (only on `reject`). |
| `ai_score` | INTEGER CHECK (0–100) | NULL when rules rejected (no AI cost incurred). |
| `ai_confidence` | TEXT CHECK (`low`,`medium`,`high`) | |
| `ai_reason` | TEXT | fact-based justification (FR-005, SC-004). |
| `engine_used` | TEXT | which `ww-llm` engine served the judgment (audit). |
| `reflection_applied` | INTEGER (0/1) DEFAULT 0 | FR-012. |
| `verdict` | TEXT NOT NULL CHECK (`qualified`,`rejected`,`needs_review`) | drives `enrichment_state`. |
| `created_at` | TIMESTAMP | |

Partial unique index on `(lead_id)` where it is the current verdict — re-running
qualification does not stack verdicts.

## New table — `enrichment_ledger` (cost + audit, engine/vendor-agnostic)

Every paid or AI action records one row (Article 4 / 10; SC-003).

| column | type | notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `customer_id` / `campaign_id` | TEXT NOT NULL | scope. |
| `lead_id` | TEXT REFERENCES leads(id) | |
| `stage` | TEXT NOT NULL CHECK (`domain`,`person`,`judge`,`reflection`,`email`) | |
| `provider` | TEXT | search/email vendor name, or `ww-llm` engine name. |
| `tokens_in` / `tokens_out` | INTEGER | for LLM stages (from `ww-llm` usage). |
| `cost_usd` | REAL | vendor lookup cost or computed token cost. |
| `status` | TEXT CHECK (`ok`,`not_found`,`error`) | |
| `detail` | TEXT | short reason; never prospect PII (Article 3). |
| `ts` | TIMESTAMP | |

## Engine-room config (NOT a DB table in v1)

`config/engines.yaml` (path overridable via `WW_ENGINES_FILE`). Keys are **env
var names**, never literals (FR-015). Shape:

```yaml
default: claude_subscription
engines:
  claude_subscription: { type: claude_subscription }          # headless `claude` CLI
  deepseek:            { type: deepseek, api_key_env: DEEPSEEK_API_KEY, model: deepseek-chat }
  gpt:                 { type: openai,   api_key_env: OPENAI_API_KEY,   model: gpt-4o }
tools:
  scout: deepseek      # omit a tool → uses `default`
  outreach: claude_subscription
```

A future `tenant_engine_overrides` table can layer per-tenant choices on top
(Article 1 forward-compat); not built in v1.

## Per-lead enrichment state machine (R6)

```
new ──enrich(domain+person)──▶ enriched ──rules reject──▶ rejected
                                   │
                                   └─rules pass─▶ judge ─▶ qualified ──email(keeper)──▶ emailed
                                                        ├─▶ rejected
                                                        └─▶ needs_review   (low-confidence AI)
any stage hard-failure (vendor/AI down) ─▶ parked  (retryable; batch continues)
```

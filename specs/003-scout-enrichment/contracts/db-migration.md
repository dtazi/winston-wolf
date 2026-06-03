# Contract — DB migration (owned by `ww-core`)

Per the spec, the shared schema is **owned by `ww-core`** and extended, not
replaced. These deltas are added to `ww-core`'s `schema.sql` and applied by
`ww-core init` (idempotent — safe to re-run; `ww-core init` already runs on
deploy). Scout does not apply migrations itself; it depends on `ww-core init`
having run. Exact shapes are in data-model.md; this is the idempotency contract.

## Guards (idempotency)

- New columns on `leads`: each guarded by a `PRAGMA table_info(leads)` check so
  `ADD COLUMN` runs at most once. Columns: `domain_status`, `person_status`,
  `person_email`, `person_email_status`, `enrichment_state`.
- New tables: `CREATE TABLE IF NOT EXISTS` for `campaign_target_profiles`,
  `qualification_verdicts`, `enrichment_ledger`.
- Indexes: `CREATE UNIQUE INDEX IF NOT EXISTS` for
  `campaign_target_profiles(campaign_id)`; partial-unique current verdict on
  `qualification_verdicts(lead_id)`; supporting indexes on
  `enrichment_ledger(campaign_id, stage)`.

## Acceptance

- Running `ww-core init` on an existing populated `data/leads.db` adds the columns
  /tables/indexes without touching existing rows and without error on re-run
  (happy + error test, Article 8).
- All new columns have safe defaults (`'pending'` / `'new'`) so existing ingested
  leads become valid `new` enrichment candidates automatically.
- CHECK constraints exactly as in data-model.md.

## Coordination note

`ww-core init` is already part of the deploy runbook and was run during the
tracking deploy. After this migration ships, a re-run of `ww-core init` on the VPS
is the only schema step required before Scout enrichment can run.

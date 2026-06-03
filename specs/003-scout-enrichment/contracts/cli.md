# Contract — `ww-scout` CLI surface (enrichment & qualification)

Extends the existing Typer app (`[project.scripts] ww-scout`, `rich` output). All
new commands accept `--db PATH` (default `data/leads.db`), are scoped by
`--campaign ID` (tenant-resolved), exit non-zero on failure (Article 11
fail-loud), and emit structured logs (Article 10). Existing `ingest` / `status` /
`list-sources` are unchanged.

| Command | Purpose | Key behavior / exit |
|---|---|---|
| `ww-scout set-profile --campaign ID --roles ... --niche ID --size-metric beds --size-min N --regions US:MT,US:WY --description-file F` | Author/update the campaign target profile (ICP) (US1, FR-001) | Validates required fields; errors listing any missing (US1.2). Idempotent upsert (one profile per campaign). |
| `ww-scout show-profile --campaign ID` | Print the stored ICP | Read-only. |
| `ww-scout enrich --campaign ID [--batch N]` | Discover domain + contact person for `new` leads (US2, FR-002/003) | Idempotent (skips `found`/`not_found` per R6); records `enrichment_ledger`; parks a lead on vendor outage, continues batch (Art. 11). |
| `ww-scout qualify --campaign ID [--batch N] [--reflect]` | Rules layer → AI judge on survivors → verdict + rank (US3/US5, FR-004/005/006/012) | Rules-rejected leads incur **no** AI cost; `--reflect` enables the off-by-default self-check; writes `qualification_verdicts`. |
| `ww-scout review --campaign ID` | List qualified leads **ranked** best→worst with score, confidence, reason, and rules-rejected counts | Read-only (FR-006). |
| `ww-scout email --campaign ID [--batch N]` | Uncover verified emails for **qualified keepers only** (US4, FR-007) | Refuses to look up non-qualified leads (SC-003); stores `verified`/`unverified`/`not_found`; ledgers cost. |
| `ww-scout costs --campaign ID` | Per-stage + per-lead cost rollup from `enrichment_ledger` | Read-only. |
| `ww-scout engines [--set TOOL=ENGINE]` | Show the engine-room mapping; assign a tool's engine (writes `config/engines.yaml`) (US6, FR-013/014) | Validates the engine exists; never writes keys (env-only, FR-015). |

**Pipeline order** (also the runbook): `set-profile` → `enrich` → `qualify` →
`review` → `email`. Each stage is independently runnable and resumable.

**Cron wiring (operator host)**: `enrich` + `qualify` nightly per active campaign;
`email` after a human glance at `review`. See quickstart.md.

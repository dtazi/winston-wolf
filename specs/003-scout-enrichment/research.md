# Phase 0 Research — Scout Enrichment & Qualification

Resolves the unknowns named in plan.md. Each item: **Decision** / **Rationale** /
**Alternatives rejected**. Vendor selection (R1) is the one item that needs API
keys and stays open until the bake-off is run; everything else is settled so the
design and most of the build can proceed vendor-neutral.

## R1 — Which search + email vendors (BLOCKED: needs API keys)

**Decision**: Defer the concrete vendor choice to a single run of the existing
`evaluation` harness against the loaded Richbond ground-truth
(`evaluation/.../ground_truth/richbond.yaml`, 195 lines). The harness already has
adapters for `exa`, `tavily`, `brave`, `serper`, `perplexity` (search) and
`hunter`, `apollo` (email). Run: `ww-eval run --customer richbond --backends …`
then `ww-eval score`; record recall per backend in `evaluation/results/history/`
and pick the highest-recall backend per role (domain/person vs email) that meets
the cost bar.

**Rationale**: The bake-off tooling and answer key exist; the only missing input
is keys. Picking by measured recall (Article: results-first) beats guessing.

**Interim**: build against the `SearchBackend`/`EmailBackend` Protocols with a
`null`/stub backend (and a single cheap default wired once one key exists) so the
pipeline is end-to-end testable without keys. Swapping the winner in later is one
adapter assignment.

**Alternatives rejected**: hardcoding one vendor now (locks us in before
evidence); skipping the harness (we already paid to build it).

## R2 — `ww-llm` engine room (engine interface + registry)

**Decision**: A new shared module `ww-llm` exposing one `Engine` Protocol —
`complete(CompletionRequest) -> CompletionResult` where the result carries text +
usage (tokens/cost). A `registry` resolves a **tool name** (e.g. `"scout"`) to an
engine via a config file (`config/engines.yaml`, repo-root or `WW_ENGINES_FILE`),
falling back to a declared `default`. Engines: `claude_subscription` (DEFAULT —
headless `claude -p --output-format json` subprocess, reusing the `ww-engine` 002
pattern), and opt-in API adapters `anthropic_api`, `openai`, `deepseek` (all via
`httpx`). All API keys resolve from **env var names referenced in the config**,
never literals. Usage is captured uniformly into the `enrichment_ledger` (R/cost),
so cost reporting is engine-agnostic.

**Rationale**: Directly delivers the user's per-tool-engine goal (Scout on
DeepSeek/GPT, Outreach on Opus) with config-only provider additions (FR-013/014).
Default-to-subscription means nothing breaks today and there is no mandatory
Anthropic API spend (Article 4).

**Alternatives rejected**: routing app LLM calls through the Zeno sidecar router
(couples the app to Zeno uptime — violates Article 11 "contain failures"); a
Scout-internal seam (not reusable by Outreach later).

## R3 — Domain discovery strategy

**Decision**: From `(company_name, region)` issue a targeted search via the chosen
`SearchBackend`; accept the top result as the official domain only when a
deterministic check passes (name-token overlap with the registered domain /
page title, and not a directory/aggregator host from a denylist). Otherwise record
`domain_status='not_found'` with the reason. Pure-code acceptance check (Article 4).

**Rationale**: Public datasets (CMS included) lack websites; a guarded search is
the cheapest reliable path. Code-level acceptance avoids an LLM call for a
mechanical match.

**Alternatives rejected**: LLM to "pick the website" (Article 4 — deterministic
matching is code); WHOIS/registry lookups (sparse for these niches).

## R4 — Person discovery strategy

**Decision**: Given the domain + the profile's target role, attempt, in order:
(a) the site's team/leadership/contact page parsed in code for a role-matching
name+title; (b) a `SearchBackend` query scoped to the domain for the role. Record
name+title or `person_status='not_found'`. No LLM required for v1.

**Rationale**: Most institutional sites list facilities/procurement/operations
leads; code parsing + scoped search covers the common case cheaply.

**Alternatives rejected**: paid people-data vendor as the primary path (cost,
defer); LinkedIn scraping (ToS/brittle — leave as a manual hook like 002).

## R5 — Email verification threshold

**Decision**: The `EmailBackend` returns a provider confidence; store
`person_email_status='verified'` only at/above a configurable threshold (default
high), else `'unverified'`; never silently promote a guess. `'not_found'` when no
candidate. Threshold is a code constant, overridable per campaign later.

**Rationale**: Spec FR-007 / edge case — a low-confidence guess must never look
verified, or Outreach sends into the void and harms deliverability.

**Alternatives rejected**: accept any returned email (deliverability risk);
SMTP-probe ourselves (reinvents the vendor, risk of blacklisting).

## R6 — Idempotency keys per stage

**Decision**: Each stage is guarded by a per-lead state field so re-runs skip
completed work and never re-charge: `domain_status`, `person_status`,
`enrichment_state`, a live `qualification_verdicts(lead_id)` row, and
`person_email_status`. A stage runs only when its precondition state is unset/
pending. This extends the existing ingest dedup key
`(campaign_id, source_channel_id, source_record_id)`.

**Rationale**: SC-005 (re-run = no duplicates, no repeat charges) and the
paid-lookup-only-on-keepers cost guarantee depend on durable per-stage state.

**Alternatives rejected**: a separate run-log only (doesn't prevent re-charge on
partial failure); recomputing every run (wastes paid lookups).

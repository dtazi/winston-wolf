# Implementation Plan: Scout — Lead Enrichment & Qualification

**Branch**: `003-scout-enrichment` | **Date**: 2026-06-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/003-scout-enrichment/spec.md`

## Summary

Extend the existing `ww-scout` module with the "second half" of Scout: take a
company-level shell lead and (1) discover its official domain + a contact person
matching the campaign's target role, (2) qualify it against a per-campaign
ideal-customer profile using a free deterministic rules layer followed by an AI
fit judgment on the survivors, and (3) uncover a verified email for qualified
keepers only. Deterministic code owns domain parsing, the rules filter, dedup,
idempotency, ranking, and cost accounting; an LLM is used only for the borderline
fit judgment (and an optional, off-by-default self-check pass). All AI calls go
through a new shared `ww-llm` "engine room" — an engine interface + a central
registry that maps each tool to an LLM engine and holds per-engine access from
the environment. The Claude Code subscription is the **default engine** (a
headless `claude` subprocess adapter, reusing the `ww-engine` 002 pattern); API
adapters (Anthropic / OpenAI / DeepSeek) plug in as config, so a tool can be
moved to a different provider with no code change and there is no mandatory
Anthropic API dependency in v1. External search and email vendors
sit behind swappable adapter seams that mirror the `evaluation` harness's
`SearchBackend` protocol; the actual vendors are chosen by running that harness
(Phase 0, needs API keys). The shared schema (owned by `ww-core`) is extended,
not replaced. Adding new data sources stays out of scope.

## Technical Context

**Language/Version**: Python ≥3.11 (matches `ww-core`, `ww-scout`, `ww-engine`, `ww-tracking`)
**Primary Dependencies**: `typer` + `rich` (CLI, as every module); `httpx` (vendor HTTP calls — search + email + LLM-API engines); `ww-core` (path dep — DB + schema); `ww-llm` (new shared path dep — engine registry + adapters; default engine is the headless `claude` subprocess, same seam pattern as `ww-engine`'s Drafter)
**Storage**: existing single SQLite file `data/leads.db`; this feature adds (via `ww-core` schema, applied by `ww-core init`) a `campaign_target_profiles` table, lead enrichment columns, a `qualification_verdicts` record, and an `enrichment_ledger` for paid-lookup + AI-token accounting
**Testing**: `pytest` — ≥1 happy + ≥1 error path per sub-component (Article 8); fake search/email backends + fake judge for integration
**Target Platform**: Linux server (operator-controlled, same Zeno-style host as other modules); runnable on macOS for local review
**Project Type**: single CLI module — extends existing `scout/` (`uv` + `hatchling`, `[project.scripts] ww-scout`)
**Performance Goals**: pilot scale (low hundreds of leads); throughput is a non-goal. Constraint: AI judge batched/throttled under Claude subscription caps; paid lookups minimised by gating behind qualification
**Constraints**: Claude subscription is the default engine (no mandatory Anthropic API dependency in v1); other LLM engines are opt-in via the `ww-llm` registry; paid email lookups only on qualified leads; every stage idempotent and resumable; search/email/LLM vendors all swappable behind adapters
**Scale/Scope**: 1 customer (Richbond), the existing CMS source's leads (plus any future source), enrich + qualify + email over the pilot window

## Constitution Check

*GATE: must pass before Phase 0. Re-checked after Phase 1 (below).*

### Article 1 — Build for Scale from Day One
- [x] `campaign_target_profiles` and all new columns/records scope by `customer_id` + `campaign_id` (the project's de-facto tenant key). No un-scoped queries. ✅

### Article 2 — Simplicity Over Cleverness
- [x] Extends the existing `scout/` module rather than adding infra; reuses the `sources/` framework, the lead-writer, and the harness's adapter pattern. Rules are plain code; AI is added only where judgment is genuinely required. ✅

### Article 3 — Security is Non-Negotiable
- [x] Prospect data (names, emails, titles) never logged in plaintext — logs carry `lead_id` only. ✅
- [x] All vendor + Graph + AI calls are HTTPS; search/email/`CLAUDE_CODE_OAUTH_TOKEN` keys read from env only, never in source. ✅
- [x] Tenant isolation enforced at the query layer (every read/write filtered by `customer_id` + `campaign_id`). ✅
- [ ] **Encrypted at rest**: `data/leads.db` is plain SQLite — a pre-existing, project-wide condition this feature does not change. ❌ → Complexity Tracking (same justification + revisit trigger as 002).

### Article 4 — AI Cost Awareness
- [x] Code-first: domain parsing, the rules filter, dedup, ranking, and verification thresholds are pure code. The LLM is used only for the borderline fit judgment (genuine judgment over ambiguous fit) and the optional reflection pass. ✅
- [x] The AI judge has a fixed input shape (one lead's gathered facts + the campaign ICP — never a whole-DB dump), runs **only on rules-survivors**, is tagged, and its tokens are ledgered via `ww-llm` regardless of which engine serves the call. Reflection is off by default. Paid email lookups run **only on qualified keepers**. ✅
- [x] `ww-llm` lets cost be managed per tool — a cheaper engine (e.g. DeepSeek) can be assigned to high-volume judging while a stronger engine stays on lower-volume, higher-stakes work. ✅

### Article 5 — Modular Architecture
- [x] Lives inside the Scout module; reads/writes the shared DB through `ww-core`'s public surface only; search/email vendors isolated behind adapter Protocols; independently testable. ✅
- [x] No reaching into another module's internals; the email this produces is consumed by Outreach later through the existing lead record, not a private call. ✅
- [x] `ww-llm` is introduced as its own independently-testable shared module (engine interface + registry + adapters), consumed by Scout through its public interface — not Scout-internal. Outreach/Engine migrate onto it later without rework. ✅

### Article 6 — Human Approval Gates
- [~] N/A — this feature does **not** send email; it stops at a ranked ready-to-email list. The send-time approval gate remains in the Outreach/Engine module (002, already satisfied). Qualified leads surface ranked with reasons for human review before they ever reach sending. ⚠ N/A (no send path introduced).

### Article 8 — Testing Standards
- [x] Plan enumerates ≥1 happy + ≥1 error test per sub-component (discovery, rules, judge, email, pipeline) — see Phase 1 / tasks. ✅

### Article 9 — Documentation Separation
- [x] spec.md stays WHAT/WHY; this plan holds all HOW. The per-campaign ICP fields are stated in the spec as inputs, not as a schema design. ✅

### Article 10 — Instrument Everything
- [x] A structured logger is task 1; every significant action (domain-found / not-found, person-found / not-found, rules-reject, ai-score, reflection, email-found / unverified, paid-lookup, run start/end, error) emits `{action, module, customer_id, campaign_id, lead_id?, ts}` — never prospect PII. ✅

### Article 11 — Contain Failures
- [x] Errors caught at the module boundary: a vendor or AI outage parks the affected lead in a `pending` state with a logged reason; the rest of the batch keeps flowing; Scout cannot take down core/engine/tracking. ✅

### Article 12 — Diagnose Before Iterating
- [x] Tasks include an explicit stop-and-diagnose checkpoint after two failed attempts at the same problem (read logs + ledger, write a diagnosis) before a third attempt. ✅

**Gate result**: PROCEED. One ❌ (Article 3 at-rest) carried over from the project-wide SQLite condition + one ⚠ N/A (Article 6, no send path) — both recorded below; neither is a blocker.

## Project Structure

### Documentation (this feature)

```text
specs/003-scout-enrichment/
├── plan.md              # this file
├── research.md          # Phase 0 — vendor bake-off result, AI-judge invocation, discovery strategy, thresholds
├── data-model.md        # Phase 1 — ICP table, lead enrichment columns, verdict + ledger, states
├── contracts/
│   ├── cli.md           # ww-scout enrich / qualify / email / status command surface
│   ├── search-backend.md# company → domain, domain+role → person (swappable adapter contract)
│   ├── email-backend.md # person+domain → verified email (swappable adapter contract)
│   ├── judge.md         # AI fit-judgment in/out contract (score, confidence, reason)
│   └── db-migration.md  # exact idempotent schema deltas (owned by ww-core)
├── quickstart.md        # operator runbook: set ICP → enrich → qualify → review ranked list → email
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
llm/                                # NEW shared module — the "engine room"
├── pyproject.toml                  # ww-llm; uv + hatchling; deps: httpx (for API engines)
├── src/ww_llm/
│   ├── __init__.py
│   ├── base.py                     # Engine Protocol + CompletionRequest/Result (FR-013)
│   ├── registry.py                 # load engine config + per-tool resolution + default fallback (FR-013/014)
│   ├── config.py                   # parse the engine-room config; keys resolved from env only (FR-015)
│   ├── ledger.py                   # token/cost capture, engine-agnostic
│   └── engines/
│       ├── __init__.py
│       ├── claude_subscription.py  # DEFAULT — headless `claude -p` subprocess (reuses 002 pattern)
│       ├── anthropic_api.py        # opt-in API adapter
│       ├── openai.py               # opt-in API adapter (GPT)
│       └── deepseek.py             # opt-in API adapter
└── tests/                          # registry resolution, default fallback, one fake engine, contract

scout/
├── pyproject.toml                  # ww-scout; add httpx; ww-core + ww-llm path deps
├── src/ww_scout/
│   ├── cli.py                      # extend: `enrich`, `qualify`, `email`, richer `status`
│   ├── db.py                       # extend: ICP + enrichment reads/writes (still ww-core-owned schema)
│   ├── logging.py                  # structured logger (Article 10) — built first
│   ├── profile.py                  # Campaign Target Profile (ICP) load + validate (FR-001)
│   ├── pipeline.py                 # orchestration: discover → rules → judge → (keepers) email; idempotent/resumable
│   ├── cost.py                     # enrichment_ledger: paid lookups + AI tokens
│   ├── sources/                    # (existing) ingest framework — unchanged
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── base.py                 # SearchBackend / EmailBackend Protocols + result shapes (mirror evaluation harness)
│   │   ├── domain.py               # company → official domain (FR-002)
│   │   ├── person.py               # domain + target role → contact name+title (FR-003)
│   │   └── email.py                # person + domain → verified email, keepers only (FR-007)
│   └── qualification/
│       ├── __init__.py
│       ├── rules.py                # deterministic hard filter from ICP (FR-004) — pure code, no AI cost
│       ├── judge.py                # AI fit score+confidence+reason via ww-llm (engine for the "scout" tool) (FR-005/013)
│       ├── reflection.py           # optional self-check pass, off by default, also via ww-llm (FR-012)
│       └── ranking.py              # order survivors best→worst (FR-006)
└── tests/
    ├── unit/                       # rules, ranking, profile validation, dedup/idempotency, cost ledger
    ├── integration/                # full discover→rules→judge→email cycle with fake backends + fake judge
    └── contract/                   # SearchBackend / EmailBackend / judge / CLI contracts honored
```

**Structure Decision**: Extend the existing top-level `scout/` module rather than
create a new one — this is literally Scout's second half, and the constitution's
Scout module already owns "discover and qualify leads." Search/email vendors are
isolated behind `enrichment/base.py` Protocols that mirror the `evaluation`
harness's `SearchBackend`, so whichever vendor wins the bake-off drops in as one
adapter file. AI calls go through the new shared `ww-llm` engine room — a
sibling module to `core`/`scout`/`engine` — whose default engine reuses
`ww-engine`'s headless-Claude seam; Scout is its first consumer, and Outreach
migrates onto it later. Building `ww-llm` now (rather than a Scout-internal seam)
is the small extra cost that delivers the per-tool-engine capability immediately.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Article 3 — `leads.db` not encrypted at rest | Pre-existing project-wide choice (`ww-core` owns the plain SQLite file shared by core/tracking/engine); changing it is out of this feature's scope | App-level field encryption now would fork the shared data layer and add key-management complexity disproportionate to a single-operator Phase-1 host. **Mitigation**: host full-disk encryption; secrets via env + 0600 token. **Revisit trigger**: first real second tenant or any non-local DB host (the Postgres migration). |

## Phase 0 — Research

See [research.md](./research.md) (to be generated). Resolves:

1. **Vendor bake-off (BLOCKED — needs API keys).** Run the existing `evaluation`
   harness against the loaded Richbond ground-truth to pick (a) the web-search
   backend for domain + person discovery and (b) the email backend (Hunter vs
   Apollo). Output: a chosen default per role, recorded with recall scores. Until
   keys are provided, the design proceeds vendor-neutral and this step is the one
   gating item before implementation can call real vendors.
2. **AI-judge invocation + `ww-llm` engine room** — confirm the headless
   `claude -p` subprocess pattern from `ww-engine` as the default engine, define
   the engine interface + per-tool registry + config format (env-only keys), the
   structured-output shape (score/confidence/reason), and engine-agnostic token
   capture for the ledger. Sketch the API-engine adapters (Anthropic/OpenAI/
   DeepSeek) so adding one later is config-only.
3. **Domain-discovery strategy** — query patterns from (company_name, region) to a
   confident official domain; how to reject wrong matches.
4. **Person-discovery strategy** — site/about-page parse vs search vs vendor for a
   role-matched contact; what counts as "found".
5. **Email verification** — the confidence threshold above which a result is
   stored "verified" vs "unverified".
6. **Idempotency keys** — per-stage markers so re-runs never re-charge or
   re-process (extends the existing ingest dedup key).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — `campaign_target_profiles`, lead enrichment columns, `qualification_verdicts`, `enrichment_ledger`; the engine-room config shape (tool→engine map + default); per-lead enrichment state machine (`new → enriched → qualified/rejected → emailed`).
- [contracts/](./contracts/) — CLI surface, the two vendor adapter Protocols, the `ww-llm` Engine Protocol + registry contract, the AI-judge contract, and the exact idempotent `ww-core` migration.
- [quickstart.md](./quickstart.md) — operator runbook: author the ICP, run `enrich`, run `qualify`, review the ranked list, run `email`.
- Agent context: `CLAUDE.md` SPECKIT block updated to point here.

**Post-design constitution re-check**: to be confirmed after Phase 1; expected no new violations (the one ❌ is the carried-over at-rest condition).

## Phase 2 — Next

Run `/speckit-tasks` to generate the dependency-ordered `tasks.md`, then
`/speckit-implement`.

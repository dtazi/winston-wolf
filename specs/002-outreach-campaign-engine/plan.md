# Implementation Plan: Outreach Campaign Engine

**Branch**: `002-outreach-campaign-engine` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/002-outreach-campaign-engine/spec.md`

## Summary

Build `ww-engine`: a new, independently-deployable module that turns a configured campaign into a self-running 3-touch email sequence. Deterministic code owns selection, rotation, idempotency, scheduling, the per-send marker, and the reply/bounce hard stop; an LLM is used only for drafting copy (behind a swappable seam) and is invoked headless on the Claude Code subscription off-peak. The module reuses `ww-core` (the lead DB) and `ww-outreach` (M365 send), adds an in-scope M365 reply/bounce poller, a per-email review/approval workflow with explicit operator promotion to autonomous mode, and per-stage token/cost accounting. Lead intake stays out of scope.

## Technical Context

**Language/Version**: Python ≥3.11 (matches `ww-core`, `ww-tracking`, `ww-outreach`)
**Primary Dependencies**: `typer` + `rich` (CLI, as every existing module), `requests` (Microsoft Graph, as `ww-outreach`), `ww-core` (path dep — DB + brief/pitch loaders), `ww-outreach` (path dep — Graph send/auth); headless `claude` CLI invoked as a subprocess for drafting
**Storage**: existing single SQLite file `data/leads.db` via `ww-core`; this feature adds idempotent migrations (new columns + `send_drafts`, `token_ledger`, `engine_runs` tables)
**Testing**: `pytest` (happy + error path per sub-component, Article 8)
**Target Platform**: Linux server controlled by the operator, cron-driven headless (same pattern as the user's Zeno stack); also runnable on macOS for local review
**Project Type**: single CLI module (`uv` + `hatchling`, `[project.scripts] ww-engine`)
**Performance Goals**: pilot scale, low hundreds of leads; throughput is a non-goal. Constraint: drafting batched/throttled to stay under Claude subscription caps
**Constraints**: no Anthropic API dependency in v1 (subscription only); send only inside one configured US-business-hours window; never send after reply/bounce; idempotent and cap-resumable
**Scale/Scope**: 1 customer (Richbond), 1 campaign, ≤ ~3 touches × low-hundreds leads over ~6 weeks

## Constitution Check

*GATE: must pass before Phase 0. Re-checked after Phase 1 (below).*

### Article 1 — Build for Scale from Day One
- [x] All new tables/columns scope by `customer_id` + `campaign_id` (the project's de-facto tenant key; documented in data-model.md). No global/un-scoped queries. ✅

### Article 2 — Simplicity Over Cleverness
- [x] One new module, no new infra, plain SQLite, deterministic code for everything except copy generation. `send_drafts` added rather than rebuilding the existing `sends`/`events` CHECK constraints. ✅

### Article 3 — Security is Non-Negotiable
- [x] Prospect data never logged in plaintext — logs carry `lead_id`/`send_id` only, never email/name/body. ✅
- [x] Graph calls are HTTPS; secrets stay in `outreach/.env` + the 0600 token file (reused, never in source). ✅
- [ ] **Encrypted at rest**: `data/leads.db` is plain SQLite — a pre-existing, project-wide condition this feature does not change. ❌ → recorded in Complexity Tracking with justification + revisit trigger.

### Article 4 — AI Cost Awareness
- [x] Code-first: selection, rotation, idempotency, scheduling, marker, detection matching are pure code. LLM only for copy drafting (NL generation) and reply classification (judgment). ✅
- [x] Every model call has a fixed input shape (the Drafter contract), is tagged by stage, and its tokens are ledgered (FR-026/27). No whole-DB dumps. Caching deferred per Article 4 ("correctness first"). ✅

### Article 5 — Modular Architecture
- [x] New module communicates with `ww-core`/`ww-outreach` through their public APIs only; independently deployable + testable. ✅
- [ ] Reply/bounce detection logically belongs to the **Engagement Tracker** module but is built inside this feature per the `/speckit-clarify` decision. ⚠ → recorded in Complexity Tracking; isolated behind `contracts/detector.md` so it can be extracted later.

### Article 6 — Human Approval Gates
- [x] New campaigns default to `review` mode; `autonomous` requires explicit, reversible per-campaign operator action; no send path exists that bypasses one of the two modes (FR-004/021). ✅ Directly satisfies the article.

### Article 8 — Testing Standards
- [x] Plan enumerates ≥1 happy + ≥1 error test per sub-component (see Phase 1 / tasks). ✅

### Article 9 — Documentation Separation
- [x] spec.md stays WHAT/WHY; this plan holds all HOW. Operator-imposed constraints in the spec (subscription, fixed window) are stated as constraints, not designs. ✅

### Article 10 — Instrument Everything
- [x] A structured logger is task 1; every significant action (select, draft, model-call, queue, approve/reject/edit, schedule, deliver, detect, mode-change, run start/end, cap, error) emits `{action, module, customer_id, campaign_id, lead_id?, ts}`. ✅

### Article 11 — Contain Failures
- [x] Errors caught at the module boundary; detector-unreachable / cap-hit → fail loud, record `engine_runs` row, and the selection pass refuses to advance touches blind (FR-009b/023). Engine cannot take down tracking/core. ✅

### Article 12 — Diagnose Before Iterating
- [x] Tasks include an explicit stop-and-diagnose checkpoint after two failed attempts at the same problem (read logs/`engine_runs`, write a diagnosis) before a third attempt. ✅

**Gate result**: PROCEED. One ❌ (Article 3 at-rest) + one ⚠ (Article 5 detector placement) justified in Complexity Tracking; both are accepted, bounded deviations, not blockers.

## Project Structure

### Documentation (this feature)

```text
specs/002-outreach-campaign-engine/
├── plan.md              # this file
├── research.md          # Phase 0 — resolved unknowns
├── data-model.md        # Phase 1 — schema deltas + entities
├── contracts/
│   ├── cli.md           # ww-engine command surface
│   ├── drafter.md       # FR-015 Drafter seam (in/out contract)
│   ├── detector.md      # inbound reply/bounce → send/lead match contract
│   └── db-migration.md  # exact idempotent schema deltas
├── quickstart.md        # operator runbook (cron entries, review, go-autonomous, costs)
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
engine/
├── pyproject.toml            # ww-engine; uv + hatchling; deps: ww-core, ww-outreach (path), typer, rich, requests
├── schema_engine.sql         # idempotent ALTER/CREATE migrations (applied by `ww-engine init`)
├── src/ww_engine/
│   ├── __init__.py
│   ├── cli.py                # typer app (see contracts/cli.md)
│   ├── db.py                 # ww-core connection + migration apply + queries
│   ├── logging.py            # structured logger (Article 10) — built first
│   ├── runs.py               # engine_runs, idempotency/resume, fail-loud (Art. 11/12)
│   ├── selection.py          # deterministic eligibility (FR-001/002/003/007/009)
│   ├── rotation.py           # 3 rotation groups, balanced assignment (FR-011/012)
│   ├── drafting/
│   │   ├── __init__.py
│   │   ├── base.py           # Drafter Protocol + DraftRequest/DraftResult (FR-015)
│   │   ├── claude_code.py    # ClaudeCodeDrafter — headless `claude -p` (v1 impl)
│   │   └── personalization.py# layered context: datasets/site/web (+ LinkedIn manual hook)
│   ├── sender.py             # ww-outreach send + pixel/click + X-WW-Send marker + window gate (FR-009c/016-019)
│   ├── detector.py           # M365 inbox poll → replied/bounced events (FR-009a/b)
│   ├── modes.py              # review/autonomous + per-email approval state machine (FR-004/021)
│   └── cost.py               # token ledger + per-stage/per-email report (FR-026/027/028)
└── tests/
    ├── unit/                 # selection, rotation, modes, cost, marker
    ├── integration/          # full draft→approve→deliver→detect→hard-stop cycle (fake drafter, fake Graph)
    └── contract/             # Drafter + detector + CLI contracts honored
```

**Structure Decision**: A new top-level `engine/` module mirroring the existing `core/`, `tracking/`, `outreach/`, `evaluation/` layout (own `pyproject.toml`, `src/ww_engine/`, `tests/`, `[project.scripts] ww-engine`). It is the constitution's **Outreach** module's orchestration layer; it depends on `ww-core` and `ww-outreach` as path dependencies and never reaches into their internals.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Article 3 — `leads.db` not encrypted at rest | Pre-existing project-wide choice (`ww-core` owns the plain SQLite file); changing it is out of this feature's scope and would fork the data layer used by `tracking`/`core` | App-level field encryption now would (a) break `ww-core`/`ww-tracking` which read the same file, (b) add key-management complexity disproportionate to a single-operator Phase-1 host. **Mitigation**: rely on host full-disk encryption (FileVault/LUKS); secrets/token already 0600 + gitignored. **Revisit trigger**: first real second tenant or any non-local DB host — becomes a blocking item for the Postgres migration. |
| Article 5 — reply/bounce detector lives in `ww-engine`, not a separate Engagement Tracker module | `/speckit-clarify` Q1 put detection in-scope so the hard stop is real on day one; a separate module now is premature (Article 2) | Splitting it into its own deployable module before it has a second consumer is speculative. **Mitigation**: detector is isolated behind `contracts/detector.md` and a single `detector.py` boundary, so extraction into Engagement Tracker later is a move, not a rewrite. |

## Phase 0 — Research

See [research.md](./research.md). Resolves: M365 reply detection method, M365 bounce/NDR detection, the deliverability-safe per-send marker, headless Claude Code invocation + token capture + cap detection, and the draft/send time-decoupling mechanism.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — schema deltas, new tables, entity states.
- [contracts/](./contracts/) — CLI surface, the Drafter seam, the detector match contract, exact DB migration.
- [quickstart.md](./quickstart.md) — operator runbook + cron layout.
- Agent context updated: `CLAUDE.md` SPECKIT block now points to this plan.

**Post-design constitution re-check**: no new violations introduced by the design; the two tracked deviations are unchanged. Gate still PROCEED.

## Phase 2 — Next

Run `/speckit-tasks` to generate the dependency-ordered `tasks.md`, then `/speckit-implement`.

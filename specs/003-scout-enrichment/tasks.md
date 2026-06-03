---
description: "Task list for Scout Enrichment & Qualification (003)"
---

# Tasks: Scout — Lead Enrichment & Qualification

**Input**: Design documents from `specs/003-scout-enrichment/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: MANDATORY per constitution Article 8 — every module gets ≥1 happy-path + ≥1 error-path test before its story is complete.
**Module roots**: new `llm/` (`ww-llm`, sibling of `core/`) + extend `scout/` (`ww-scout`). Schema deltas land in `ww-core` (applied by `ww-core init`). All paths repo-relative.

User stories (spec.md): **US1** author ICP (P1) · **US2** find person+domain (P1) · **US3** qualify: rules→AI (P1) · **US6** per-tool engine choice (P2) · **US4** email keepers (P2) · **US5** AI reflection (P3). Phase order follows priority + the dependency that qualification (US3) needs the ICP (US1), discovered facts (US2), and the engine room (foundational).

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create `llm/` module structure (`src/ww_llm/`, `src/ww_llm/engines/`, `tests/`) and `llm/pyproject.toml` (`ww-llm`, py>=3.11, deps `httpx`; `[project.scripts]` none; hatchling), then `uv sync` in `llm/`
- [ ] T002 Extend `scout/` structure: add `src/ww_scout/enrichment/`, `src/ww_scout/qualification/`, `tests/{unit,integration,contract}/`; update `scout/pyproject.toml` to add `httpx` + path deps `ww-core`, `ww-llm`; `uv sync`
- [ ] T003 [P] Add pytest config + `conftest.py` to both modules with a tmp `leads.db` fixture seeded via `ww-core` (incl. the new migration) and a profile/lead factory

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ No user-story work begins until this phase is complete.**

- [ ] T004 Implement structured logger `scout/src/ww_scout/logging.py` — emits `{action, module:"scout", customer_id, campaign_id, lead_id?, ts}`; helper asserts no name/email/domain body is ever logged (Article 3 & 10). Built first; every later task uses it
- [ ] T005 Add the idempotent schema deltas to `ww-core`'s `schema.sql` exactly per `contracts/db-migration.md` + `data-model.md` (PRAGMA-guarded `ADD COLUMN` on `leads`; `CREATE TABLE IF NOT EXISTS` for `campaign_target_profiles`, `qualification_verdicts`, `enrichment_ledger`; indexes). Extend `scout/src/ww_scout/db.py` with the enrichment reads/writes
- [ ] T006 [P] Implement `ww-llm` engine seam `llm/src/ww_llm/base.py` — `Engine` Protocol, `CompletionRequest`/`Usage`/`CompletionResult`, `EngineError` per `contracts/engine-registry.md`
- [ ] T007 Implement `llm/src/ww_llm/config.py` + `registry.py` — load `config/engines.yaml` (or `WW_ENGINES_FILE`), `engine_for(tool)` with default fallback, fail-loud on undefined engine / missing env key (FR-013/014/015)
- [ ] T008 Implement the default engine `llm/src/ww_llm/engines/claude_subscription.py` — headless `claude -p --output-format json` subprocess, parse text + usage, `cost_usd=None` (reuses 002 pattern, research R2)
- [ ] T009 [P] Implement `scout/src/ww_scout/cost.py` — `enrichment_ledger` writer (stage-tagged, engine/vendor-agnostic) + per-stage/per-lead rollup query (FR/Article 4, SC-003)
- [ ] T010 [P] Implement enrichment adapter seam `scout/src/ww_scout/enrichment/base.py` — `SearchBackend` + `EmailBackend` Protocols, result dataclasses, `BackendError`, and a `null` stub backend for keyless runs (contracts/search-backend.md, email-backend.md)
- [ ] T011 Implement `scout/src/ww_scout/cli.py` skeleton wiring (`--db`, `--campaign`, log setup) — commands stubbed, filled per story
- [ ] T012 [P] Foundational tests: migration idempotency happy+error (`scout/tests/unit/test_migration.py`); `ww-llm` registry resolution + default fallback + missing-key error (`llm/tests/test_registry.py`); ledger writer happy+error (`scout/tests/unit/test_cost.py`); a fake `Engine` + fake backends contract (`llm/tests/test_engine_contract.py`, `scout/tests/contract/test_backends.py`)

**Checkpoint**: schema migrated, engine room resolves to the subscription default, ledger + adapter seams green.

---

## Phase 3: User Story 1 — Author the ICP (Priority: P1) 🎯 foundation of quality

**Goal**: Operator stores a per-campaign target profile; it is validated and tenant-scoped.

**Independent Test**: `set-profile` then `show-profile` returns it; a profile missing a required field is rejected listing what's absent.

- [ ] T013 [P] [US1] Happy+error tests `scout/tests/unit/test_profile.py` — save+read round-trip; missing `roles`/`regions`/`description` rejected (US1.2)
- [ ] T014 [US1] Implement `scout/src/ww_scout/profile.py` — `CampaignTargetProfile` load/validate/upsert against `campaign_target_profiles` (one per campaign; tenant-scoped) (FR-001)
- [ ] T015 [US1] Implement `set-profile` + `show-profile` commands in `cli.py` per `contracts/cli.md` (`--description-file`, JSON list parsing for roles/regions); log actions

**Checkpoint**: a campaign can carry a validated quality bar.

---

## Phase 4: User Story 2 — Find the person + company website (Priority: P1)

**Goal**: For `new` leads, discover domain + a role-matching contact, idempotently.

**Independent Test**: run `enrich` on a batch with a fake backend → each lead ends `found` (domain+person) or `not_found`; re-run touches nothing; a backend outage parks the lead and the batch continues.

- [ ] T016 [P] [US2] Happy+error tests `scout/tests/integration/test_enrich.py` — found/not_found paths, idempotent re-run (R6), backend outage → `parked` + batch continues (Art. 11), ledger rows written
- [ ] T017 [US2] Implement `scout/src/ww_scout/enrichment/domain.py` — `find_domain` + deterministic acceptance (name-token overlap / denylist, research R3); sets `domain_status`
- [ ] T018 [US2] Implement `scout/src/ww_scout/enrichment/person.py` — site/contact-page parse then scoped search for a role match (research R4); sets `person_status`, name+title
- [ ] T019 [US2] Implement `enrich` command + the per-lead idempotency/state transitions (`new → enriched/parked`) in `cli.py`/`pipeline.py`; ledger each call; log actions (FR-002/003)

**Checkpoint**: shell leads gain a domain + contact, resumably.

---

## Phase 5: User Story 3 — Qualify: rules first, then AI (Priority: P1) 🎯 the quality brain

**Goal**: Free rules layer rejects clear misses (no AI cost); survivors get an AI score+reason; output ranked.

**Independent Test**: a lead outside region is rejected by rules with **zero** AI calls; a passing lead gets score+confidence+reason stored; `review` lists qualified best→worst.

- [ ] T020 [P] [US3] Happy+error tests `scout/tests/integration/test_qualify.py` — rules-reject incurs no engine call (assert via fake engine call-count=0); pass → judged with stored reason; low-confidence → `needs_review`; ranking order correct
- [ ] T021 [US3] Implement `scout/src/ww_scout/qualification/rules.py` — deterministic hard filter from the ICP (region in list, size ≥ `size_min`, niche match, relevant contact present) → `pass`/`reject` + reason (FR-004), pure code
- [ ] T022 [US3] Implement `scout/src/ww_scout/qualification/judge.py` — assemble fixed-shape input (ICP + one lead's facts), call `ww_llm.engine_for("scout")` with `response_schema`, parse score/confidence/reason, map to verdict + threshold, ledger usage (FR-005, contracts/judge.md)
- [ ] T023 [P] [US3] Implement `scout/src/ww_scout/qualification/ranking.py` — order qualified leads by score (FR-006)
- [ ] T024 [US3] Implement `qualify` + `review` commands; write `qualification_verdicts`; transitions (`enriched → qualified/rejected/needs_review`); log actions

**Checkpoint**: leads are scored, ranked, and explainable; rules-rejects cost nothing (SC-002).

---

## Phase 6: User Story 6 — Per-tool engine choice (Priority: P2)

**Goal**: Add LLM engines by config and assign them per tool; Scout's judge honors the assignment.

**Independent Test**: assign `scout` to a fake non-default engine → judge calls it; unassign → falls back to default; adding an engine needs no Scout code change.

- [ ] T025 [P] [US6] Tests `llm/tests/test_engines_api.py` + `scout/tests/integration/test_engine_switch.py` — per-tool resolution end-to-end via the judge; missing-key fail-loud; default fallback
- [ ] T026 [P] [US6] Implement API engine adapters `llm/src/ww_llm/engines/{anthropic_api,openai,deepseek}.py` via `httpx` (key from env-named config, usage→cost) per contracts/engine-registry.md
- [ ] T027 [US6] Implement `ww-scout engines [--set TOOL=ENGINE]` command — show/edit `config/engines.yaml`, validate engine exists, never write keys (FR-014/015)

**Checkpoint**: Scout can run on DeepSeek/GPT/Opus by config alone.

---

## Phase 7: User Story 4 — Uncover verified emails for keepers (Priority: P2)

**Goal**: Paid email lookup only on qualified leads; verified vs unverified honored.

**Independent Test**: `email` looks up only `qualified` leads (assert zero lookups for rejected — SC-003); low provider confidence stored `unverified`; cost ledgered.

- [ ] T028 [P] [US4] Happy+error tests `scout/tests/integration/test_email.py` — keepers-only gate (rejected-lead lookups = 0), verified/unverified/not_found mapping (R5), outage → `parked`, cost rows
- [ ] T029 [US4] Implement `scout/src/ww_scout/enrichment/email.py` — `find_email` on keepers, map provider confidence to `verified`/`unverified` at the R5 threshold; never log the email (Art. 3)
- [ ] T030 [US4] Implement `email` command + transition (`qualified → emailed`); ledger every lookup cost (FR-007, SC-003)

**Checkpoint**: qualified leads carry a verified email — ready for Outreach.

---

## Phase 8: User Story 5 — Optional AI reflection (Priority: P3)

- [ ] T031 [P] [US5] Tests `scout/tests/integration/test_reflection.py` — off → one engine call; on → second review runs, may revise, `reflection_applied=1`, both recorded
- [ ] T032 [US5] Implement `scout/src/ww_scout/qualification/reflection.py` + `--reflect` flag on `qualify` (FR-012)

---

## Phase 9: Polish & Cross-Cutting

- [ ] T033 [P] Implement `costs` command rollup view + `status` enrichment funnel additions (per-state counts, ledger totals)
- [ ] T034 [P] End-to-end integration test `scout/tests/integration/test_pipeline_e2e.py` — ingest→set-profile→enrich→qualify→email with fake backends + fake engine; asserts SC-001/003/005
- [ ] T035 [P] Security pass — grep tests proving no PII (name/email/domain) reaches logs (Article 3); confirm all keys env-sourced
- [ ] T036 [P] Update `scout/README.md` ("What's not built yet" → built) and `CLAUDE.md` SPECKIT block to point at this plan; add `llm/` to the repo README pillar list
- [ ] T037 **Vendor bake-off (BLOCKED: needs API keys)** — run `ww-eval` per quickstart, record recall in `evaluation/results/history/`, wire the winning `SearchBackend`/`EmailBackend` into Scout config. The only step that requires keys + real spend; everything above is testable against the `null`/fake backends without it.

---

## Dependencies & parallel notes

- Phase 2 blocks everything. Within it, T006/T009/T010/T012 are `[P]` (different files).
- US1 (P3-phase) → US2 → US3 is the critical path (qualify needs profile + facts + engine room). US6 and US4 depend on the engine room / qualification respectively; US5 depends on the judge.
- `[P]` = different files, no ordering dependency. Tests precede their implementation within each story (Article 8).
- **Diagnose-before-iterating (Article 12)**: if any task fails twice, stop, read logs + `enrichment_ledger`, write a diagnosis before a third attempt.

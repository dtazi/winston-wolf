---
description: "Task list for Outreach Campaign Engine (002)"
---

# Tasks: Outreach Campaign Engine

**Input**: Design documents from `specs/002-outreach-campaign-engine/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: MANDATORY per constitution Article 8 — every module gets ≥1 happy-path + ≥1 error-path test before its story is complete.
**Module root**: `engine/` (new `ww-engine`, sibling of `core/`/`tracking/`/`outreach/`). All paths below are repo-relative.

User stories (from spec.md): **US1** validate first batch in review mode (P1, MVP) · **US3** reply/bounce hard stop (P1, safety) · **US2** autonomous follow-ups (P2). Phases follow priority + the dependency that autonomous (US2) is only safe after US1 and US3.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create `engine/` module structure (`src/ww_engine/`, `src/ww_engine/drafting/`, `tests/unit/`, `tests/integration/`, `tests/contract/`) per plan.md
- [X] T002 Create `engine/pyproject.toml` (`ww-engine`, `requires-python>=3.11`, deps: `typer>=0.12`, `rich>=13.0`, `requests`, path deps `ww-core` and `ww-outreach`; `[project.scripts] ww-engine=ww_engine.cli:app`; hatchling), then `uv sync` in `engine/`
- [X] T003 [P] Add `engine/tests/` pytest config (pytest in dev deps, `tests/__init__.py`, conftest with a tmp `leads.db` fixture seeded via `ww-core`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ No user story work begins until this phase is complete.**

- [X] T004 Implement structured logger in `engine/src/ww_engine/logging.py` — emits `{action, module:"engine", customer_id, campaign_id, lead_id?, ts}`; helper asserts no email/name/body is ever passed (Article 3 & 10). Built first; every later task uses it.
- [X] T005 Write `engine/schema_engine.sql` and the idempotent applier in `engine/src/ww_engine/db.py` (ww-core connection reuse + `PRAGMA table_info` guarded `ADD COLUMN` + `CREATE TABLE IF NOT EXISTS` + indexes) exactly per `contracts/db-migration.md` and `data-model.md`
- [X] T006 [P] Implement `engine/src/ww_engine/runs.py` — `engine_runs` lifecycle (start/finish, `outcome` completed/capped/error, `counts` JSON), idempotency guard helper, fail-loud recorder (Article 11/12)
- [X] T007 [P] Implement `engine/src/ww_engine/cost.py` — `token_ledger` writer (stage-tagged) + per-email/per-stage rollup query (FR-026/027, SC-011)
- [X] T008 [P] Implement `engine/src/ww_engine/rotation.py` — 3 rotation groups + `stable_hash(lead.id)%3` balanced assignment (research R6, FR-011/012)
- [X] T009 Implement `engine/src/ww_engine/selection.py` — deterministic eligibility query (FR-001/002/003: touch<3, ≥14d, active) with hooks for the reply/bounce exclusion and the detect-freshness guard (filled by US3)
- [X] T010 Implement Drafter seam in `engine/src/ww_engine/drafting/base.py` — `Drafter` Protocol, `DraftRequest`/`DraftResult`, `DraftError`/`DrafterCapReached`, and the deterministic FR-013 named-account guard (post-check on body) per `contracts/drafter.md`
- [X] T011 [P] Implement `engine/src/ww_engine/drafting/personalization.py` — layered context: official datasets → org site → public web; LinkedIn manual hook; `thin` flag when none (FR-010)
- [X] T012 Implement `engine/src/ww_engine/drafting/claude_code.py` — `ClaudeCodeDrafter` (subprocess `claude -p --output-format json`, parse text+usage→cost.py, raise `DrafterCapReached` on cap) per research R4
- [X] T013 Implement `engine/src/ww_engine/cli.py` skeleton + `init` and `enroll` commands (Typer/rich; `--db` default `data/leads.db`) per `contracts/cli.md`
- [X] T014 [P] Foundational tests in `engine/tests/`: migration idempotency happy+error (`tests/unit/test_db_migration.py`), selection eligibility happy+error (`tests/unit/test_selection.py`), rotation balance happy+error (`tests/unit/test_rotation.py`), Drafter seam contract with a fake drafter (`tests/contract/test_drafter.py`), cost ledger happy+error (`tests/unit/test_cost.py`)

**Checkpoint**: foundation ready — selection/rotation/drafter/db/logging/cost all unit-green.

---

## Phase 3: User Story 1 — Validate first batch in review mode (Priority: P1) 🎯 MVP

**Goal**: Operator drafts touch 1 in review mode, inspects per-email, approves/edits/rejects, and approved mail is delivered in-window with a recorded recipe.

**Independent Test**: small lead list → `draft` (nothing sent) → `review` shows bodies + thin flags → reject one, edit one, `approve-all` → `deliver` sends only the kept/edited drafts inside the window, each with `sends` row + `message_recipe` + `sent` event.

### Tests for User Story 1 (REQUIRED — Article 8) ⚠️

- [X] T015 [P] [US1] Happy-path integration test in `engine/tests/integration/test_us1_review_happy.py` — draft→review→reject/edit/approve-all→deliver; assert rejected never sent, edited uses operator text, recipe+sent event written, marker header set (fake Graph + fake drafter)
- [X] T016 [P] [US1] Error-path test in `engine/tests/integration/test_us1_review_errors.py` — unapproved draft never delivered in review mode; `deliver` outside the configured window is a no-op (exit 0); thin-personalization draft is flagged

### Implementation for User Story 1

- [X] T017 [US1] Implement `engine/src/ww_engine/modes.py` — `review`/`autonomous` campaign mode + per-email approval state machine (`pending→approved/edited/rejected→delivered`), default `review` (FR-004/021, Article 6)
- [X] T018 [US1] Implement the draft pass in `engine/src/ww_engine/cli.py` `draft` command — select (T009) → assign angle from rotation (T008) → personalization (T011) → Drafter (T010/T012) → write `send_drafts` (pending) → ledger tokens (T007); batch+cap-aware via runs.py (T006)
- [X] T019 [P] [US1] Implement `review`, `approve`, `reject`, `edit --body-file`, `approve-all` commands in `engine/src/ww_engine/cli.py` per `contracts/cli.md` (records each action; `edit` preserves `body_text_original`)
- [X] T020 [US1] Implement `engine/src/ww_engine/sender.py` — window gate (single configured US-business-hours window, FR-016/017), `ww-outreach` send, pixel+click token injection (`ww-tracking` schema), `X-WW-Send` marker header + capture `conversation_id`/`internet_message_id` (FR-009c, research R3), write `sends` row + `sent` event, mark draft delivered
- [X] T021 [US1] Implement `deliver` command in `cli.py` — review-mode gate (only approved/edited), pre-send eligibility re-check stub (completed in US3 T026), in-window only; plus `status` and `costs` commands
- [X] T022 [US1] Add logging for all US1 actions (draft, model_call, approve/reject/edit, schedule, deliver) via T004

**Checkpoint**: MVP — operator can run a validated, reviewed first batch end-to-end. STOP and validate against quickstart.md §3.

---

## Phase 4: User Story 3 — Reply/bounce hard stop (Priority: P1, safety)

**Goal**: A reply or bounce permanently halts that lead's sequence (incl. the manual LinkedIn note); detection is in-scope and verified; the engine never follows up blind.

**Independent Test**: log a `replied` event → engine drafts/sends nothing further for that lead and its LinkedIn task shows cancelled; repeat with `bounced`; a real test reply in the mailbox produces a `replied` event within the detect window; Graph failure makes draft/deliver refuse to advance.

### Tests for User Story 3 (REQUIRED — Article 8) ⚠️

- [X] T023 [P] [US3] Happy-path test in `engine/tests/integration/test_us3_hardstop_happy.py` — `replied` halts (no further draft/deliver), `bounced` excludes, LinkedIn task marked cancelled, detector matches reply by conversation_id and bounce by NDR+marker (fake Graph)
- [X] T024 [P] [US3] Error-path test in `engine/tests/integration/test_us3_hardstop_errors.py` — auto-reply/OOO NOT treated as reply; Graph-unreachable → `engine_runs.outcome='error'` and selection refuses to advance; reply arriving between draft and deliver cancels the send

### Implementation for User Story 3

- [X] T025 [US3] Implement `engine/src/ww_engine/detector.py` + `detect` CLI command — Graph inbox poll, match rules in priority order, auto-reply ignore, write `replied`/`bounced` events, set `leads.sequence_state`, void non-delivered drafts, dedupe, fail-loud per `contracts/detector.md`
- [X] T026 [US3] Complete the hard-stop enforcement: fill the selection.py reply/bounce exclusion + detect-freshness guard (T009 hooks), and the `deliver` pre-send re-check (T021 stub) so an ineligible lead is never sent (FR-007/009/009b)
- [X] T027 [US3] Implement manual-LinkedIn-task surfacing + cancel-on-halt in `status` output (FR-008/022)
- [X] T028 [US3] Add logging for detect runs, matches, halts, and refuse-to-advance events via T004

**Checkpoint**: the safety guarantee is real and tested; autonomous mode is now safe to build.

---

## Phase 5: User Story 2 — Autonomous follow-ups (Priority: P2)

**Goal**: After explicit promotion, follow-ups advance on their own every ≥14 days with the next rotation angle, idempotent and cap-resumable, no operator action.

**Independent Test**: validated campaign → `go-autonomous` → advance clock 14d → next touch drafted with next angle, recorded touch 2 then 3, never touch 4; <14d sends nothing; a cap mid-run resumes next run with zero duplicates.

### Tests for User Story 2 (REQUIRED — Article 8) ⚠️

- [X] T029 [P] [US2] Happy-path test in `engine/tests/integration/test_us2_autonomous_happy.py` — autonomous mode, 14d elapsed → touch 2 then 3 with correct rotation angles + recipe; no touch 4; no operator action
- [X] T030 [P] [US2] Error-path test in `engine/tests/integration/test_us2_autonomous_errors.py` — <14d no send; double `draft` run no duplicate (idempotency); `DrafterCapReached` mid-batch → run `capped`, next run resumes exactly remaining leads

### Implementation for User Story 2

- [X] T031 [P] [US2] Implement `go-autonomous` / `go-review` commands in `cli.py` (explicit, reversible mode flip; FR-004)
- [X] T032 [US2] Implement autonomous path in modes.py/draft pass — auto-create drafts as `approved`, advance `current_touch`, next-angle selection across touches 2→3, terminal at 3 (FR-002/011)
- [X] T033 [US2] Harden idempotency + cap resume across the draft/deliver passes using runs.py (T006) and the `uq_drafts_live_touch` partial index (FR-005/006, SC-003/008)
- [X] T034 [US2] Add logging for mode changes, autonomous draft cycles, cap/resume via T004

**Checkpoint**: all three stories independently functional; campaign "lives on its own".

---

## Phase 6: Polish & Cross-Cutting

- [ ] T035 [P] Run quickstart.md end-to-end against a seeded test `leads.db`; fix any drift
- [ ] T036 [P] Security pass: grep logs/tests to assert no email/name/body (Article 3); confirm secrets only via `outreach/.env`/token file
- [ ] T037 [P] Add the Article 12 stop-and-diagnose note + cron layout to `engine/README.md`
- [ ] T038 [P] Extra unit tests in `engine/tests/unit/` beyond the Article 8 minimum (marker matching, NDR parsing, window edges, rotation distribution at N=200)
- [ ] T039 Update root project status (README "active feature" line) and `data/` notes if needed

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → (Phase 3 → Phase 4 → Phase 5) → Phase 6.** Phase 2 blocks all stories.
- **US1 (Phase 3)** = MVP, depends only on Foundational.
- **US3 (Phase 4)** depends on Foundational; finalizes selection/deliver hooks left as stubs in US1 (T026 ← T009/T021).
- **US2 (Phase 5)** depends on US1 (draft/deliver/modes) **and** US3 (hard stop must exist before autonomous is safe — explicit per spec).
- **Within a story**: tests written first and failing → models/state → services → CLI → logging.

### Parallel opportunities

- Setup: T003 ∥ T001/T002 order.
- Foundational: T006, T007, T008, T011, T014 marked [P] (distinct files) once T004/T005 exist.
- Each story's two test tasks [P] together; T019 ∥ within US1; T031 ∥ within US2.

## Implementation Strategy

**MVP** = Phase 1 + 2 + 3 (US1): a human-validated, reviewed, in-window first batch with recipes and cost data — already demonstrable and the pilot's real learning starts here. Then US3 (make it safe), then US2 (make it autonomous). Commit after each task or logical group; stop at any checkpoint to validate per quickstart.md.

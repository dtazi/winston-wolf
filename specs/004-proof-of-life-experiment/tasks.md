# Tasks: Proof-of-Life Experiment

**Branch:** `004-proof-of-life-experiment` · **Spec/Plan/Contracts:** this folder.

> **Status (2026-06-11):** T001–T036 IMPLEMENTED — engine built, 46 tests green, the
> grounded drafter offline-smoke-validated (`engine/ops/smoke_draft.py`). Per-checkbox
> states below are not individually maintained; the authoritative status is here + the
> spec header. **Remaining: T037** (operator pre-flight — `richbond.ma` auth + a live
> draft→review→deliver smoke to a test address). Scouting the real prospect list is the
> deliberately-last step, after T037.

Legend: `[P]` = parallelizable (different files, no ordering dep) · `[USx]` = user story.
Most work **extends** the existing `ww-engine` (002) — tasks say NEW vs CHANGE.
Tests precede implementation per Article 8.

---

## Phase 1: Setup

- [ ] T001 Add `ww-llm` as a path dependency in `engine/pyproject.toml` (research, drafter,
  conclude use it; engine already deps `ww-core`+`ww-outreach`); `uv sync` in `engine/`.
- [ ] T002 [P] Create new module stubs: `engine/src/ww_engine/{research,knowledge,intake,feedback,conclude}.py`.
- [ ] T003 [P] Extend `engine/tests/conftest.py`: seed campaigns with the new config columns;
  add a fake `ww-llm` engine fixture (the fake Graph transport already exists).

## Phase 2: Foundational (blocking prerequisites)

- [ ] T004 CHANGE `engine/schema_engine.sql` + `db.py` applier — idempotent `ADD COLUMN`:
  `campaigns.max_touches`(def 2), `.touch_gap_days`(def 7), `.send_tz_default`;
  `leads.send_timezone`; `send_drafts.comment`. Per `data-model.md`.
- [ ] T005 [P] NEW `knowledge.py` — loaders for the KB, strategy library (`data/strategies/*.md`),
  conclusions log, and recent `send_drafts.comment` values. Pure file/DB read.
- [ ] T006 CHANGE `selection.py` — read `max_touches`/`touch_gap_days` from the campaign row
  (fallback to defaults); eligibility + `replied`/`bounced` hard-stop unchanged.
- [ ] T007 NEW engagement-tier helper (`selection.py`) — `clicked` > `opened` > `silent`
  per `data-model.md`. Tier shapes, never gates (FR-016b).
- [ ] T008 [P] CHANGE `sender.py` (D10) — fix pixel URL to `{base}/p/<token>.gif`; add
  link-wrapping (write `tracked_links`, rewrite to `{base}/c/<id>`); default
  `WW_TRACKING_BASE_URL=https://track.richbondgroup.eu`.
- [ ] T009 CHANGE `sender.py` (D2) — `in_send_window`/`next_window_slot` read the lead's
  `send_timezone` (fallback campaign default); window Tue–Thu, hours default 10–14.
- [ ] T010 [P] Foundational tests in `engine/tests/unit/`: migration idempotency;
  knowledge loaders happy+empty; selection cap/gap from config; tier helper
  (clicked/opened/silent); sender pixel path + link-wrap + per-tz window.

## Phase 3: User Story 1 — Nightly research → grounded draft + reasoning note → review (P1) 🎯 MVP

### Tests (REQUIRED — Article 8) ⚠️
- [ ] T011 [P] [US1] Happy integration `tests/integration/test_us1_review_happy.py` — draft
  pass with fake research+fake LLM → grounded draft + reasoning note in `message_recipe` →
  review file written; `review --verdict approve|edit|reject --comment` applies via
  `modes` and stores the comment; edited body replaces text.
- [ ] T012 [P] [US1] Error `tests/integration/test_us1_review_errors.py` — unsourced claim
  emitted `grounded:false` (Art 17 flag); thin research flagged; re-deciding a
  delivered/rejected draft refused; unapproved draft never deliverable.

### Implementation
- [ ] T013 [US1] NEW `research.py` per `contracts/research.md` — bounded sources via
  `ww-llm`; structured summary + `signals` + `send_timezone` + `confidence`; persist on the
  lead; no PII in logs (Art 3), no inbox access (Art 15).
- [ ] T014 [US1] CHANGE `drafting/claude_code.py` per `contracts/drafter.md` — read
  KB+strategy library+research+conclusions+recent comments; select strategies; emit
  subject/body + reasoning note (`strategies/why/how_applied/claims[]/engagement_tier`) in
  `message_recipe`; keep `violates_named_account_guard`. Seam (`base.py`) untouched.
- [ ] T015 [US1] NEW `feedback.py` — write per-draft review markdown to
  `data/reviews/<date>/<draft-id>.md` (email+note+research+tier); read verdict/comment back.
- [ ] T016 [US1] CHANGE `modes.py` — `set_review_state` accepts and stores `comment`.
- [ ] T017 [US1] NEW `intake.py` + `import-prospects` CLI — parse `data/prospects/*.yaml`
  → `leads` rows (`active`, touch 0, rotation group, tz NULL); idempotent on email.
- [ ] T018 [US1] CHANGE `cli.py` — wire the nightly `draft` pass (select → research →
  grounded draft → review file → ledger) and the `review` command (list + record +
  schedule approved). Per `contracts/cli.md`.
- [ ] T019 [US1] Logging for research/draft/review actions via `logging` (Art 10).

## Phase 4: User Story 2 — Approved draft sent at recipient local mid-day (P1)

### Tests ⚠️
- [ ] T020 [P] [US2] Happy `tests/integration/test_us2_send_happy.py` — approved draft
  scheduled to the recipient-local window; `deliver` sends in-window (fake transport);
  `sends` row + `sent` event + pixel(`/p`) + wrapped links + `tracked_links` written; draft
  marked delivered.
- [ ] T021 [P] [US2] Error `tests/integration/test_us2_send_errors.py` — out-of-window
  `deliver` is a no-op (exit 0); a lead with a `replied` event is never sent.

### Implementation
- [ ] T022 [US2] CHANGE `cli.py` `deliver` — schedule `scheduled_send_at` on approval (next
  per-recipient slot, T009), deliver only in-window, `is_still_eligible` re-check before
  send, sender D10 applied. Approval gate enforced (FR-015).

## Phase 5: User Story 3 — Manual reply flag stops outreach, never reads mail (P1, safety)

### Tests ⚠️
- [ ] T023 [P] [US3] Happy `tests/integration/test_us3_replyflag_happy.py` — `flag-replied`
  writes a `replied` event (category in payload), sets `halted_reply`, voids non-delivered
  drafts; later `draft`/`deliver` skip the lead.
- [ ] T024 [P] [US3] Error `tests/integration/test_us3_replyflag_errors.py` — `detector` is
  never invoked (no mailbox call); flag on an unknown lead errors cleanly; a reply flagged
  between draft and deliver cancels the send.

### Implementation
- [ ] T025 [US3] NEW `flag-replied` CLI (D4) — reuse the hard-stop write path (event +
  state + void drafts), category in the event payload; **no `detector.py` wiring, no
  read** (Art 15).
- [ ] T026 [US3] Logging for flag/halt via `logging`.

## Phase 6: User Story 5 — Engagement-tiered follow-up at +7 days (P2)

### Tests ⚠️
- [ ] T027 [P] [US5] Happy `tests/integration/test_us5_followup_happy.py` — at +7d a
  non-replied lead gets touch #2; tier computed and passed to the drafter + recorded in the
  note; threaded to the original; capped at 2 touches.
- [ ] T028 [P] [US5] Error `tests/integration/test_us5_followup_errors.py` — replied lead
  gets no follow-up; a `silent` lead is still eligible (opens never gate); no touch #3.

### Implementation
- [ ] T029 [US5] CHANGE the `draft` pass — touch #2 path: tier helper (T007) feeds the
  drafter context; selection honors `max_touches=2`/`gap=7`; follow-up threads to the
  original send.

## Phase 7: User Story 4 — Learning loop / conclusions (P2)

### Tests ⚠️
- [ ] T030 [P] [US4] Happy `tests/integration/test_us4_learning_happy.py` — `conclude`
  reads new comments + recent drafts → appends a dated observation to the conclusions log;
  the next `draft` pass consumes conclusions + comments.
- [ ] T031 [P] [US4] Error — empty/no new feedback → `conclude` no-ops (no spurious entry).

### Implementation
- [ ] T032 [US4] NEW `conclude.py` + `conclude` CLI — `ww-llm` pass over new comments +
  recent drafts; append-only dated entries to `data/conclusions/richbond.md`.

## Phase 8: Polish & cross-cutting

- [ ] T033 [P] NEW `report` CLI (FR-021) — prospects contacted, unique repliers, **reply
  rate** vs the ≥5%/2–5%/<2% rule; opens/clicks secondary.
- [ ] T034 [P] Run `quickstart.md` end-to-end against a seeded test `leads.db` with fakes
  (no live M365/LLM); fix drift.
- [ ] T035 [P] Security pass — assert no prospect PII in logs (Art 3); secrets only in
  `outreach/.env`/token; grep the codebase to confirm no reply content is ever read (Art 15).
- [ ] T036 [P] Update `engine/README.md` — daily-cycle cron layout + Article 12 note.

## Pre-flight (operator-gated — before any LIVE send)

- [ ] T037 Supply `outreach/.env` (`AZURE_CLIENT_ID`/`AZURE_TENANT_ID`) + run
  `ww-outreach auth` for richbond.ma (Phase 0: no token on this box); set
  `WW_TRACKING_BASE_URL`; live smoke one draft→review→deliver to a test address.

---

## Dependencies & parallelism
- Phase 2 blocks Phases 3–7. T004 (schema) blocks T006/T007/T016.
- **MVP = Phases 1–4** (research → grounded draft → review → send). US3 (safety) can land
  alongside US1. US4/US5 are P2, after the MVP loop runs.
- All code/tests build against the injectable fakes; **T037 is the only task needing live
  M365** and is operator-gated.

**Total: 37 tasks** (8 phases + pre-flight). Tests-first within each user story.

# Implementation Plan: Proof-of-Life Experiment

**Feature branch:** `004-proof-of-life-experiment`
**Spec:** [spec.md](./spec.md)
**Created:** 2026-06-08
**Status:** Draft — plan gate (awaiting operator review)

---

## Summary

This is a **reconcile-and-extend** job, not a new build. The `ww-engine` (002) already
owns the workflow spine — drafts, the approve/edit/reject state machine, the send-window
gate, tracking-pixel injection, the M365 Graph transport (via `ww-outreach`), the
draft→deliver→sequence loop, and per-lead hard-stop on `replied`/`bounced` events. We
extend it with the experiment's intelligence pieces (research, KB-grounded drafting,
engagement-tiered follow-up) and adjust a handful of constants/seams to match the spec.

The intelligence layer (research + KB-grounded writer) lives **inside `ww-engine` for the
experiment** rather than as separate packages. This is a deliberate Article 2 call: a
30-day experiment wants a tight loop, not module ceremony. The internal seams stay clean
(the drafter Protocol is untouched as a seam), so these graduate to their own modules at
product time. Noted in Complexity Tracking.

---

## Technical Context

- **Language/runtime:** Python 3.12+, `uv`-managed, per existing modules.
- **Storage:** the shared SQLite `data/leads.db` (ww-core schema + ww-engine migrations).
- **Send:** Microsoft Graph `/me/sendMail` via `ww-outreach` (un-retired), real
  `richbond.ma` mailbox.
- **Tracking:** `ww-tracking` (un-retired) open-pixel + click-redirector at
  `https://track.richbondgroup.eu` → writes engagement `events` to `leads.db`.
- **LLM:** `ww-llm` registry for research, drafting, and the conclusions pass.
- **Operator-maintained inputs (files):** the knowledge base, the strategy library, the
  conclusions log — markdown under `data/`.

---

## Key technical decisions (the HOW)

### D1 — Feedback interface: markdown-file-per-draft + a review CLI *(recommended; operator's glance wanted)*
Each nightly draft writes a self-contained review file (email + strategy/reasoning note +
research summary + engagement tier for follow-ups) into a review folder. The operator
records a verdict and comment via a `ww-engine review` CLI (or by editing a verdict field
in the file). Approved drafts get scheduled.
- **Pros:** fastest to build (Art 2), zero new auth/network surface (Art 3), inspectable,
  git-versionable, fits the existing CLI-driven engine.
- **Cons:** less polished than a web form; editing in markdown is clunkier than a UI.
- **Why now:** at 5–15 drafts/morning this is enough. A small local web UI is a clean
  fast-follow if the morning ritual feels clunky — but it's not worth blocking the
  experiment on.
- **This is the one discretionary call worth your eyes before tasks.** If you'd rather a
  minimal local web app from day one, say so and I'll plan that instead.

### D2 — Send window becomes per-recipient local
`sender.py` currently gates on a single configured timezone (`America/New_York`,
Tue–Thu, 9–11). The spec wants **each recipient's local 10am–2pm, Tue–Thu**. Change:
derive a `send_timezone` per prospect at research time (from company HQ location), store
it on the lead, and have the window gate + `next_window_slot` read the lead's timezone.
Tue–Thu retained; hours default to 10–14.

### D3 — Touch cap 2, gap 7 days, made campaign-configurable
`selection.py` hardcodes `MAX_TOUCHES=3`, `TOUCH_GAP_DAYS=14`. Move these to
campaign-level config (new `campaigns` columns, defaults **2** and **7**) rather than
new module constants — small migration, satisfies Article 1 (scale) without bespoke
single-tenant assumptions. `deliver_draft`'s "completed when touch>=3" reads the same cap.

### D4 — Manual reply flag reuses the hard-stop path, never reads mail
A `ww-engine flag-replied <lead> [--category ...]` CLI writes a `replied` event (with the
operator-supplied category in the payload), sets the lead to `halted_reply`, and voids
non-delivered drafts — exactly the stop/suppress/log semantics `detector.py` already
implements, minus any mailbox access. `selection.is_still_eligible` already cancels a send
the moment a `replied` event exists, so the gate-time re-check is the backstop against
flag lag. **`detector.py` is not wired** (no inbox polling, no body scanning → Article 15).

### D5 — Engagement-tiered follow-up
At the +7-day mark, eligible non-replied prospects get touch #2. A new helper reads
`events` for `opened`/`clicked` since the first send and computes a tier
(`clicked` > `opened` > `silent`). The tier is passed to the drafter as context (it shapes
angle/priority) and recorded in the reasoning note. **Raw opens are never a hard
include/exclude gate** (FR-016b) — everyone non-replied is eligible; the signal only
shapes the draft. Phase 0 confirms the exact `event_type` strings `ww-tracking` writes.

### D6 — Grounded, KB-aware drafter
The drafter seam (`drafting/base.py` Protocol) is unchanged. The Claude-Code drafter's
prompt is extended to read: the **knowledge base** (grounded facts/offers), the **strategy
library** (chooses 1+ strategies, grounded in the research), the **conclusions log**, and
the **prior feedback comments**. It emits subject/body **plus a strategy/reasoning note**
carried in the existing `message_recipe` JSON field. Article 17: every claim/offer must
cite a KB source; unsourced/low-confidence claims are flagged in the note and surfaced at
approval. `violates_named_account_guard` (the IKEA guard) stays.

### D7 — Research module
A new `research.py`: per prospect, run a bounded set of web searches + fetch the company
site + recent news (+ LinkedIn where feasible) via `ww-llm`, producing a structured
research summary stored on the lead and surfaced at approval. Bounded for cost (Article 4);
deterministic plumbing in code, LLM only for synthesis.

### D8 — Prospect intake
A `ww-engine import-prospects` CLI ingests the operator's hand-built list (simple
YAML/CSV under `data/`) into `leads` rows: `sequence_state='active'`, `current_touch=0`,
a default rotation group, derived `send_timezone`. KB/strategy/conclusions seed files are
operator prep (pitch.yaml → KB v0; 002 `email_*.md` → strategy library v0).

### D10 — Tracking integration fixes (found in Phase 0)
Two gaps block decision #2 (keep open + click):
- **Pixel path mismatch:** `sender.py` emits `{base}/pixel/<token>`; the tracker serves
  `/p/<token>.gif`. Align the sender to the real route.
- **No click capture:** `sender.py` injects only the pixel. Add link-wrapping — for each
  URL in the body, write a `tracked_links` row and rewrite the link to
  `{base}/c/<token>` (the tracker's existing click-redirect). Set
  `WW_TRACKING_BASE_URL=https://track.richbondgroup.eu`.

### D9 — Conclusions pass
After the day's feedback is captured, a `ww-engine conclude` pass feeds new comments +
recent drafts to `ww-llm` and appends dated observations to the conclusions log when
patterns emerge. Read back by the next nightly batch (D6).

---

## Constitution Check

- **Art 1 (scale):** touch cap/gap as campaign config, tenant-scoped data — no new
  single-tenant assumptions baked in.
- **Art 2 (simplicity):** extend `ww-engine` rather than spin up packages; markdown+CLI
  feedback over a web app. Intelligence-in-engine is a conscious experiment-scope tradeoff
  (Complexity Tracking).
- **Art 3 (security):** no new auth/network surface; prospect data stays in `leads.db`;
  M365 secrets remain in `ww-outreach/.env`.
- **Art 4 (code-first):** selection, sequencing, window, tiering, flagging are code; LLM
  only for research synthesis, drafting, conclusions.
- **Art 5 (modular):** vendors reached only through adapters (`ww-outreach`, `ww-tracking`,
  `ww-llm`); drafter Protocol seam preserved.
- **Art 6 (approval gate):** every send (incl. follow-ups) passes review; default-on.
- **Art 9 (doc separation):** this plan is HOW; the spec stays WHAT/WHY.
- **Art 10/11 (instrument/contain):** reuse `runs.py` run-wrapping + `logging`; module
  boundaries catch and log.
- **Art 13 (rent the plumbing):** using a real mailbox's send API at low volume is not
  building SMTP/warm-up/DNS infrastructure — compliant.
- **Art 15 (reply boundary):** manual flag only; detector not wired; no reply content read.
- **Art 16 (sending hygiene):** primary-domain send permitted under the **validation-pilot
  exception** (amended 2026-06-08); operator decision #1 is the written risk acceptance.
- **Art 17 (grounded claims):** KB-sourced claims; unsourced flagged at approval.

No violations. One scoped tradeoff (intelligence-in-engine), tracked below.

---

## Project Structure

```
engine/src/ww_engine/
  selection.py        # CHANGE: touch cap/gap from campaign config; tier helper
  sender.py           # CHANGE: per-recipient-local window; tracking base → richbondgroup.eu
  modes.py            # CHANGE: feedback capture (comment) on review decisions
  drafting/
    claude_code.py    # CHANGE: KB + strategy library + conclusions + comments in prompt;
                      #         emit strategy/reasoning note into message_recipe
  research.py         # NEW: per-prospect research → structured summary (ww-llm)
  knowledge.py        # NEW: loaders for KB, strategy library, conclusions
  feedback.py         # NEW: write review files; record verdict+comment
  conclude.py         # NEW: post-feedback conclusions pass
  intake.py           # NEW: import manual prospect list; derive timezone; enroll
  cli.py              # CHANGE: import-prospects, review, flag-replied, conclude commands
  schema_engine.sql   # CHANGE: campaigns.max_touches/touch_gap_days;
                      #         send_drafts.comment, .verdict; leads.send_timezone

data/
  knowledge/richbond-kb.md     # operator-maintained (seed from pitch.yaml)
  strategies/*.md              # operator-maintained (seed from 002 email_*.md)
  conclusions/richbond.md      # system-appended
  prospects/richbond.yaml      # operator-built intake list
  reviews/                     # nightly review files (feedback interface)
```

No changes to `ww-outreach`, `ww-tracking`, `ww-llm`, `ww-core` beyond configuration.

## Complexity Tracking

- **Intelligence layer inside `ww-engine`.** Per the pivot's 3-layer model, research +
  KB-grounded writing are the *intelligence layer* and would ideally be their own
  module(s). For a 30-day experiment we keep them in `ww-engine` to keep the loop tight
  (Art 2). Mitigation: the drafter Protocol seam is preserved; the new files
  (`research.py`, `knowledge.py`) are self-contained and extractable. Graduates to its own
  module at product time.

## Phase 0 — Findings (resolved 2026-06-08)

1. **Open/click event types** ✅ — `ww-tracking` writes `"opened"` and `"clicked"`; both
   already in the `events` CHECK constraint. No schema change. (Drives D5.)
2. **M365 connection NOT established on this box** ⚠️ — no `~/.winston-wolf/outreach-token.json`
   and no `outreach/.env`. Pre-flight is a **first-time auth**, not a refresh: supply the
   Richbond Azure AD app `AZURE_CLIENT_ID`/`AZURE_TENANT_ID` in `outreach/.env`, then run
   `ww-outreach auth` (device-code) to authenticate the richbond.ma mailbox. **Operator
   dependency — blocks first send.**
3. **Click tracking has two wiring gaps** ⚠️ — pixel path mismatch + no link-wrapping →
   captured in **D10**. Tracker routes/tables are ready.
4. **Timezone derivation** — research emits the prospect's IANA `send_timezone` (the LLM
   knows the company HQ location); campaign default fallback when unknown (D2/D7).
5. **D1 (feedback interface)** ✅ — operator chose markdown + CLI.

## Phase 1 — Design & Contracts (produced after plan approval)

- `data-model.md` — the schema deltas (campaign config, draft comment/verdict,
  lead timezone), engagement-tier query, review-file shape.
- `contracts/` — drafter contract update (KB/strategy/note I/O), CLI contract
  (import-prospects/review/flag-replied/conclude), research contract.
- `quickstart.md` — operator runbook for the daily cycle + pre-day-one prep.

## Phase 2 — Next

`tasks.md` (the tasks gate) after this plan and the Phase-1 contracts are approved.
```

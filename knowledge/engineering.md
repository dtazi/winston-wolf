# Engineering — conventions, gotchas, testing

## Gotchas
- **SQLite timestamp converter** (py3.12) is deprecated and **crashes on
  tz-suffixed timestamps** — the tracker writes `...+00:00`. Read such columns
  with `CAST(col AS TEXT)` or a raw `sqlite3.connect` without `detect_types`.
- **Schema migrations** (`engine/db.py`): `ADD COLUMN` runs in **two passes** —
  pre-script for tables ww-core already created (campaigns/leads/sends),
  post-script for tables `schema_engine.sql` itself creates (send_drafts).
  Don't ALTER a table before it exists; the schema script's indexes need the
  pre-script columns present.
- Don't commit `__pycache__/` or `*.pyc` (gitignored).

## Testing
- Inject fakes at the seams (Drafter, Researcher, Transport, MailReader) — **no
  network in unit/integration tests**. Live paths (Graph send, the `claude` CLI)
  are proven by **operator-gated smokes**, not unit tests.
- The 002 suite is kept green as regression coverage; 004 changes default to
  legacy behavior so they don't break.

## Conventions
- **Backward-compatible defaults:** new schema columns default to the OLD
  behavior so existing campaigns/tests don't silently change (e.g. campaign
  touch-cap defaults to the legacy 3/14; the experiment campaign sets 2/7
  explicitly via `configure`).
- Extend at the seam rather than rewrite: the 004 grounded drafter is a NEW class
  (`drafting/grounded.py`); the 002 `ClaudeCodeDrafter` stays intact.

## Pre-pilot findings (offline smoke `engine/ops/smoke_draft.py`, 2026-06-09)
- The smoke proves the **grounded** path end-to-end: real KB + strategies →
  `GroundedClaudeDrafter` (claude CLI) → 82-word email, correct strategy selection,
  all claims grounded to KB anchors, full reasoning note. WORKS.
- **GAP — no link in grounded output → click-tracking is dead.** Unlike the legacy
  `ClaudeCodeDrafter` (which mandated the `richbondgroup.eu` URL + signature), the 004
  `grounded.py` prompt never instructs the model to include a link. The sender only
  *wraps* existing links, so a linkless body yields no `/c/` click signal — and the
  engagement-tiered follow-up (`clicked>opened>silent`) degrades to opened/silent only.
  FIX before pilot: add the mandatory tracked company URL (+ decide signature identity)
  to the grounded prompt. Pixel-open tracking still works regardless.
- Harness footgun: import `GroundedClaudeDrafter`, NOT the legacy `ClaudeCodeDrafter`
  (which ignores `req.knowledge_base`/`req.strategies` entirely).

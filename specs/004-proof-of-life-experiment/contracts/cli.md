# Contract — `ww-engine` CLI (experiment commands)

New/changed subcommands. All operate on the shared `data/leads.db` and log via the
existing `logging` + `runs.run` wrappers (Articles 10/11).

## `ww-engine import-prospects <file> --campaign <id>` (NEW, D8)
Ingest the hand-built list (YAML/CSV) into `leads`.
- **In:** rows of `{company, person_name, person_email, [country/city], [notes]}`.
- **Effect:** one `leads` row each — `sequence_state='active'`, `current_touch=0`, a
  default rotation group, `send_timezone` left NULL (research fills it).
- **Out:** count imported / skipped (duplicate email). Idempotent on `person_email`.

## `ww-engine draft --campaign <id>` (CHANGED, nightly)
The autonomous nightly pass: for each eligible lead → research → strategy selection →
KB-grounded draft + reasoning note → write a review file.
- Reuses `runs.run(..., 'draft')`, `selection.eligible_leads`, the drafter seam.
- Touch #2 path computes the engagement tier and passes it to the drafter.
- **Out:** `{drafted, researched, capped, skipped}`.

## `ww-engine review --campaign <id>` (NEW, D1)
The morning interface.
- **List:** show pending review files (draft id, prospect, touch, tier).
- **Record:** `--draft <id> --verdict approve|edit|reject [--comment "…"] [--body <file>]`.
  Applies via `modes.set_review_state`; `edit` replaces `body_text`; stores `comment`.
  Approved drafts get `scheduled_send_at = next per-recipient-local window slot`.
- Re-deciding a delivered/rejected draft is refused (existing `set_review_state` rule).

## `ww-engine deliver --campaign <id>` (CHANGED)
Send approved/edited drafts whose `scheduled_send_at` is in the recipient's local window.
- `selection.is_still_eligible` re-checks the hard stop at send time (backstop vs flag lag).
- Sender fixes from D10 (pixel path + link wrapping) apply here.

## `ww-engine flag-replied --lead <id> [--category interested|not-interested|wrong-person|ooo|other]` (NEW, D4)
Manual reply handling — **no mailbox access**.
- Writes a `replied` event (category in payload), sets `sequence_state='halted_reply'`,
  voids non-delivered drafts for the lead. Mirrors `detector.py` stop/suppress/log,
  minus any read. Honors Article 15.

## `ww-engine conclude --campaign <id>` (NEW, D9)
Post-feedback pass: feed new comments + recent drafts to `ww-llm`; append dated
observations to `data/conclusions/richbond.md` when patterns emerge.

## `ww-engine report --campaign <id>` (NEW, FR-021)
Print the experiment scoreboard: prospects contacted, unique repliers, **reply rate**
(repliers ÷ contacted), opens/clicks (secondary), against the ≥5% / 2–5% / <2% rule.

## `ww-outreach auth` (EXISTING — pre-flight)
First-time device-code auth for richbond.ma (needs `outreach/.env` with the Azure app ids).
Phase 0 found no token on this box — this must run before the first `deliver`.

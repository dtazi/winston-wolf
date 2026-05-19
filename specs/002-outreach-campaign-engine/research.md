# Phase 0 Research — Outreach Campaign Engine

Resolves every NEEDS CLARIFICATION / technical unknown before design.

## R1 — Detecting replies in the Richbond M365 mailbox

**Decision**: Poll the mailbox via Microsoft Graph (`GET /me/messages`) on a delta/`receivedDateTime` filter and match inbound messages to an originating send by **`conversationId`**, falling back to the **`X-WW-Send` custom header / marker token** echoed in quoted replies.

**Rationale**: The existing `ww-outreach` send already returns Graph's message identifiers; capturing `conversationId` + `internetMessageId` at send time gives an exact, deterministic join from any reply back to the send — no fuzzy matching (satisfies FR-009c). `Mail.ReadBasic` is already an approved-but-unused scope on the Richbond app (per `outreach/README.md`), so no new IT approval is required. Polling (not webhooks) keeps the module a simple cron pass with no public callback endpoint, consistent with Article 2.

**Alternatives considered**: Graph change-notifications/webhooks (needs a public HTTPS endpoint + subscription renewal — more infra than a pilot needs); IMAP (M365 app-password/basic-auth is being deprecated; the OAuth path is already built).

## R2 — Detecting bounces (NDRs)

**Decision**: Treat as `bounced` any inbound message that is (a) from a postmaster/`MAILER-DAEMON`-class sender or has `Content-Type: multipart/report; report-type=delivery-status`, **and** (b) references one of our sends via the quoted original `internetMessageId` or `X-WW-Send` token. Hard bounces set `sequence_state='halted_bounce'`; transient/auto-reply (`X-Autoreply`, `Auto-Submitted: auto-replied`) are explicitly **not** treated as replies or bounces.

**Rationale**: M365 does not expose a clean structured bounce API for delegated mail; NDRs arrive as messages. Parsing the DSN report + matching on our own marker is deterministic and avoids misclassifying out-of-office auto-replies as human replies (a real false-positive risk for the hard stop). Code-first (Article 4).

**Alternatives considered**: Relying on Graph `extendedProperties` delivery receipts (unreliable for external domains); SMTP-level bounce capture (not available on a hosted M365 mailbox).

## R3 — Deliverability-safe per-send marker (FR-009c)

**Decision**: Inject a custom internet header **`X-WW-Send: <marker_token>`** on send (Graph `singleValueExtendedProperties` for the header) and persist `marker_token`, `conversation_id`, `internet_message_id` on the `sends` row. The marker is invisible to the recipient; matching uses `conversation_id` first, marker token second (for forwarded/header-stripped NDRs).

**Rationale**: A visible token at the top of a cold email (the operator's first instinct) harms trust and deliverability; a custom header carries the same uniqueness with zero recipient-visible footprint and survives in NDR header echoes. No subject-line tag (subjects get edited/translated by recipients). Meets "immediate, unambiguous" without a cosmetic cost.

**Alternatives considered**: VERP/plus-addressing on Reply-To (`reply+<token>@…`) — M365 shared/delegated mailboxes handle sub-addressing inconsistently; subject-embedded token — fragile across "Re:" localisation and recipient edits.

## R4 — Headless Claude Code drafting: invocation, token capture, cap handling

**Decision**: The `ClaudeCodeDrafter` shells out to `claude -p <prompt> --output-format json` as a subprocess on the cron host. The JSON result carries the assistant text **and** a usage block (input/output tokens) → written to `token_ledger` tagged by stage. Cap/limit handling: a non-zero exit or a recognized usage-limit/rate-limit signal marks the current `engine_runs` row `outcome='capped'`, stops drafting further leads this run, and leaves already-persisted drafts intact. The next run is idempotent (only drafts leads with no live draft for the due touch), so it resumes exactly where it stopped.

**Rationale**: Subprocess + JSON is the lowest-complexity integration that still yields real token numbers (required by FR-026/027 and SC-011) and needs no API key (the explicit cost decision). Drafting runs in small fixed batches at 02:00–06:00 to stay in the trough of the operator's own subscription budget.

**Alternatives considered**: Anthropic API/SDK (rejected for v1 on cost grounds; kept available behind the FR-015 seam — an `ApiDrafter` is a drop-in later); long-lived Claude session (more state, harder to make idempotent/cap-safe).

## R5 — Decoupling draft time from send time (FR-016/017)

**Decision**: Two separate cron passes over one queue. **Draft pass** (02:00–06:00): selects eligible leads, drafts, writes `send_drafts` with `scheduled_send_at` = next slot inside the configured window; in `autonomous` mode drafts are auto-`approved`, in `review` mode they stay `pending`. **Deliver pass** (hourly): inside the configured window only, picks `approved`/`edited` drafts whose `scheduled_send_at` has passed, **re-checks reply/bounce eligibility immediately before sending** (FR-009), sends via `ww-outreach` with pixel/click + `X-WW-Send`, inserts the `sends` row, logs `sent`, marks the draft `delivered`. **Detect pass** (hourly) runs R1/R2.

**Rationale**: Separating "think" (expensive, off-peak, cap-bound) from "send" (cheap, window-bound, must be fresh) is the simplest way to satisfy both the off-peak-subscription constraint and the business-hours + hard-stop constraints without a scheduler service. All three passes are idempotent cron jobs.

**Alternatives considered**: Single pass that drafts and sends inline (can't honor both off-peak drafting and business-hours sending); an in-process scheduler/daemon (more moving parts than cron for a pilot, Article 2).

## R6 — Rotation assignment balance (FR-012 / SC-006)

**Decision**: At campaign enrolment each lead gets `rotation_group = stable_hash(lead.id) % 3` (groups: `[c1,60y,hv]`, `[60y,hv,c1]`, `[hv,c1,60y]`). Deterministic, reproducible, and balanced to ±10% for any non-trivial N — verified by a unit test asserting per-position distribution.

**Rationale**: Pure code, no state, idempotent re-enrolment, satisfies the position-balance success criterion without a counter/coordinator.

---

All unknowns resolved. No remaining NEEDS CLARIFICATION. Proceed to Phase 1.

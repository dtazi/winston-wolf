# Contract — Inbound match (reply / bounce → send / lead)

How the detect pass turns mailbox messages into `replied` / `bounced` events. Deterministic (Article 4). Isolated here so it can later move to an Engagement Tracker module unchanged (plan Complexity Tracking).

## Input
Microsoft Graph messages from the Richbond mailbox since the last successful `detect` run (`receivedDateTime` watermark), using the already-approved `Mail.ReadBasic` scope.

## Matching rules (in order)
1. **Reply**: inbound message whose `conversationId` equals a `sends.conversation_id` → that send/lead. (Primary, exact.)
2. **Reply fallback**: body/headers contain a known `X-WW-Send` `marker_token` → that send/lead. (Forwarded/re-threaded.)
3. **Bounce**: sender is postmaster/`MAILER-DAEMON`-class OR `Content-Type: multipart/report; report-type=delivery-status`, AND the quoted original references a known `internet_message_id` or `marker_token` → that send/lead, classified hard vs transient from the DSN status code.
4. **Ignore (not a reply, not a bounce)**: `Auto-Submitted: auto-replied`, `X-Autoreply`, vacation/OOO autoresponders — logged as `skipped`, never trigger the hard stop (prevents false halts).
5. **Unmatched**: logged to `engine_runs.detail` (count only, no PII) for operator review; no event written.

## Output (effects)
- Write an `events` row: `event_type='replied'` or `'bounced'`, `lead_id`, `send_id`, `payload` = `{match_rule, message_meta}` (no body/PII beyond minimal metadata, Article 3).
- Set `leads.sequence_state` = `halted_reply` / `halted_bounce` (hard, terminal — FR-007).
- Any non-`delivered` `send_drafts` for that lead are voided (FR-009).

## Reliability (FR-009b)
- Graph unreachable / auth failure ⇒ `detect` run `outcome='error'`, operator-visible; the draft & deliver passes then **refuse to advance** that campaign until a fresh successful detect exists (never follow up blind).
- Idempotent: re-processing the same message produces no duplicate event (dedupe on `(lead_id, event_type, message_id)`).

# Feature Specification: Outreach Campaign Engine

**Feature Branch**: `002-outreach-campaign-engine`
**Created**: 2026-05-19
**Status**: Draft
**Input**: User description: "Outreach campaign engine for the Richbond US Institutional Pilot. A campaign that runs itself once configured."

## Overview

A self-running outreach campaign. Once an operator configures a campaign (brief + pitch + lead list), the system drafts personalized emails, sends them on a 3-touch sequence two weeks apart, records what was sent in a structured way, and stops the moment a lead replies or bounces — without the operator initiating each step. The pilot's single success metric is **a reply**; the system is built to maximize replies and to learn *qualitatively* from what people write back.

Every lead receives all three value angles — one per touch — in a rotated order across the lead population, so no single angle is permanently tied to the "follow-up advantage." This deliberately favors reply volume over a statistically clean A/B test, because at pilot scale a clean A/B test is not achievable anyway (see Assumptions).

This feature is the drafting + sequencing engine. The shareable dashboard, analytics rollups, and the nightly analyst narrative are **out of scope here** and belong to `001-dashboard-skeleton`.

## Clarifications

### Session 2026-05-19

- Q: Is reply/bounce detection built by this feature, or assumed to already exist? → A: Built **inside this feature** — a minimal poller over the Richbond M365 inbox that logs `replied`/`bounced` events. The hard stop is real on day one; detection is in-scope, not an external dependency.
- Q: Per-recipient timezone, one fixed window, or regional buckets for send timing? → A: **One fixed configured US-business-hours window** for the whole pilot (e.g., Tue–Thu 09:00–11:00 ET). No per-lead timezone resolution in v1.
- Q: Review-mode approval granularity — per-email or whole-batch? → A: **Per-email** approve / reject / edit, with an "approve all remaining" shortcut. Reject and edit actions are recorded per draft.
- Q: What triggers a campaign moving from review mode to autonomous mode? → A: **Explicit manual operator action** ("go autonomous"). Until that action, every batch including follow-ups is review-gated. The system never self-promotes.
- Decision (operator side note): every outgoing email MUST carry a unique per-send marker enabling the detector to attribute an inbound reply/bounce/notification to the exact originating send/lead immediately and unambiguously (no fuzzy matching). Exact placement (subject tag vs. discreet body line) is a planning detail; deliverability is the constraint.
- Q: Does this feature import leads, or assume them pre-loaded? → A: **Pre-loaded.** Lead intake is a **separate dedicated tool** (out of scope here) that must support client-provided lists, bulk-purchased email lists, and Scout — all writing leads into `leads.db` with `campaign_id` set. This engine only reads a campaign's eligible leads.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The operator validates a real first batch before trusting automation (Priority: P1)

The operator configures a campaign and runs the engine in **review mode**: it drafts the first touch for every lead but delivers nothing. The operator reads the drafted emails, confirms the personalization is real (not "Hi {name}, generic text"), records approval, and only then are they delivered — during recipients' business hours. This proves the message works *before* any unattended automation is trusted.

**Why this priority**: The pilot's real question is "does the message earn replies?" — not "can it run at night?". A validated first batch is the minimum that produces real learning and protects the Richbond sender reputation on the riskiest send. Nothing else matters if the message is weak.

**Independent Test**: Configure a campaign with a small lead list, run in review mode, confirm nothing is delivered until approval is recorded, confirm each draft shows recipient/touch/angle/full body, then approve and confirm delivery happens in business hours with a recorded `message_recipe` and `sent` event per lead.

**Acceptance Scenarios**:

1. **Given** a configured campaign, **When** the engine runs in review mode, **Then** every lead has a drafted first email visible to the operator and **zero** emails are delivered.
2. **Given** drafted emails, **When** the operator inspects the queue, **Then** each entry shows recipient, touch number, value angle, and full body text.
3. **Given** the operator records batch approval, **When** delivery runs, **Then** each lead receives exactly one email within recipient business hours, with a `sends` row, `message_recipe`, and `sent` event.
4. **Given** a draft whose personalization is empty/thin, **When** the operator reviews it, **Then** it is visibly flagged so the operator can fix the data source rather than send generic mail.
5. **Given** a batch of drafts, **When** the operator rejects one, edits another, and uses "approve all remaining", **Then** the rejected draft is never delivered, the edited draft is delivered with the operator's text, the rest are delivered as drafted, and each reject/edit is recorded.

---

### User Story 2 - The campaign runs its follow-ups on its own (Priority: P2)

Once the message is validated, the operator switches the campaign to autonomous mode. Two weeks after each touch, leads who have not replied or bounced automatically receive their next touch — a *different* value angle each time — with no operator action between runs.

**Why this priority**: This is the "lives on its own" requirement and the operator's stated goal — but it is only safe and worthwhile *after* Story 1 proves the message. Automating an unvalidated message just sends bad email faster.

**Independent Test**: With a validated campaign in autonomous mode, advance the clock 14 days past a lead's touch 1 with no reply; run the engine; confirm touch 2 is drafted with the *next* angle in that lead's rotation and recorded as touch 2. Repeat for touch 3. Confirm no touch 4 ever.

**Acceptance Scenarios**:

1. **Given** a validated campaign in autonomous mode and a lead whose last touch was 14+ days ago with no reply/bounce and touch < 3, **When** the engine runs, **Then** the next touch is drafted and sent with no operator action.
2. **Given** a lead whose last touch was 10 days ago, **When** the engine runs, **Then** no follow-up is sent.
3. **Given** a lead at touch 3, **When** the engine runs any number of times thereafter, **Then** no further email is ever sent.
4. **Given** a lead in rotation group "China+1 → 60-years → heavyweights", **When** its 3 touches are drafted, **Then** touch 1 uses `china_plus_one`, touch 2 uses `60_years_experience`, touch 3 uses `trusted_by_heavyweights`, each recorded in `message_recipe`.

---

### User Story 3 - A reply or bounce stops everything immediately (Priority: P1)

The instant a lead replies or their address bounces, that lead's entire sequence halts — no further email, and the paired manual LinkedIn step is also cancelled. Following up on someone who already answered is the primary failure the operator wants prevented.

**Why this priority**: This is a safety guarantee, not a feature. A campaign that "runs itself" but keeps emailing people who already replied actively damages the customer's reputation — the opposite of the pilot's goal. It also depends on reply/bounce detection actually working, which is treated here as co-equal, not assumed (see Dependencies).

**Independent Test**: Log a `replied` event for a lead between touches; run the engine after the 14-day window; confirm no further touch is drafted or sent and the lead's LinkedIn step is marked cancelled. Repeat with a `bounced` event. Separately, verify the reply/bounce detector actually produces those events from a real inbox.

**Acceptance Scenarios**:

1. **Given** a lead with a logged `replied` event, **When** the engine runs at any later point, **Then** no further email is drafted or sent to that lead.
2. **Given** a lead with a logged `bounced` event, **When** the engine runs, **Then** the sequence halts and the lead is excluded from all future selection.
3. **Given** a lead due for a manual LinkedIn note who has since replied, **When** the operator reviews the LinkedIn task list, **Then** that lead's LinkedIn task is shown as cancelled.
4. **Given** a real reply lands in the mailbox, **When** the detector runs, **Then** a `replied` event is logged against the correct lead within the documented detection window.

---

### Edge Cases

- **Subscription usage cap reached mid-batch**: drafting stops cleanly; already-recorded sends are unaffected; remaining leads are picked up on the next run with no duplication.
- **Engine runs twice in one day** (manual + cron, or cron misfire): no lead is selected twice; no duplicate send.
- **A lead replies *after* a touch is drafted but *before* it is delivered**: the pending send is cancelled, not delivered.
- **Personalization context is missing or thin**: in review mode the draft is flagged for the operator; in autonomous mode the email sends with a safe generic opening rather than failing or fabricating details — and the flag is recorded so weak-data leads are auditable.
- **Two leads at the same company**: each is treated independently (no cross-lead suppression in v1).
- **Recipient time zone unknown**: not an issue in v1 — a single fixed sending window applies to all leads regardless of their location.
- **Reply detection lags** (reply exists but not yet logged when a follow-up is due): documented residual risk; the 14-day spacing plus the detector's poll cadence is the mitigation.
- **Operator never approves the held first batch**: drafts remain held indefinitely; nothing sends; no silent expiry.

## Requirements *(mandatory)*

### Functional Requirements

#### Sequencing & autonomy

- **FR-001**: System MUST select, without human initiation, leads eligible for their next touch: last touch ≥ 14 days ago (or never contacted), no `replied` or `bounced` event, and current touch number < 3.
- **FR-002**: System MUST send no more than 3 email touches to any lead, ever.
- **FR-003**: System MUST space consecutive touches to the same lead at least 14 days apart.
- **FR-004**: System MUST support two modes: **review mode** (every batch, including follow-ups, drafts-only until per-email operator approval) and **autonomous mode** (runs follow-ups on schedule with no operator action between runs). A campaign MUST start in review mode and MUST transition to autonomous mode **only by an explicit operator action**; the system MUST NOT self-promote. The mode MUST be reversible back to review mode by the operator.
- **FR-005**: System MUST be idempotent: running it more than once in a period MUST NOT produce duplicate sends.
- **FR-006**: System MUST resume cleanly after an interrupted or capped run, continuing from where it stopped without re-sending or sending partially drafted emails.

#### Reply/bounce hard stop

- **FR-007**: System MUST halt a lead's entire sequence immediately upon a logged `replied` or `bounced` event for that lead.
- **FR-008**: System MUST cancel a lead's pending manual LinkedIn step when that lead's sequence is halted.
- **FR-009**: System MUST never deliver an email that became ineligible (reply/bounce logged) between drafting and delivery.
- **FR-009a**: System MUST include a reply/bounce detector that polls the configured Richbond M365 mailbox and logs `replied` / `bounced` events against the correct lead. This detector is part of this feature, not an external dependency.
- **FR-009b**: The detector MUST run on a cadence at least as frequent as it is needed to satisfy the hard stop given 14-day touch spacing, and MUST fail loud (FR-023) if it cannot reach the mailbox rather than silently letting the sequence proceed blind.
- **FR-009c**: Every delivered email MUST carry a unique per-send marker that survives into replies and bounce notifications, so the detector attributes any inbound message to the exact originating send and lead **immediately and unambiguously** (no heuristic/fuzzy matching). Marker placement MUST be chosen to not harm deliverability.

#### Message construction (rotated angles)

- **FR-010**: System MUST draft each email with a personalized opening derived from the lead's available context, gathered through a **layered source strategy**: (floor, always) official public datasets the brief already maps (e.g. IPEDS, CMS, state licensure); (bonus) the lead organization's own public website and public web search at draft time; (richest) LinkedIn person/company information. The system MUST mark the draft when no usable personalization context could be obtained. *(LinkedIn as a research/personalization input is distinct from FR-025, which governs LinkedIn as an outreach channel.)*
- **FR-011**: System MUST give every lead all three value angles — `china_plus_one`, `60_years_experience`, `trusted_by_heavyweights` — exactly one per touch, in the order defined by that lead's assigned rotation group.
- **FR-012**: System MUST assign leads across three rotation groups so that each value angle appears in each touch position (1st, 2nd, 3rd) in roughly equal volume across the lead population.
- **FR-013**: System MUST record, per send, a structured `message_recipe` capturing at minimum the value angle and the touch number, so a reply can be related to what was sent without re-reading the email text.
- **FR-014**: System MUST NOT name or hint at any specific Richbond customer or reference account (including IKEA) in any email; the `trusted_by_heavyweights` angle MUST remain unnamed until a separate, recorded Richbond authorization exists.

#### Drafting as a replaceable capability

- **FR-015**: The email-drafting capability MUST be isolated behind a fixed input→output contract (in: lead context + pitch + brief + angle + touch; out: subject + body + recipe). Sequencing, sending, and stop logic MUST NOT depend on *how* drafting is performed, so the current Claude-Code-subscription implementation can later be replaced without changing the rest of the engine.

#### Send timing & delivery

- **FR-016**: System MUST decouple drafting time from delivery time.
- **FR-017**: System MUST deliver emails only within a single configured sending window applied to all leads (a US-business-hours window, e.g. Tue–Thu 09:00–11:00 ET; the exact window is a campaign config value). No per-recipient timezone resolution in v1. The system MUST NOT deliver outside this window.
- **FR-018**: System MUST send from the configured Richbond mailbox and ensure replies return to that mailbox's inbox.
- **FR-019**: System MUST embed open- and click-tracking for every delivered email so opens, clicks, replies, and bounces are recorded as events against the lead.

#### Operator visibility & control

- **FR-020**: Operators MUST be able to inspect the pending/drafted queue, including recipient, touch number, value angle, full body text, and any thin-personalization flag, before delivery.
- **FR-021**: While in review mode, the system MUST let the operator act on each drafted email individually — approve, reject, or edit its text — and MUST provide an "approve all remaining" shortcut. Only per-email-approved (or edited-then-approved) drafts are delivered; rejected drafts are never sent. Each reject and each edit MUST be recorded against that draft (FR-022 visibility, auditable later).
- **FR-022**: System MUST surface the list of due manual LinkedIn steps to the operator, paired to touch 2, with cancelled steps clearly marked.
- **FR-023**: System MUST fail loud: a run that cannot complete (cap reached, send failure, missing config, detector unavailable) MUST leave an operator-visible record rather than failing silently.

#### Boundaries

- **FR-024**: System MUST operate on a single customer's single SQLite-backed dataset for v1; multi-customer/multi-tenant operation is explicitly out of scope.
- **FR-024a**: Lead intake is **out of scope** for this feature. The engine MUST consume leads already present in `leads.db` with a `campaign_id` set, and MUST NOT import, buy, or scrape leads itself. A separate dedicated leads-intake tool (supporting client-provided lists, bulk-purchased email lists, and Scout output) is responsible for populating leads; it is its own future component, not part of this engine, `001-dashboard-skeleton`, or `core/`.
- **FR-025**: System MUST treat the manual LinkedIn *outreach note* (the touch-2 connection message) as an out-of-system operator checklist item only; the system MUST NOT automate, send, or track LinkedIn *outreach*. (This does not restrict reading LinkedIn as a personalization input under FR-010.)

#### Cost & measurement

- **FR-026**: Every model call MUST be tagged with the task stage that issued it (at minimum: `research/personalization`, `drafting`; plus any others added later) and have its input/output token counts recorded.
- **FR-027**: System MUST be able to report token consumption and an estimated cost **per email and per stage**, so the operator can decide which model fits which task and whether a paid API is worth it — from real measured numbers, not estimates.
- **FR-028**: Token/cost measurement MUST be implementation-independent (it works whether drafting runs on the subscription today or a paid API later), consistent with the FR-015 drafting seam.

### Key Entities

- **Campaign**: a configured run bound to one customer, carrying its brief (audience), pitch (offer), a status, and a mode (review / autonomous) that changes only by explicit operator action and is reversible.
- **Lead**: a prospect within a campaign, carrying personalization context, an assigned rotation group, a current touch number, and a derived sequence state (active / halted-by-reply / halted-by-bounce / completed).
- **Rotation group**: one of three orderings of the three value angles, ensuring each angle is used in each touch position roughly equally across the population.
- **Send**: one email for a lead at a specific touch number, carrying subject, body, the structured `message_recipe`, and (in review mode) a per-draft state: pending / approved / edited / rejected / delivered.
- **Event**: append-only record of what happened to a lead (`sent`, `opened`, `clicked`, `replied`, `bounced`, status changes) — the substrate the learning layer reads.
- **Message recipe**: the structured, machine-readable description of what shaped this email — at minimum value angle and touch number — recorded per send.
- **Manual LinkedIn task**: an operator-facing checklist item paired to touch 2, outside the instrumented system, cancellable by the hard stop.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A validated campaign in autonomous mode completes a full 3-touch, 6-week run with **zero operator actions** between switching to autonomous and completion (excluding the manual LinkedIn steps).
- **SC-002**: **Zero** emails are delivered to a lead after that lead's reply or bounce was recorded, across the entire pilot.
- **SC-003**: **Zero** duplicate sends: no lead receives the same touch twice, including across interrupted/capped/re-run cycles.
- **SC-004**: **100%** of delivered emails have a stored, queryable `message_recipe` (value angle + touch number).
- **SC-005**: The pilot produces a **qualitative** read of outreach: the count and content of replies, the objections raised, and whether each value angle ever provoked a reply at all. It does **not** claim a statistically significant "winning angle" — pilot volume is too low for that, and this is accepted by design.
- **SC-006**: Each value angle appears in each touch position (1st/2nd/3rd) within ±10% of an even split across the population, so position bias does not silently favor one angle.
- **SC-007**: **100%** of emails are delivered within the defined recipient business-hours window; none outside it.
- **SC-008**: A run that hits the subscription usage cap results in **zero** lost, duplicated, or partially-sent emails.
- **SC-009**: **Zero** emails name or hint at a specific Richbond customer/reference account during the pilot.
- **SC-010**: The reply/bounce detector demonstrably logs a `replied`/`bounced` event for a real test message within its documented detection window (the hard stop is verified, not assumed).
- **SC-011**: After a real test batch, the operator can read a true cost-per-email figure broken down by stage (research/personalization vs. drafting), sufficient to make an informed model-choice and paid-API decision.

## Assumptions

- **Engine host & LLM**: The drafting work runs **first** on the operator's existing Claude Code subscription, triggered headless by a scheduler on a server the operator already controls (same pattern as their existing Zeno stack). A paid Anthropic API is **not ruled out** — the explicit intent is to measure real cost-per-email per stage on the subscription first (FR-026/27, SC-011), then decide which model fits which task and whether paying is worth it. Subscription usage caps are a hard runtime constraint while on the subscription: drafting runs in small throttled batches off-peak (≈02:00–06:00 server time). Per FR-015 the implementation is replaceable without reworking the engine.
- **Learning is qualitative, not statistical**: pilot scale is low (low hundreds of leads). Splitting into clean A/B cells would yield only a handful of replies per cell — indistinguishable from noise. The design therefore sends all three angles to every lead to maximize replies, and treats reply content as the real signal. A statistically valid angle comparison is explicitly deferred to a larger later phase.
- **Reply/bounce detection is in-scope** (clarified 2026-05-19): built inside this feature as a minimal M365 inbox poller (FR-009a/b), verified by SC-010. Not an external dependency.
- **Personalization source — resolved (layered, FR-010)**: official public datasets are the guaranteed floor; public web/site lookup is the bonus; **LinkedIn and any other source are permitted** as research/personalization inputs. The VISION.md "no behind-login sources" anti-goal was dropped entirely by explicit operator decision (2026-05-19, recorded in VISION.md) — no source is excluded preemptively. Manual LinkedIn lookup during review mode is the simplest v1 path; automated LinkedIn or a paid data vendor is a growth-phase choice, not a v1 plan blocker. Thin-personalization flag + safe-generic fallback remain the floor.
- **Existing infrastructure is reused**, not rebuilt: lead database (`leads`/`sends`/`events`/`tracked_links`), brief/pitch loaders (`core/`), open-pixel + click-redirector (`tracking/`), M365 Graph send/auth/revoke (`outreach/`). This feature is the unbuilt drafting + sequencing layer ("built last" in `foundation-schemas.md`), plus a new per-send `message_recipe` (the slot `foundation-schemas.md` reserved for `variant_id`).
- **Send window**: one fixed configured US-business-hours window applies to all leads in v1 (clarified 2026-05-19); per-lead timezone resolution is explicitly deferred.
- **Single operator, single customer (Richbond)** for v1; Postgres/multi-tenant migration deferred to a real second customer.
- **Out of scope (in `001-dashboard-skeleton`)**: the shareable read-only dashboard, factored analytics rollups, and the nightly analyst narrative. This spec only guarantees the data those consume.
- **Out of scope (separate future leads-intake tool)**: importing client-provided lead lists, ingesting bulk-purchased email lists, and Scout lead-finding. The engine assumes `leads.db` is already populated with `campaign_id`-tagged leads (FR-024a).

## Dependencies

- `core/` — lead database schema, brief/pitch YAML loaders. Requires a schema addition: per-send `message_recipe`, plus lead rotation-group and mode tracking.
- `tracking/` — open-pixel + click-redirector; emails must be injected with its tokens.
- `outreach/` — M365 Graph send/auth/revoke; extended from single-send to engine-driven sends.
- *(Reply/bounce detection is no longer an external dependency — it is built by this feature, FR-009a/b.)* It still depends on `outreach/` M365 auth having mailbox read access.
- **Personalization context source** — resolved: layered (official public datasets + public web/site + LinkedIn). No longer a plan blocker; the LinkedIn-at-scale method (manual-in-review now → automation/vendor later) is a deliberately phased decision.
- **Token/cost accounting** — per-stage token counting must be wired from first run (FR-026/27) so the subscription-vs-paid-API decision is data-driven.
- A scheduler on an operator-controlled host capable of triggering headless Claude Code runs.
- A separate **leads-intake tool** (future, not built here) to populate `leads.db` with `campaign_id`-tagged leads from client lists, bulk-purchased lists, or Scout (FR-024a).

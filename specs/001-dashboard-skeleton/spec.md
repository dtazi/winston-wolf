# Feature Specification: Dashboard Skeleton

**Feature Branch**: `001-dashboard-skeleton`
**Created**: 2026-05-04
**Status**: Draft (clarifications applied 2026-05-04; post-analysis fix pass applied 2026-05-04; follow-up fix pass applied 2026-05-04)
**Input**: User description: "Build the Dashboard skeleton for Winston Wolf — the foundational web interface that all other modules will plug into. Phase 1 of the platform: a control panel and CRM with login, lead table, lead profile, campaign manager, email performance, scout mission status, AI spending tracker, and Admin-only User Management + Settings. Two roles (Admin, Member). Single tenant in Phase 1 (Richbond) but every entity scoped by tenant_id. Mock data for any module that does not yet exist. Strict tenant isolation, action logging, no plaintext prospect data in logs, encrypted API keys."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin authenticates and inspects the lead pipeline (Priority: P1)

An Admin user from Richbond logs in, lands on the Dashboard, sees the persistent
stats bar with current pipeline counts, browses the Lead Table, filters and
sorts to find a specific prospect, and opens that prospect's profile to review
their full engagement history.

**Why this priority**: This is the demo. Without this end-to-end flow, the
Dashboard delivers no perceptible value. It also exercises every cross-cutting
concern (auth, tenant scoping, action logging, mock-data wiring, the persistent
stats bar) — which means everything else can be added incrementally on top.

**Independent Test**: Given a populated mock dataset, an Admin user can sign
in with valid credentials and, within the same session, navigate Login → Lead
Table → Lead Profile. They see correct stats in the bar, the lead they
searched for in the table, and a complete history (mock sent-email content,
mock open/click events, mock company background, a reply indicator if the
prospect has replied) on the profile page — all without external help.

**Acceptance Scenarios**:

1. **Given** valid Admin credentials, **When** the user submits the login form, **Then** they are routed to the Dashboard and the persistent stats bar shows non-zero pipeline counts from the mock dataset.
2. **Given** the user is on the Lead Table, **When** they apply a filter (e.g., status = "contacted"), **Then** the table re-renders showing only matching leads and the visible row count updates.
3. **Given** a lead row is visible, **When** the user clicks the row, **Then** the Lead Profile loads showing the lead's attributes, full mock sent-email history with content, open/click timestamps, company background, and — if the prospect has replied — a reply indicator with timestamp (but no reply content).
4. **Given** invalid Admin credentials, **When** the user submits, **Then** the login is rejected with a generic error message, the failed attempt is logged with a timestamp and a one-way hash of the submitted email (never the raw email), and after a configured threshold further attempts from the same source are temporarily blocked.

---

### User Story 2 - Member uses the same lead views with restricted access (Priority: P1)

A Member user from Richbond logs in and reaches the same lead-related views
(Lead Table, Lead Profile, persistent stats bar). The User Management and
Settings entries do not appear in the navigation. Direct URL navigation to
Admin-only routes is rejected.

**Why this priority**: Tied for P1 with US1 because role-based access is a
security requirement, not polish. Shipping US1 without role enforcement would
be a regression against Article 3 (Security is Non-Negotiable). Both Admin
and Member flows need to demo at the same time.

**Independent Test**: A Member user can log in, browse leads, open lead
profiles, and see the persistent stats bar — but the navigation does not
display "User Management" or "Settings", and direct URL navigation to those
routes returns an authorization error.

**Acceptance Scenarios**:

1. **Given** valid Member credentials, **When** the user is signed in, **Then** the left-nav shows the Member-accessible sections only (no User Management, no Settings).
2. **Given** a signed-in Member, **When** they browse to a lead profile, **Then** the page renders identically to what an Admin sees (same data, same fields).
3. **Given** a signed-in Member, **When** they manually navigate to the Settings or User Management URL, **Then** they receive an authorization-denied response and the attempt is logged.
4. **Given** a signed-in Member viewing the AI Spending tracker, **When** they look for a way to change the cap, **Then** no edit control is visible or reachable.

---

### User Story 3 - Campaign and email-performance visibility (Priority: P2)

Either role opens Campaign Manager to see all campaigns with their per-campaign
metrics (and the campaign owner), drills into an individual campaign for
detail, then opens Email Performance to view aggregate analytics broken down
by segment, hook, personalisation depth, and sequence step, with trends over
time.

**Why this priority**: This is the "how is my outreach performing?" loop —
important but only meaningful once the lead/profile views are working. All
values use mock data in Phase 1.

**Independent Test**: A signed-in user can navigate from the left-nav to
Campaign Manager, see at least one mock campaign with its metrics and named
owner, click into the campaign for detail, then navigate to Email Performance
and toggle the breakdown axis to confirm the chart updates.

**Acceptance Scenarios**:

1. **Given** the user is on the Dashboard, **When** they click "Campaigns" in the nav, **Then** the Campaign Manager loads listing all campaigns from mock data with leads count, sends, replies, click rate, and the campaign owner per row.
2. **Given** a campaign row, **When** the user clicks it, **Then** a campaign detail view loads showing per-campaign breakdowns and the owner.
3. **Given** the user is on Email Performance, **When** they change the breakdown to "by hook used", **Then** the displayed metrics regroup accordingly and the trend chart updates.

---

### User Story 4 - Operational visibility: Scout missions and AI spending with at-cap enforcement (Priority: P2)

Either role views the Scout Mission Status panel (currently running missions
and recent past missions, all mock) and the AI Spending tracker (current
spend, spend-over-time, breakdown by module, configured cap). Admins can
adjust the cap; Members see the same data but the cap control is hidden.
When current spend reaches the cap, the system hard-blocks new AI-consuming
actions while letting in-flight work finish gracefully.

**Why this priority**: Constitutional requirement (Article 4 — AI Cost
Awareness) makes spend visibility a first-class feature. At-cap enforcement
is what turns the cap from advisory into binding.

**Independent Test**: A signed-in Admin can navigate to AI Spending, see the
current period's spend vs. cap, change the cap, and see the change persist
across page refreshes. A signed-in Member sees the same spending data but no
editable cap control. When mock spend is at or above the cap, the dashboard
visibly disables every "new AI action" surface (regenerate, new chat
exchange, new variant proposal, new scout mission launch) and shows the
reason; previously-approved sends and in-flight calls continue.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin, **When** they open AI Spending, **Then** they see current spend, spend-over-time, per-module breakdown, the configured cap, and a control to change the cap.
2. **Given** a signed-in Admin changes the cap to a new value and saves, **When** they refresh, **Then** the new cap is shown and the change is logged with timestamp + user ID + tenant ID.
3. **Given** a signed-in Member opens AI Spending, **When** the page renders, **Then** all the same data is shown but no cap-change control is visible or reachable.
4. **Given** the user opens Scout Mission Status, **When** the page loads, **Then** at least one mock running mission is shown with progress (leads found, budget consumed, time elapsed) and recent past missions appear with outcomes.
5. **Given** current spend exceeds the configured warning threshold, **When** any page renders the persistent stats bar, **Then** the AI spending element shows a visual warning indicator.
6. **Given** current spend reaches 100% of the configured cap, **When** the user navigates to the Approval Queue, AI Chat, Variant Selection, or Mission Launcher surface, **Then** all controls that would start a new AI-consuming action are visibly disabled with a clear at-cap explanation; previously-approved emails still send and any running scout mission continues processing its current batch.
7. **Given** the system is in the at-cap state, **When** an Admin raises the cap or the cap period resets, **Then** the previously-disabled controls become available again automatically with no further configuration.

---

### User Story 5 - Connect a personal email and become a campaign owner (Priority: P2)

A user opens their personal Settings, connects their work email account, and
becomes eligible to be assigned as a campaign owner. An Admin can then
assign or transfer campaign ownership to that user. A user without a
connected email is visibly blocked from being made an owner.

**Why this priority**: The whole outreach loop sends FROM the owner's
connected email — replies arrive in the owner's inbox naturally. Without
this, no campaign can launch and the approval/variant/chat flows have
nothing to operate on.

**Independent Test**: A signed-in user opens their personal Settings,
completes the Connect Email flow (mock connection in Phase 1), and the
Connected Email status becomes "connected". An Admin can then assign that
user as a campaign owner; an unconnected user remains ineligible. Ownership
transfers between two connected users are recorded in the action log.

**Acceptance Scenarios**:

1. **Given** a signed-in user with no connected email, **When** they open their personal Settings, **Then** they see a "Connect Email" section showing status "not connected".
2. **Given** a signed-in user, **When** they complete the Connect Email flow, **Then** their status becomes "connected", their connected email address is shown (the credentials/tokens are not), and the connection is logged.
3. **Given** an Admin selecting a campaign owner, **When** they look at the candidate list, **Then** users without a connected email are either hidden or visibly disabled with a reason ("no connected email").
4. **Given** an Admin transfers a campaign from one connected user to another connected user, **When** the change is saved, **Then** the new owner is shown on the campaign and the transfer is logged with timestamp, transferring user, new owner, and campaign ID.
5. **Given** a user disconnects their email, **When** they confirm, **Then** the system displays an immediate in-app warning, sends a notification to their registered backup notification email, logs the disconnect, and starts a 24-hour grace clock during which their owned campaigns continue running. The user becomes ineligible to be assigned as the owner of any *new* campaign immediately. After 24 hours without reconnection, all of their owned campaigns auto-pause and each campaign's designated backup owner — or tenant Admins, if no backup owner is designated or the backup is itself disconnected — is notified. Every auto-pause and every notification is logged.

---

### User Story 6 - Variant selection at campaign launch (Priority: P2)

When a campaign is being launched, the AI proposes one or more email
candidates (default 5, configurable per campaign — minimum 1). When 2 or
more candidates are proposed, the campaign owner reviews them side-by-side,
each with its AI reasoning panel, and selects how many to actually test
(default 2). When exactly 1 candidate is proposed, the owner sees a
confirm-or-regenerate flow on that single candidate (the reasoning panel is
still shown). Rejected candidates are discarded; selected (or confirmed)
variants enter the live test.

**Why this priority**: Variant selection is the gate between AI proposing
content and the campaign actually putting that content in front of prospects.
It's where the human owner exercises judgment over what gets sent. Required
for a credible Outreach demo.

**Independent Test**: A signed-in campaign owner enters the Variant
Selection view for a launching campaign. With N=5, they see 5 mock candidate
emails side-by-side each with its reasoning panel, select 2, and save — the
3 unselected variants are no longer reachable and the 2 selected ones
become the campaign's live test variants. With N=1, they see a single mock
candidate with its reasoning panel and either confirm (the candidate enters
the live test) or regenerate (a fresh single candidate replaces it).

**Acceptance Scenarios**:

1. **Given** a campaign is being launched, **When** the owner opens Variant Selection, **Then** the configured number of mock candidate emails is shown — side-by-side when N≥2 (N defaults to 5, configurable per campaign), or as a single-candidate confirm-or-regenerate flow when N=1 — each candidate showing subject, body, and a read-only AI reasoning panel.
2. **Given** the owner is in Variant Selection, **When** they select 2 of the candidates and save, **Then** those 2 enter the live test and the others are discarded — discarded candidates are not stored for future reuse.
3. **Given** the owner has selected variants, **When** they revisit the campaign detail view, **Then** the selected variants are visible as the campaign's live variants.
4. **Given** the system is at the AI spending cap, **When** the owner opens Variant Selection for a campaign that has not yet been launched, **Then** the variant proposal action is visibly blocked with the at-cap reason.

---

### User Story 7 - Approve, edit, regenerate proposed emails with reasoning panel and AI chat (Priority: P2)

For every campaign in approval mode, the AI generates a proposed email per
recipient. These appear in an approval queue specific to the campaign owner.
The owner sees the recipient, subject, body, the AI reasoning panel, and an
AI chat panel beside it. They can edit subject and body, ask the AI questions
or give it direction, then approve and send, regenerate, or reject the
proposal.

**Why this priority**: This is the per-email control loop that makes the
Outreach module trustable. Without it, "approval mode" (Article 6) has no UI.

**Independent Test**: A signed-in campaign owner enters their approval queue,
sees a mock proposed email with all fields and reasoning panel, asks the AI
a question via the chat panel (mock response in Phase 1), edits the subject,
clicks "Approve and send", and the email moves out of the queue. They then
regenerate another proposal (returns a fresh mock draft) and reject a third
(it's discarded). Every action is logged.

**Acceptance Scenarios**:

1. **Given** a campaign is in approval mode and has proposed emails, **When** the campaign owner opens their approval queue, **Then** they see only their campaigns' proposed emails — items belonging to other owners' queues are not visible to them.
2. **Given** an owner viewing a proposed email, **When** the page renders, **Then** they see recipient (lead reference), subject, body, the AI reasoning panel (hook used, tone choice, assumptions about the recipient, lead-profile context referenced), and an AI chat panel beside the email.
3. **Given** an owner has edited the subject or body, **When** they save or approve, **Then** the edit is logged with timestamp and user ID and the sent message reflects the edited content.
4. **Given** an owner clicks "Regenerate", **When** the action runs, **Then** a fresh proposed email replaces the current one with its own reasoning panel; the previous draft is discarded.
5. **Given** an owner clicks "Reject", **When** the action runs, **Then** the proposed email is discarded and removed from the queue; no email is sent to that recipient for that proposal cycle.
6. **Given** an owner asks a question or gives guidance in the AI chat, **When** they submit, **Then** the exchange is recorded against this specific email draft and may inform subsequent regenerations.
7. **Given** the system is at the AI spending cap, **When** an owner views a proposed email, **Then** "Approve and send" remains available (the email is already drafted), but "Regenerate" and AI chat input are visibly disabled with the at-cap reason.

---

### User Story 8 - Admin manages members and tenant settings (Priority: P3)

An Admin user opens User Management to invite a new member, change an existing
member's role, deactivate a member, and view login history. They open
Settings to configure API keys for data sources and email-sending platforms,
adjust the AI spending cap, and tune alert thresholds.

**Why this priority**: Without this, the platform is unusable beyond the
seeded demo accounts — but for the Phase 1 demo to Richbond, Settings can be
pre-seeded and Member accounts pre-created. So it ships, but after the
data-viewing and outreach-loop flows are solid.

**Independent Test**: A signed-in Admin can invite a new member (the new
account appears in the member list), change an existing Member to Admin,
deactivate a member (they can no longer log in), and view login history.
The Admin can also save an API key in Settings and see only its masked form
on subsequent loads.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin on User Management, **When** they invite a new member by email and submit, **Then** the new member appears in the list with status "invited" and the invite is logged.
2. **Given** a Member-role user in the list, **When** the Admin changes their role to Admin and saves, **Then** the change is persisted, logged, and the next login by that user grants Admin privileges.
3. **Given** an active member, **When** the Admin deactivates them, **Then** that user can no longer authenticate and the deactivation is logged.
4. **Given** an Admin on Settings, **When** they paste an API key into the email-platform field and save, **Then** subsequent loads of Settings show the key in masked form (e.g., last 4 characters only) and the full key is never returned by any API.
5. **Given** an Admin on Settings, **When** they adjust the AI spending warning threshold (e.g., from 80% to 75%) and save, **Then** the new threshold persists across page reloads and the change is logged with timestamp, user ID, tenant ID, previous value, and new value.

---

### User Story 9 - Reply notification queue (Priority: P3)

A signed-in user opens the Reply Notification view to see which leads have
replied. The view is notification-only: it surfaces the *fact* of a reply so
the campaign owner knows where to focus, but it does not show reply content
and offers no actions. Reply content lives in the owner's connected email
inbox.

**Why this priority**: Important for closing the loop on outreach, but
secondary to the lead-viewing and approval flows. Crucially: replaces the
former "take over" concept entirely — the agent's outreach scope ends
automatically the moment a prospect replies.

**Independent Test**: A signed-in user opens Reply Notifications, sees a list
of leads from mock data who have replied (with timestamp and the campaign
that drove the reply), and confirms the view exposes no reply text and no
action buttons. Clicking a row navigates to the Lead Profile, where the
reply indicator is also visible.

**Acceptance Scenarios**:

1. **Given** any signed-in user, **When** they open the Reply Notification view, **Then** they see a list of leads (within their tenant) who have replied, each row showing the lead reference, the campaign, and the reply timestamp — and nothing else interactive.
2. **Given** the Reply Notification view is open, **When** the user inspects any row, **Then** no reply content (subject, body, snippet) is shown anywhere on the page or in any underlying API response.
3. **Given** a row in the Reply Notification view, **When** the user clicks it, **Then** they navigate to that lead's profile, where the reply indicator and timestamp are also visible.
4. **Given** a prospect replies to a campaign email, **When** the system processes that reply, **Then** the agent's outreach for that lead automatically ends — no further automated emails are queued or sent for that lead in that campaign — and the lead appears in the campaign owner's Reply Notification view.

---

### Edge Cases

- **Empty pipeline**: when no leads exist for the tenant, the Lead Table shows an empty state with guidance and the persistent stats bar shows zeros (not errors).
- **Stale session**: when a user's session expires, the next protected request redirects to login with the originally-requested destination preserved for post-login redirect.
- **Concurrent role change**: if an Admin demotes a logged-in Member's user mid-session, the next protected action by that user re-checks role from the source of truth and is rejected if they no longer have access.
- **Cross-tenant URL probing**: if any user attempts to load a resource (lead ID, campaign ID, mission ID, draft ID, chat ID) belonging to another tenant, the system returns the same not-found response it returns for a non-existent ID — leaking no information about the foreign resource's existence.
- **Cross-owner queue probing**: if a non-owner user (even within the same tenant) attempts to load another owner's approval-queue items, the system returns the same not-found response a missing item would yield.
- **API-key disclosure attempt**: any UI surface or API endpoint that returns Settings data — or any user's connected-email credentials/tokens — must redact the secret material; an attacker who reads the response cannot reconstruct it.
- **Mock-to-real swap**: when a real module (Scout, Outreach, Learning Engine, AI Chat) ships and replaces its mock source, the Dashboard views must continue rendering with no spec changes — only the data binding changes.
- **Failed-login flooding**: when a single source exceeds the configured failed-login rate, further attempts from that source are temporarily blocked and the block window is logged.
- **Sanitisation of sent emails**: when a stored sent-email body contains script-like or markup content, the Lead Profile and Approval Queue render it inert (no script execution, no broken layout).
- **Spending-warning latency**: if a burst of AI activity pushes spend past the warning threshold between page renders, the next render of the stats bar reflects the warning state.
- **Cap reached during owner review**: if the cap is hit while an owner is reviewing the approval queue, "Approve and send" remains available for already-drafted emails, while "Regenerate", "AI chat input", and "New variant proposal" controls visibly disable with the at-cap reason.
- **Cap raised mid-block**: when an Admin raises the cap or the cap period resets, previously-disabled new-AI-action controls re-enable automatically — no further configuration or page reload required beyond the next surface render.
- **Cap lowered below current spend**: if an Admin lowers the AI spending cap to a value below current period spend, the system MUST enter the at-cap state immediately and treat the lowered cap as if it had been reached organically — the inverse of FR-067 applies (previously-available controls become disabled at the next surface render).
- **Owner email disconnect with active campaigns**: when a campaign owner's primary connected email enters a disconnected state, the system gives the user a 24-hour grace period during which campaigns continue running with retry-on-unreachable and pause-on-rejection behaviour (per FR-126). If the user has not reconnected by the end of the grace period, all of their active campaigns auto-pause and each campaign's designated backup owner is notified per FR-127. The disconnect itself, every per-campaign pause-on-rejection during grace, every auto-pause at grace expiry, and every backup-owner / Admin notification are logged.
- **Reconnect after grace expiry**: if the owner reconnects their primary email *after* the 24-hour grace has already expired and campaigns have auto-paused, those campaigns MUST NOT auto-resume. The owner MUST manually resume each paused campaign; pause history is preserved in the action log.
- **Backup owner unreachable at auto-transfer**: if a primary owner's 24-hour grace period expires and the campaign's designated backup owner has since disconnected their own email — or no backup owner was designated — the campaign remains paused and tenant Admins receive a notification asking them to designate a new owner manually. The system MUST NOT auto-transfer the campaign to a Connected user picked at random.
- **Both primary and backup owner disconnected at auto-transfer time**: if a primary owner's grace expires and the designated backup owner is also currently disconnected (their own primary is in a disconnected state), the campaign MUST remain paused, all tenant Admins MUST be notified, and ownership MUST NOT be auto-transferred to any other user. Admins must manually designate a new owner.
- **Owner deactivation with active campaigns**: when an Admin deactivates a user who owns active campaigns, those campaigns auto-pause and surface a warning until ownership is transferred.
- **Variant count edge values**: a campaign configured with N=1 proposed variant displays a confirm-or-regenerate flow (not side-by-side) per FR-150; a campaign configured with N>1 always shows the side-by-side selection view, even if the owner only intends to test 1.
- **Reply-text leak attempt**: any UI or API request that asks for reply content for a lead returns no body — only the fact of the reply (timestamp, campaign reference). The system has no path that surfaces reply text in the dashboard.
- **Reply arrives during in-flight regenerate**: if a prospect replies while a regenerate operation for that same lead is mid-flight, the regenerate MUST be auto-cancelled, the in-flight draft MUST be discarded, and the lead's status MUST flip to `replied` per FR-183. No new draft is added to the approval queue for that recipient.
- **Deactivated user attempts login**: a deactivated user submitting valid credentials sees the same generic failed-login response a wrong-password user sees, and the attempt is logged as "deactivated user".

---

## Requirements *(mandatory)*

### Functional Requirements

#### Authentication & Session

- **FR-001**: System MUST authenticate users via email and password.
- **FR-002**: System MUST log every login attempt with a timestamp, source identifier (see Source Identifier in Key Entities), and outcome. Successful attempts MUST reference the authenticating user by user ID. **Failed attempts MUST NOT log the raw email string submitted**; instead, they MUST reference the submitted email via a stable one-way hash that always produces the same value for the same input (so rate-limiting and enumeration-defence still work) but is cryptographically irreversible (no rainbow-table recovery of common email addresses). The system MUST NEVER log the raw email string used in a failed login attempt — only the hash, the source identifier, and the timestamp.
- **FR-003**: System MUST rate-limit failed login attempts from the same source. Rate-limiting MUST group attempts by the email-hash from FR-002 and the source identifier — not by the raw email.
- **FR-004**: System MUST end a user's session on logout and reject subsequent authenticated requests under that session.

#### Authorization & Tenant Isolation

- **FR-010**: System MUST enforce two roles per user: Admin and Member.
- **FR-011**: System MUST hide Admin-only navigation entries (User Management, Settings) from Member users.
- **FR-012**: System MUST reject any direct API or URL access to Admin-only resources by Member users with an authorization-denied response, and MUST log the attempt.
- **FR-013**: Every user MUST belong to exactly one tenant.
- **FR-014**: System MUST scope every data query by `tenant_id`. No code path may return data belonging to a tenant other than the requesting user's tenant.
- **FR-015**: System MUST return identical "not found" responses for resources that exist in other tenants and resources that do not exist anywhere — to prevent enumeration of cross-tenant data.
- **FR-016**: Per-owner resources (approval-queue items, AI chat exchanges) MUST be scoped to their owner. Cross-owner probing within the same tenant MUST return the same "not found" response a missing item would yield.

#### Persistent Stats Bar

- **FR-020**: System MUST display a persistent stats bar on every authenticated page.
- **FR-021**: Stats bar MUST show: total leads in pipeline, leads contacted this week, replies received this week, active campaigns count, and current AI spending against the configured cap.
- **FR-022**: Stats bar MUST visually indicate when current AI spending crosses a configured warning threshold and MUST display a distinct, prominent at-cap state when current spending reaches 100% of the configured cap.

#### Lead Table & Profile

- **FR-030**: System MUST display a Lead Table with columns: name, company, title, current status, last touchpoint, lead score, sequence stage.
- **FR-031**: Lead Table MUST be sortable by every visible column.
- **FR-032**: Lead Table MUST be filterable by campaign, status, vertical, and lead score.
- **FR-033**: System MUST navigate to the corresponding Lead Profile when a row is clicked.
- **FR-034**: Lead Profile MUST display lead attributes (title, seniority, company size, industry, location), all sent emails with their content, open and click events with timestamps, current status and sequence stage, company background, and a clear indicator (with timestamp) if the prospect has replied. Lead Profile MUST NOT display any reply content (no subject, no body, no snippet).
- **FR-035**: The Lead Profile MUST NOT contain a "take over" button or any equivalent control. Outreach automation for a lead ends automatically when the prospect replies — no manual takeover is required (and none is offered).
- **FR-036**: System MUST sanitise stored sent-email content before rendering it in any view (Lead Profile, Approval Queue) so that no embedded markup or script can execute.

#### Campaign & Email Performance

- **FR-040**: System MUST display a Campaign Manager listing all active and past campaigns with leads count, sends, replies, click rate, and the campaign owner per campaign.
- **FR-041**: Campaign Manager MUST navigate to a Campaign Detail view when a row is clicked.
- **FR-042**: System MUST display an Email Performance view showing aggregate reply rate, click rate, and bounce rate, broken down by segment, hook used, personalisation depth, and sequence step, with trends over time.

#### Scout Mission Status

- **FR-050**: System MUST display a Scout Mission Status panel showing currently running missions with progress (leads found, budget consumed, time elapsed) and recent past missions with outcomes — all sourced from mock data in Phase 1.

#### AI Spending & Cap Enforcement

- **FR-060**: System MUST display an AI Spending tracker showing current spend, spend-over-time, cost broken down by module, and the configured cap.
- **FR-061**: Admin users MUST be able to change the configured cap; the change MUST be logged.
- **FR-062**: Member users MUST see the same spending data but MUST NOT have any control to change the cap.
- **FR-063**: When current spend reaches 100% of the configured cap, the system MUST hard-block the start of any new AI-consuming action (new email generation, new variant proposal, new AI chat exchange, new scout-mission lead pull, regeneration of an existing draft) until the cap is raised or the cap period resets.
- **FR-064**: At-cap enforcement MUST allow in-flight AI calls to complete naturally, and MUST allow already-queued sends that do not require new AI (e.g., a previously-approved email) to send.
- **FR-065**: At-cap enforcement MUST NOT abort a running scout mission. A running mission MUST complete its current batch but MUST NOT pull additional leads. New scout missions MUST NOT start until the cap is raised or the period resets.
- **FR-066**: The dashboard MUST surface the at-cap state in: the persistent stats bar, the AI Spending tracker, the Approval Queue (Regenerate and Chat input disabled), Variant Selection (new proposals disabled), AI Chat (input disabled), Scout Mission Status (new-mission action disabled), and the Mission Launcher entry point. Each disabled control MUST display the at-cap reason in plain language.
- **FR-067**: When the configured cap is raised by an Admin or the cap period resets, previously-blocked controls MUST become available again automatically without further configuration.
- **FR-068**: AI responses that can be deterministically reused MUST be cached. Every AI-generating feature MUST define a cache key strategy and a time-to-live (TTL). At minimum this applies to: regenerated email drafts (FR-143), AI Chat exchanges where an identical question targets the same draft (FR-170), and AI Reasoning regeneration on identical inputs (FR-160). Cache hits MUST NOT count against the AI spending cap; cache misses (which trigger an actual model call) MUST count. Every cache hit MUST be marked with a `cache_hit: true` boolean on the user-action log entry that triggered it (e.g., `email_regenerate`, `ai_chat_exchange`, `variant_proposal_generated`); when `cache_hit` is true, the entry MUST also include a reference ID pointing to the original AI invocation log entry (FR-092) whose response is being reused. The `cache_hit` flag is for forensic and analytics purposes only — it does NOT affect cap accounting. Cache TTL MUST be specified per feature in Settings (Tenant); default values are: AI Chat exchanges 1 hour, Email Drafts 24 hours, Email Variants 24 hours, AI Reasoning panels 24 hours. Per-feature overrides via Settings are allowed but MUST be bounded between 1 minute and 7 days.

#### User Management (Admin only)

- **FR-070**: Admin users MUST be able to invite new members, change a member's role, deactivate a member, and view login history.
- **FR-071**: Deactivated members MUST be unable to authenticate; deactivation MUST be logged.

#### Settings (Admin only)

- **FR-080**: Admin users MUST be able to configure tenant-level settings: API keys for data sources and email-sending platforms (encrypted), AI spending cap, AI spending warning threshold, default variant counts (proposed and selected), and per-feature cache TTLs (subject to FR-068 bounds). Tenant Settings MUST NOT include any tenant-wide override for the per-campaign default approval mode — see FR-146.
- **FR-081**: API keys stored in Settings MUST be encrypted at rest.
- **FR-082**: API keys MUST never be returned to any client in full once saved; Settings MUST display only a masked form (e.g., last 4 characters).

#### Action Logging

- **FR-090**: System MUST log every significant action with: timestamp, **module** (one of Configuration, Scout, Outreach, Engagement Tracker, Knowledge Base, Learning Engine, Dashboard, System), action name, tenant ID, actor (user ID for user-initiated actions, System Actor Identifier for system-initiated actions — see Action Log Entry definition in Key Entities), and target resource ID where applicable. User-initiated actions to be logged include (non-exhaustive): login, lead view, setting change, role change, deactivation, member invite, cap change, email connect, email disconnect, ownership transfer, variant selection, email approve, email edit, email regenerate, email reject, AI chat exchange.
- **FR-091**: Prospect personal data (name, email, title, company name) MUST NOT appear in plain text in any log entry; logs MUST reference lead IDs only. The same rule applies to reply content — which the dashboard does not capture in the first place. The same rule applies to the email submitted in failed login attempts (per FR-002).
- **FR-092**: Every AI model invocation MUST be logged with: timestamp, module emitting the call, action name, tenant ID, actor (user ID or System Actor Identifier), model name, estimated input tokens, estimated output tokens, and a reference ID linking the call to the user-facing action that triggered it. AI invocation log entries are the source of truth for AI Spending Records (FR-060) and at-cap accounting (FR-063, FR-068).

#### Data Ownership & Export

- **FR-095**: All client data — leads, campaigns, sent emails, engagement events, action logs, settings, AI drafts, AI variants, AI reasoning records, AI chat exchanges — MUST be designed in a structure that supports full export in standard formats (at minimum CSV and JSON). Phase 1 does NOT require an in-dashboard export UI; the data layer MUST be exportable via direct query when needed. Future phases will add a self-serve export UI.
- **FR-096**: NO client data may be used to train shared models, fine-tune cross-tenant prompts, or inform another tenant's campaigns in any way. Within a single tenant, *intra-tenant* learning IS permitted and intentional — the Learning Engine improves a client's future campaigns from that same client's past results. The prohibition applies strictly across tenant boundaries.

#### Mock Data

- **FR-100**: System MUST operate end-to-end against mock data for any field sourced from modules that do not yet exist (Scout, Outreach including email drafts and variants, Learning Engine, AI Chat, AI Reasoning) during Phase 1. The Dashboard skeleton in Phase 1 does NOT surface any Knowledge Base data directly — Knowledge Base is consumed by the future Outreach module, not by the Dashboard — so no Knowledge Base mock data is required in this feature.
- **FR-101**: Mock-data structure MUST mirror the planned real-data structure so that future module integration is a wiring change, not a redesign change.

#### Navigation & Visual Design

- **FR-110**: System MUST display a persistent left-side navigation on every authenticated page.
- **FR-111**: System MUST be usable on standard laptop and desktop screen sizes; mobile layout is out of scope for Phase 1.
- **FR-112**: Interface MUST be in English only for Phase 1.

#### Connected Email (Per-User Sending Identity)

- **FR-120**: Each user's personal Settings MUST contain a "Connect Email" section showing connection status, the connected email address (when connected), and controls to connect or disconnect.
- **FR-121**: Connected-email credentials and tokens MUST be encrypted at rest.
- **FR-122**: Connected-email credentials and tokens MUST never be returned to any client in full once saved; only the email address and connection status are displayed.
- **FR-123**: A user without a connected email MAY use the platform but MUST NOT be assignable as a campaign owner. The User Management view (Admin) MUST surface this state for each user.
- **FR-124**: Each user MUST register a backup notification email before they may connect a primary sending email. The backup notification email is a personal address — separate from the primary sending address — used solely for system notifications and never used to send cold opens. It is set in personal Settings, MUST be encrypted at rest, and MUST never be returned to any client in full once saved.
- **FR-125**: When a user's primary connected email enters a disconnected state — whether by explicit user action or because the system detects external failure (e.g., token revocation, hard authentication failure, sustained unreachability) — the system MUST: (a) record the disconnect with timestamp and reason, (b) display an immediate in-app warning to the user, and (c) send a notification message to the user's registered backup notification email.
- **FR-126**: For 24 hours following the disconnect event the user MUST have a grace period during which campaigns they own continue running, subject to per-send rules: if a send fails because the primary address is technically valid but temporarily unreachable (transient delivery failure — e.g., transient network failure or rate limit), the send MUST queue and retry; if a send fails because the primary address is actively rejecting mail (permanent delivery failure — e.g., authentication revoked or hard bounce), sends for that specific campaign MUST pause and the owner MUST be notified — other campaigns the user owns are not paused by an active rejection on a different campaign's send. The grace period ends if the user reconnects (cancelling all timeout consequences) or after 24 elapsed hours.
- **FR-127**: If the 24-hour grace period elapses without reconnection, the system MUST automatically pause every campaign owned by the user. For each paused campaign, the system MUST notify the campaign's designated backup owner that they may either take ownership or wait for the original owner to reconnect. If the campaign has no designated backup owner, or the designated backup owner does not currently have a connected email, the campaign MUST remain paused and the system MUST notify all tenant Admins so they can resolve ownership manually. Every auto-pause and every backup-owner or Admin notification MUST be recorded in the action log with timestamp, action name, affected campaign ID, tenant ID, and a System Actor Identifier.
- **FR-128**: Ownership transfers triggered by the 24-hour timeout — whether accepted by the backup owner or completed by an Admin acting on the Admin notification — MUST follow the same logging rules as manual transfers (FR-134), recording timestamp, the previous owner, the new owner, and the campaign ID. If the backup owner declines or does not act, no transfer is recorded; the campaign simply remains paused until the original owner reconnects or another transfer is initiated.

#### Campaign Ownership

- **FR-130**: Every campaign MUST have exactly one owner, selected from the tenant's users at campaign launch.
- **FR-131**: A user MUST have a connected email before they can be assigned or transferred-to as a campaign owner.
- **FR-132**: Cold-open emails for a campaign MUST be sent FROM the owner's connected email address, never from a system or shared address.
- **FR-133**: Replies to a campaign's emails arrive in the owner's connected inbox. The dashboard MUST flag that a reply occurred (lead reference, campaign reference, timestamp) but MUST NOT capture, store, or display reply content.
- **FR-134**: Campaign ownership MUST be transferable to another user with a connected email. Transfers (manual via this FR or system-triggered via FR-128) MUST be recorded as Action Log entries with action name `campaign_ownership_transfer` and structured details capturing previous owner, new owner, campaign ID, and trigger reason (`manual` vs. `timeout`).
- **FR-135**: Every campaign MUST have a backup owner field. At campaign launch, the backup owner MUST be designated from another user (within the same tenant) who has a connected email. The field MAY be null only when fewer than two users in the tenant have connected emails. Once at least two users in the tenant have connected emails, every campaign launched thereafter MUST populate this field, and any existing campaign without a backup owner MUST surface a warning to Admins until the field is populated.
- **FR-136**: A campaign's backup owner MUST be a different user from the campaign's primary owner. The system MUST prevent setting them to the same user; an attempted assignment that would violate this constraint MUST fail with a clear reason.

#### Email Approval Queue

- **FR-140**: When a campaign is in approval mode (per constitution Article 6), proposed emails MUST appear in an approval queue specific to that campaign's owner. The queue MUST be reachable from the dashboard navigation when there are items to act on.
- **FR-141**: Each proposed email in the approval queue MUST display: recipient (lead reference), subject, body, the AI reasoning panel (see FR-160), editing controls for subject and body, and the AI chat panel (see FR-170).
- **FR-142**: The campaign owner MUST be able to edit the subject and body of any proposed email before approving.
- **FR-143**: The approval queue MUST support three actions per proposed email: **approve and send** (sends the email — possibly edited — from the owner's connected address), **regenerate** (returns the email to AI for a new draft, discarding the current draft), **reject** (discards the email; no email is sent for that proposal cycle).
- **FR-144**: All edits to a proposed email — and every approve/regenerate/reject decision — MUST be logged with timestamp and user ID.
- **FR-145**: The approval queue MUST be per-owner. A user other than the campaign's owner MUST NOT see or act on items in that owner's queue, and probing for them MUST return the same response a missing item would yield (per FR-016).
- **FR-146**: Every newly-created campaign MUST default to approval-required mode (per constitution Article 6). Switching the campaign to automated mode MUST require an explicit, deliberate action by the campaign owner — never a default value, never a pre-checked checkbox, never inferred from other settings. There is no tenant-wide override for this default: per Article 6, every new campaign starts in `approval_required` mode without exception, and switching to `automated` is always per-campaign, owner-initiated, and explicitly confirmed (per FR-148).
- **FR-147**: NO email may be sent by the system without one of the following being true at send time: (a) explicit human approval has been recorded against that specific email (via FR-143's "approve and send" action), or (b) the campaign has been explicitly switched to automated mode by the owner. Any third state — including ambiguity, missing approval state, or unresolved approval mode — MUST result in the email NOT being sent and the situation being logged with action name `send_blocked_invalid_state`.
- **FR-148**: Every campaign MUST have an `approval_mode` attribute with one of two values: `approval_required` (the default per FR-146) or `automated`. The campaign owner MUST be able to view and toggle this attribute from the campaign detail view in the Campaign Manager. Toggling from `approval_required` to `automated` MUST require an explicit confirmation step (e.g., a confirmation dialog) — never a single-click toggle. Every change to `approval_mode` MUST be logged with timestamp, user ID, tenant ID, campaign ID, previous value, and new value.

#### Variant Selection

- **FR-150**: For each campaign launch, the AI MUST propose at least 1 email candidate (configurable per campaign, default 5). When 2 or more candidates are configured, the Variant Selection view MUST display them side-by-side. When exactly 1 candidate is configured, the Variant Selection view MUST show that candidate as a confirm-or-regenerate flow rather than a side-by-side comparison.
- **FR-151**: The campaign owner MUST review every proposed candidate, each accompanied by its AI reasoning panel. When 2 or more candidates are configured, the review MUST present them side-by-side. When exactly 1 candidate is configured, the review MUST present that single candidate as a confirm-or-regenerate flow (per FR-150), with the reasoning panel still displayed.
- **FR-152**: The campaign owner MUST select how many candidates to actually test, with a default of 2. Selected variants MUST enter the live test.
- **FR-153**: Rejected (unselected) candidates MUST be discarded. They MUST NOT be retained for future reuse, recommendations, or model training.

#### AI Reasoning Panel

- **FR-160**: Every AI-generated email displayed in the approval queue or variant selection view MUST be accompanied by an AI reasoning panel.
- **FR-161**: The reasoning panel MUST show: the value-proposition hook used, the tone choice, what the AI assumed about the recipient, and what context from the lead profile influenced the draft.
- **FR-162**: The reasoning panel MUST be read-only context for the human and MUST NOT be editable.

#### AI Chat Interface

- **FR-170**: The dashboard MUST provide an AI chat panel beside the approval-queue email view and the variant-selection view.
- **FR-171**: The chat panel MUST allow the campaign owner to converse with the AI about a specific draft — including questions ("why this opener?"), guidance ("make it more direct"), and direction ("lean harder on the tariff angle").
- **FR-172**: Each chat exchange MUST be recorded against the email it relates to and MAY influence subsequent regeneration of that email.
- **FR-173**: Phase 1 ships with mock chat responses; real AI integration arrives with the Outreach module. The chat data structure MUST mirror the planned real structure so that wiring real AI later is plumbing, not redesign.

#### Reply Notification Queue

- **FR-180**: The dashboard MUST provide a Reply Notification view that lists leads (within the user's tenant) who have replied to campaign emails.
- **FR-181**: The Reply Notification view MUST be notification-only: it MUST NOT support actions, MUST NOT mark notifications "read" in any way that affects automation state, and MUST NOT show reply content (no subject, body, or snippet).
- **FR-182**: Reply content MUST remain in the campaign owner's connected email inbox. The dashboard MUST NOT capture, store, persist, or expose reply content via any UI surface or API response.
- **FR-183**: When a reply is received from a prospect, the agent's outreach scope for that lead MUST automatically end — no further automated emails MUST be queued or sent to that lead in that campaign — and the lead MUST appear in the campaign owner's Reply Notification view.

### Key Entities

- **Tenant**: An organisation. Owns all data scoped to it. Phase 1 has one (Richbond). Has a stable identifier referenced by every tenant-scoped entity.
- **User**: A person with login credentials. Belongs to exactly one Tenant. Has a role (Admin or Member). Is active or deactivated. Has a login-history record. Has at most one Connected Email. Has at most one Backup Notification Email (referenced via the user's `backup_notification_email` field; mandatory before a Connected Email can be set).
- **Connected Email**: A per-User record holding the user's email-sending identity. Carries the email address (visible) and encrypted credentials/tokens (never visible). Has a connection status (connected, disconnected). Required for campaign ownership.
- **Backup Notification Email**: A per-User record holding a personal email address used solely for system notifications (disconnect alerts, takeover prompts, admin fallback alerts). The address itself is encrypted at rest and is never returned to any client in full once saved. Never used to send cold opens. Mandatory before a Connected Email may be set.
- **Lead (Prospect)**: An individual prospect within a Tenant. Attributes: name, email, title, seniority, company, company size, industry, location, current status (which can include "replied"), lead score, sequence stage, last touchpoint. Holds the *fact* of any reply (timestamp, campaign reference) but never reply content.
- **Campaign**: A grouping of outreach activity within a Tenant. Has status (active, paused, past), aggregate metrics (leads count, sends, replies, click rate), exactly one primary owner (a User), an optional `backup_owner_user_id` reference to another User with a connected email (nullable when fewer than two users in the tenant have connected emails; required once at least two do; per FR-136 must differ from the primary owner), an `approval_mode` attribute (per FR-148, default `approval_required`, alternative `automated`, owner-toggleable from the campaign detail view with explicit confirmation), and a per-campaign variant-count configuration.
- **Email**: A sent message tied to a Lead in the context of a Campaign. Has content, send timestamp, sender (the owner's connected email address at send time), and downstream events (opens, clicks, replies — replies stored as fact-of-reply only).
- **Email Draft**: A proposed, AI-generated email awaiting owner action in the approval queue. Carries recipient (lead reference), subject, body, edit history, decision (pending, approved-and-sent, regenerated, rejected), an associated AI Reasoning record, and an associated AI Chat thread. Tied to a Campaign.
- **Email Variant**: A candidate email proposed during variant selection. Carries subject, body, an associated AI Reasoning record, and a status (proposed, selected-for-test, rejected). Rejected variants are discarded, not retained.
- **AI Reasoning**: A read-only record attached to each Email Draft and Email Variant. Holds: hook used, tone choice, recipient assumptions, lead-profile context referenced.
- **AI Chat Exchange**: A chronological conversation between the campaign owner and the AI about a specific Email Draft. Tied to one Email Draft. Phase 1 ships with mock responses.
- **Engagement Event**: An open, click, or fact-of-reply tied to an Email and a Lead. Carries a timestamp. (Reply content is never stored here.)
- **Scout Mission**: A lead-discovery run with progress (leads found, budget consumed, time elapsed) and final outcome. Phase 1: mock only. Subject to at-cap enforcement (current batch finishes; new pulls/missions are blocked).
- **AI Spending Record**: A unit of AI cost tied to a module and a Tenant, contributing to that Tenant's current-period spend. Sourced from AI invocation log entries (FR-092). Drives at-cap enforcement.
- **Settings (Tenant)**: Tenant-scoped configuration: API keys (encrypted), AI spending cap, warning threshold, default variant counts (proposed, selected), per-feature cache TTLs (per FR-068, bounded between 1 minute and 7 days). Note: there is no tenant-wide default approval mode — per FR-146 / Article 6, the per-campaign default is fixed at `approval_required` and is not configurable here.
- **Source Identifier**: A composite reference capturing the network origin of a request — at minimum the IP address and the User-Agent string. Used in login-attempt logs and rate-limiting (FR-002, FR-003). Phase 1 stores both fields in the action log; future phases may extend with additional fingerprint attributes.
- **System Actor Identifier**: A literal string used in place of a user ID for log entries created by system-initiated events that have no human actor. Format: `system:<subsystem>` — examples include `system:campaign_ownership_timeout`, `system:cap_enforcement`, `system:scheduled_retry`, `system:ai_invocation`. Used by Action Log Entry's actor field when no user is responsible.
- **Action Log Entry**: A record of any logged action — timestamp, module (per FR-090), action name, tenant ID, **actor** (either a user ID for user-initiated actions or a System Actor Identifier for system-initiated actions), and target resource ID (where applicable). For failed login attempts the actor reference uses the email-hash from FR-002 in lieu of a user ID, since the user is not yet authenticated. AI-consuming user actions (e.g., `email_regenerate`, `ai_chat_exchange`, `variant_proposal_generated`) carry a `cache_hit` boolean per FR-068; when true, the entry also carries a reference ID to the AI invocation log entry whose response is being reused. Ownership transfers (manual per FR-134, system-triggered per FR-128) are recorded here with action name `campaign_ownership_transfer` rather than in a separate entity.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An Admin user can complete the path Login → Lead Table → Lead Profile and view mock email history and AI spending data in a single session, without written instructions.
- **SC-002**: A Member user can complete the same lead-viewing path, cannot reach User Management or Settings via navigation or direct URL, and cannot change the AI spending cap.
- **SC-003**: 100% of cross-tenant data-access attempts (whether by URL probing or by API call) return the same response shape as a non-existent resource — no information leaks about other tenants.
- **SC-004**: 100% of logged actions appear with tenant ID, module, actor (user ID for user-initiated events, System Actor Identifier for system-initiated events, email-hash for failed-login attempts), and timestamp; 0% contain prospect personal data in plain text.
- **SC-005**: The Lead Table renders 1,000 leads within 2 seconds (initial paint to interactive) on a standard laptop.
- **SC-006**: A non-technical user given valid credentials can complete the Login → Lead Profile path on first attempt without external guidance, in under 90 seconds.
- **SC-007**: All stored API keys and connected-email credentials remain unrecoverable from any UI surface or API response after they have been saved (only the masked form / status is retrievable).
- **SC-008**: Failed-login rate-limiting blocks further attempts from a source after the configured threshold is reached, with the block visible in the action log; 0% of failed-login log entries contain the raw email submitted.
- **SC-009**: When current AI spend reaches 100% of the configured cap, every new AI-consuming surface (Regenerate, AI Chat input, Variant proposal, new Scout-mission action) is visibly disabled with an at-cap reason; previously-approved sends complete and any in-flight AI calls finish naturally.
- **SC-010**: A campaign cannot be launched or transferred to a user who does not have a connected email; the system blocks the assignment and surfaces the reason.
- **SC-011**: 100% of cold-open emails sent by a campaign are sent from the connected email address of that campaign's owner — not from a system or shared address.
- **SC-012**: 0% of dashboard UI surfaces and 0% of dashboard API responses expose reply content (subject, body, or snippet). The dashboard exposes only the *fact* of reply (lead reference, campaign reference, timestamp).
- **SC-013**: When a primary email disconnect occurs, an outbound email alert to the user's backup notification address is dispatched within 60 seconds of the disconnect event regardless of the user's online state. The corresponding in-app warning is shown immediately if the user is currently signed in; otherwise it is queued and shown at the start of the user's next session. Owned campaigns continue running during a 24-hour grace period. After 24 hours without reconnection, all campaigns owned by that user transition to paused state and the designated backup owner (or tenant Admins if no backup owner) are notified.
- **SC-014**: An Admin or Member can navigate from the Campaign Manager to a per-segment Email Performance breakdown for any active campaign in 3 clicks or fewer; the breakdown loads within 3 seconds for a campaign with 10,000 sends.
- **SC-015**: When variant selection is triggered, the AI proposes the configured number of candidates within 10 seconds. When N≥2, the side-by-side review renders all candidates without horizontal scrolling on a standard laptop screen. When N=1, the single-candidate confirm-or-regenerate view renders fully on a standard laptop screen without scrolling. The selection-to-test transition completes in under 2 seconds.
- **SC-016**: A campaign owner can approve, edit, or regenerate any email in their approval queue; each action completes (or fails with a clear reason) within 5 seconds.
- **SC-017**: The AI Reasoning Panel renders alongside every AI-generated email and shows the hook used, tone choice, recipient assumptions, and lead-profile context referenced — all four fields visible without scrolling on a standard laptop screen.
- **SC-018**: An Admin can invite a new Member, change a Member's role, or deactivate a Member; the change takes effect within 10 seconds of saving and the action is recorded in the action log per FR-090.

---

## Assumptions

- Users have stable internet connectivity sufficient for a typical web application.
- Phase 1 deployment hosts a single tenant (Richbond), but the data schema treats `tenant_id` as a mandatory attribute on every tenant-scoped entity from day one.
- Authentication uses email and password for Phase 1; SSO and social login are deferred.
- Email content displayed in lead profiles and approval queue is sanitised before display to prevent injection attacks.
- The AI spending cap operates over a calendar month by default; the warning threshold is set at 80% of the cap (configurable in Settings); at-cap (hard-block) triggers at exactly 100%.
- Member invites are sent via email containing a one-time link the recipient uses to set their own password.
- The Lead Table is paginated (default 50 rows per page).
- API keys, when displayed back to an Admin in Settings, appear in masked form showing only the last 4 characters (e.g., `••••••XYZ9`).
- Failed-login rate-limit defaults: 5 failed attempts from the same source within 15 minutes triggers a temporary 30-minute block; thresholds tunable in Settings. Rate-limiting groups attempts by the email-hash defined in FR-002 plus the source identifier — never by the raw email.
- Lead status values, vertical taxonomy, hook categories, and personalisation-depth dimensions are pre-seeded constants in Phase 1; later modules (Outreach, Learning Engine) may add to them. The lead status enum includes a `replied` value used to drive the Reply Notification view and to halt automation per FR-183.
- Campaign status values include `active`, `paused`, and `past`. "Active" in the persistent stats bar means status is `active` (a property of the campaign), not derived from recent send activity. `paused` is reachable via owner email-disconnect (post-grace), owner deactivation, and manual admin action; per FR-067 it is *not* the state used for at-cap behavior — at-cap blocks new AI work but leaves campaign status alone.
- Variant-count defaults: 5 proposed, 2 selected for live test; configurable per campaign in Settings or at launch.
- Connected email integration uses industry-standard authentication mechanisms for connecting external email services in production; Phase 1 ships with a mock-connect flow that records "connected" status without performing real authentication. The data structure and encryption-at-rest expectation match the eventual real flow.
- The backup notification email is a personal address (e.g., a personal Gmail) the user designates at primary-email connection time, distinct from the primary sending address. Encryption-at-rest and masking on display follow the same handling pattern as API keys.
- Disconnect detection is event-driven: triggered by explicit user disconnect action, by external-service callback indicating revocation, or by the system classifying send-time errors as terminal. The 24-hour grace clock starts at the recorded disconnect timestamp.
- Per-send error classification ("temporarily unreachable" vs. "actively rejecting") distinguishes transient delivery failures (the destination is unreachable but the address itself is valid) from permanent delivery failures (the destination actively rejects mail or authentication has been revoked). Specific class boundaries are tunable in Settings. Transient failures retry; permanent failures pause the originating campaign and notify the owner.
- Timeout-triggered ownership transfer is opt-in for the backup owner: notifications invite them to take ownership but never force it. The campaign sits paused until they accept, the original owner reconnects, or an Admin reassigns.
- AI Chat ships in Phase 1 with mock responses; the chat data structure mirrors the planned real structure so that swapping in a real AI provider later is plumbing, not redesign.
- Scout missions, AI spending records, engagement events, sent-email content, email drafts, email variants, AI reasoning records, and AI chat exchanges are populated entirely from mock data in Phase 1; replacing them with real sources later is a wiring change, not a redesign.
- Action logs are retained for at least 90 days.
- Sessions expire after 8 hours of inactivity; the user is redirected to login on the next protected request.
- Phase 1 has no in-dashboard data export UI per FR-095; client-data export is performed via direct query against the data layer when needed. The data structure is designed to be exportable in CSV and JSON without any restructuring effort.
- Default cache TTLs (per FR-068): AI Chat exchanges 1 hour; Email Drafts 24 hours; Email Variants 24 hours; AI Reasoning panels 24 hours. Per-feature overrides allowed in Settings (Tenant), bounded to [1 minute, 7 days].
- Mobile layouts, multi-language UI, single sign-on / social login, the Mission Launcher form (page exists; form is out of scope), the Email Sequence Editor, the manual "take over" / handoff control (which has been removed from product scope), capturing or displaying reply content in the dashboard, and an in-dashboard data-export UI are all explicitly out of scope for Phase 1.

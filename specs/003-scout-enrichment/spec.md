# Feature Specification: Scout — Lead Enrichment & Qualification

**Feature Branch**: `003-scout-enrichment`
**Created**: 2026-06-03
**Status**: Draft
**Input**: User description: "We need to complete the finding of the person, decide if they are a quality target, and then uncover their email."

## Summary

Scout today finds *companies* but leaves the contact person and email blank, so
the leads it produces cannot be emailed by the Outreach engine. This feature
builds the second half of Scout's job: **find the person, decide whether they
are a quality target, and uncover their verified email** — turning raw
company-level lists into a quality-ranked, ready-to-email list.

The quality bar is authored per campaign (the ideal-customer profile) and is the
single source of truth that the qualification logic measures against.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Describe the ideal target when creating a campaign (Priority: P1)

When setting up a campaign, the user describes what a good target looks like:
the position/title to reach, the niche, the size that counts as "big enough",
the in-scope locations, and a short plain-language description of the ideal
customer. This becomes the quality bar everything downstream measures against.

**Why this priority**: Every later step reads from this profile. Without it,
nothing downstream is trustworthy — garbage in, garbage out.

**Independent Test**: Create a campaign with a target profile; confirm it is
stored, tenant-scoped, and shown back accurately.

**Acceptance Scenarios**:

1. **Given** a new campaign, **When** the user provides target role, niche, size
   threshold, regions, and a description, **Then** the profile is saved and tied
   to that campaign's tenant.
2. **Given** a profile missing a required field, **When** the user saves, **Then**
   the system flags what is missing rather than silently accepting a
   half-defined target.

---

### User Story 2 - Find the contact person and company website (Priority: P1)

For each shell lead, Scout finds the company's official website and a relevant
named contact (matching the role in the profile), or clearly records "not found".

**Why this priority**: Without a person and a domain there is nothing to qualify
or email.

**Independent Test**: Run on a batch of shell leads; each ends up with a domain +
candidate person, or an explicit "not found" reason.

**Acceptance Scenarios**:

1. **Given** a company with no website on file, **When** discovery runs, **Then**
   Scout records the official domain, or records why it could not be found.
2. **Given** a company website, **When** discovery runs, **Then** Scout identifies
   a contact matching the target role where findable, with name + title.

---

### User Story 3 - Qualify leads against the profile: rules first, then AI (Priority: P1)

Scout scores each lead. A free, deterministic rules check drops the obvious
misses (wrong region, too small, wrong niche, no relevant contact). The
survivors receive an AI judgment that scores fit 0-100 with a stored, fact-based
reason. Output is a ranked list, best first, each with an explanation.

**Why this priority**: This is the "quality target" decision — the core of the
feature.

**Independent Test**: Feed in enriched leads; confirm clear-cut misses are
dropped by rules with no AI cost, survivors get an AI score + reason, and the
list is returned ranked.

**Acceptance Scenarios**:

1. **Given** a lead outside the target region, **When** qualification runs,
   **Then** it is rejected by the rules layer with no AI cost incurred.
2. **Given** a lead that passes the rules, **When** the AI judges it, **Then** a
   score, a confidence, and a short fact-based reason are stored next to the lead.
3. **Given** a batch of qualified leads, **When** the user views them, **Then**
   they are ordered best-to-worst with reasons visible.

---

### User Story 4 - Uncover verified emails for keepers only (Priority: P2)

Only leads that clear qualification get an email lookup, so paid lookups are
never spent on leads we would not contact.

**Why this priority**: Depends on US3. This is where money is spent, so it runs
last and only on qualified leads.

**Independent Test**: Run on a qualified set; confirm emails are found + verified
for keepers and that no lookup fires for rejected leads.

**Acceptance Scenarios**:

1. **Given** a qualified lead with a known person + domain, **When** email
   discovery runs, **Then** a verified email is stored, or a clear
   "unverified / not found".
2. **Given** a rejected lead, **When** the pipeline runs, **Then** no email
   lookup is performed for it.

---

### User Story 5 - Optional AI double-check ("reflection") (Priority: P3)

A switch that makes the AI re-review its own borderline verdicts to catch
careless calls — off by default, enabled only if the AI is seen making sloppy
judgments.

**Why this priority**: A reliability dial, not core. It roughly doubles AI cost,
so it is evidence-gated.

**Independent Test**: With the switch on, confirm a second AI review runs on
borderline leads and can revise the first score; with it off, only one pass runs.

**Acceptance Scenarios**:

1. **Given** reflection is off, **When** qualification runs, **Then** exactly one
   AI judgment is made per surviving lead.
2. **Given** reflection is on, **When** a borderline lead is judged, **Then** a
   second review runs and may revise the score, with both recorded.

---

### User Story 6 - Choose which AI engine each tool uses (Priority: P2)

From one central place, the user can assign which LLM engine powers each tool
(e.g. Scout's judge on DeepSeek or GPT, Outreach on Opus), and can add a new
engine later by supplying its access key and pointing a tool at it — with no code
changes. Anything left unassigned uses a default engine.

**Why this priority**: This is the user's stated infrastructure goal — start on
one engine today, add other LLM providers freely later. Scout is the first
consumer, but the capability is shared across modules.

**Independent Test**: Assign Scout's judge to a non-default engine in the central
config; confirm the judge calls that engine. Remove the assignment; confirm it
falls back to the default engine.

**Acceptance Scenarios**:

1. **Given** no engine is assigned to a tool, **When** that tool makes an AI call,
   **Then** it uses the default engine (the Claude subscription) with no error.
2. **Given** a new engine is added to the central config with its key, **When** a
   tool is pointed at it, **Then** that tool's AI calls use the new engine without
   any code change.

---

### Edge Cases

- Company has no findable website → recorded as "not found", lead parked,
  pipeline continues (no crash).
- AI service is down or slow → lead stays "pending qualification"; other leads
  keep flowing (failures contained).
- Email lookup returns a low-confidence guess → stored as unverified, never
  silently promoted to verified.
- Re-running the pipeline → already-processed leads are not re-processed or
  re-charged (idempotent, like the existing ingest).
- A lead passes rules but the AI cannot reach a confident verdict → flagged for
  human review rather than auto-accepted or auto-rejected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each campaign MUST carry a target profile with: target role/title,
  niche, size threshold, in-scope regions, and a plain-language ideal-customer
  description.
- **FR-002**: Scout MUST discover a company's official domain for a shell lead,
  or record a reason it could not.
- **FR-003**: Scout MUST attempt to identify a contact matching the target role,
  recording name + title, or "not found".
- **FR-004**: Qualification MUST run a deterministic rules layer first that
  rejects leads failing hard criteria, with no AI cost for those.
- **FR-005**: Leads passing the rules MUST receive an AI fit score (0-100), a
  confidence, and a stored fact-based reason.
- **FR-006**: Qualified leads MUST be presented ranked best-to-worst with their
  reasons.
- **FR-007**: Email discovery MUST run only on qualified leads, and MUST
  distinguish verified from unverified results.
- **FR-008**: Every step MUST be idempotent — re-running never duplicates work
  or re-charges for already-processed leads.
- **FR-009**: All data and actions MUST be scoped to the campaign's tenant; no
  query may access another tenant's data.
- **FR-010**: Prospect data MUST never be written to logs in plain text; API
  keys MUST be read from the environment only, never hardcoded.
- **FR-011**: Each step MUST fail independently and emit a log entry capturing
  what happened, which step, which tenant, and when.
- **FR-012**: A reflection (AI self-check) pass MUST be available as an
  off-by-default option.
- **FR-013**: Every AI call MUST run on an engine selected per tool from a
  central engine registry; when a tool has no engine assigned, the default
  engine (the Claude subscription) MUST be used.
- **FR-014**: Adding a new LLM engine MUST require only configuration (supplying
  its access key and assigning it to a tool), never changes to a module's code.
- **FR-015**: Each engine's credentials MUST be read from the environment, never
  stored in the registry file or in source.

### Key Entities

- **Campaign Target Profile (ICP)**: the quality bar — target role, niche, size
  threshold, in-scope regions, and ideal-customer description. Belongs to one
  campaign / tenant.
- **Lead (extended)**: the existing shell lead, now also carrying the discovered
  company domain, the contact person (name + title), the qualification verdict
  (rules outcome + AI score + confidence + reason), and the email with a verified
  flag.
- **Engine Registry**: the central "engine room" — the list of available LLM
  engines (each with env-referenced access) and the mapping of which tool uses
  which engine, plus a default engine. Shared across modules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A shell lead can travel the full path — person found → qualified →
  (if kept) email found — with no manual coding per lead.
- **SC-002**: Clear-cut misses are rejected by the free rules layer, so the AI
  only judges genuine borderline cases (measured: % of leads rejected pre-AI).
- **SC-003**: No paid email lookup is ever spent on a rejected lead (measured:
  rejected-lead lookups = 0).
- **SC-004**: Every qualification decision is explainable — a stored reason
  exists for every score.
- **SC-005**: Re-running the pipeline produces no duplicate leads and no repeat
  charges.

## Assumptions

- The size yardstick (e.g. bed/room count) and the exact target role are
  per-campaign inputs the user sets in the profile — not hardcoded. This feature
  builds the machinery; the values are authored per campaign.
- Vendor choice is deferred to the plan: which web-search service finds domains
  and which service finds emails will be decided by running the existing
  evaluation harness. This spec stays vendor-neutral; the design will keep
  vendors swappable. This step needs API keys, at plan/build time.
- The shared lead database and its schema (owned by `ww-core`) will be extended,
  not replaced.
- Sending emails is out of scope — that is the Outreach module's job. This
  feature stops at a "ready-to-email" list.
- Adding more data sources (IPEDS, TABS, SHB, state licensure, etc.) is a
  separate later feature; this spec covers enrichment + qualification of leads
  from any existing source.
- A shared LLM engine layer (the engine registry + per-provider adapters) is
  introduced by this feature as reusable infrastructure, with Scout as its first
  consumer; other modules (e.g. Outreach) migrate onto it later. It runs
  independently of the separate Zeno model-router so that a router outage cannot
  take Winston Wolf offline.

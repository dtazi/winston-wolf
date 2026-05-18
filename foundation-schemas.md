# Foundation schemas — review draft

This document sketches the three foundational data structures that everything else in Winston Wolf attaches to:

1. **The lead database** — SQLite tables that hold campaigns, leads, sends, and events.
2. **The brief schema** — a per-campaign YAML artifact (audience side).
3. **The pitch schema** — a per-customer YAML artifact (offer side).

The drafting layer (built last) will read a campaign's brief plus the customer's pitch plus a lead's data, and produce an email. Everything in between — Scout, source-channel ingesters, the tracking server, reply detection — reads from or writes to the lead database.

This document is a written spec, not code. Approve, edit, or push back on anything; once it's settled, the SQLite layer and YAML examples become a half-day's build.

---

## How the three pieces fit together

```
Customer (Richbond)
   |
   |-- Pitch (one per customer)
   |       Captures: what we sell, why, proof, CTA
   |
   |-- Campaign 1 (US Institutional Pilot)
   |       |
   |       |-- Brief (one per campaign)
   |       |       Captures: niches, geography, role taxonomy, source channels
   |       |
   |       |-- Leads (many per campaign)
   |       |       Captures: company + person + email + status
   |       |
   |       |-- Sends (one or more per lead)
   |       |       Captures: subject + body + Microsoft message id + tracking tokens
   |       |
   |       \-- Events (many per lead, append-only)
   |               Captures: opens, clicks, replies, bounces, status changes
   |
   \-- Campaign 2 (Hospitality MENA — future)
           ... same shape ...
```

A campaign is bound to one customer and inherits that customer's pitch. The brief is per-campaign and per-niche-bundle. Leads belong to a single campaign but the per-lead source attribution is preserved across the platform so we can roll up by source channel across campaigns and (later) customers.

---

## 1. Lead database (SQLite)

One file: `winston-wolf/data/leads.db`. Six tables.

### Table: `customers`

One row per client. Richbond is one customer.

| column | type | notes |
|---|---|---|
| id | TEXT PRIMARY KEY | slug, e.g. `richbond` |
| name | TEXT | display name |
| pitch_path | TEXT | relative path to the customer's pitch YAML |
| created_at | TIMESTAMP | |

### Table: `campaigns`

One row per campaign. Many per customer over time.

| column | type | notes |
|---|---|---|
| id | TEXT PRIMARY KEY | slug, e.g. `richbond-us-institutional-pilot-2026q2` |
| customer_id | TEXT FK → customers.id | |
| name | TEXT | display name |
| brief_path | TEXT | relative path to this campaign's brief YAML |
| status | TEXT | `draft`, `active`, `closed` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### Table: `source_channels`

A reference table for the directories, associations, publications, conferences, and signal sources we draw leads from. Lets us roll up cross-campaign performance per source.

| column | type | notes |
|---|---|---|
| id | TEXT PRIMARY KEY | slug, e.g. `cms_nursing_home_compare`, `asha_directory`, `ipeds` |
| name | TEXT | display name |
| type | TEXT | `directory`, `public_record`, `publication`, `conference`, `signal` |
| access_tier | TEXT | `free`, `paid_approx`, `paid` |
| description | TEXT | one-line summary of what this source provides |
| url | TEXT | source homepage, if applicable |

Pre-seeded with the map we built earlier (CMS, IPEDS, state licensure, ACUHO-I, ASHA, etc.).

### Table: `leads`

The core entity. One row per prospect we identify.

| column | type | notes |
|---|---|---|
| id | TEXT PRIMARY KEY | UUID |
| customer_id | TEXT FK → customers.id | denormalized for cross-campaign queries |
| campaign_id | TEXT FK → campaigns.id | |
| niche_id | TEXT | matches a sub-niche id in the campaign's brief (e.g., `edu_university_dorms`) |
| source_channel_id | TEXT FK → source_channels.id | how this lead was found |
| source_record_id | TEXT | source's own identifier (e.g., CMS provider number, IPEDS UNITID) |
| access_difficulty | TEXT | `free`, `scraped`, `paid`, `manual` |
| company_name | TEXT | |
| company_domain | TEXT | |
| company_country | TEXT | ISO-2 |
| company_region | TEXT | state/province |
| company_size_band | TEXT | `small`, `mid`, `large`, `unknown` |
| person_first_name | TEXT | nullable until enriched |
| person_last_name | TEXT | nullable until enriched |
| person_title | TEXT | |
| person_email | TEXT | nullable until enriched |
| email_confidence | INTEGER | 0–100, from Hunter or similar |
| email_method | TEXT | `hunter_email_finder`, `hunter_domain_search_guess`, `directory_listed`, `manual` |
| person_phone | TEXT | |
| person_linkedin | TEXT | |
| status | TEXT | `cold`, `queued`, `sent`, `opened`, `clicked`, `replied`, `bounced`, `closed` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| notes | TEXT | free-text scratchpad |

Indexes: `(campaign_id, status)`, `(customer_id)`, `(source_channel_id)`, `(niche_id)`, `(company_domain)`.

### Table: `sends`

One row per individual email send. A lead can have multiple sends over time (initial + follow-ups) — v1 only does single-touch but the schema doesn't constrain that.

| column | type | notes |
|---|---|---|
| id | TEXT PRIMARY KEY | UUID |
| lead_id | TEXT FK → leads.id | |
| subject | TEXT | what was sent |
| body_text | TEXT | full body — small enough to store inline at our scale |
| sent_at | TIMESTAMP | |
| microsoft_message_id | TEXT | Graph's returned message id, for traceability and reply matching |
| pixel_token | TEXT | unique token embedded in the open-tracking pixel URL |
| created_at | TIMESTAMP | |

Indexes: `(lead_id, sent_at)`, `(pixel_token)`, `(microsoft_message_id)`.

### Table: `tracked_links`

One row per trackable link placed in an outgoing email. The click redirector
looks up the token, logs the click, and forwards to `original_url`. (Added
2026-05-14 when the tracking server was built — the click redirector needs a
token→URL map the original foundation draft lacked.)

| column | type | notes |
|---|---|---|
| id | TEXT PRIMARY KEY | the click token, embedded in the email link |
| send_id | TEXT FK → sends.id | which send this link belongs to |
| lead_id | TEXT FK → leads.id | denormalized for fast event writes |
| original_url | TEXT | the real destination to 302-redirect to |
| created_at | TIMESTAMP | |

Index: `(send_id)`.

### Table: `events`

Append-only log of everything that happens to a lead. This is where the compounding-intelligence layer reads from.

| column | type | notes |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| lead_id | TEXT FK → leads.id | |
| send_id | TEXT FK → sends.id, nullable | nullable for events not tied to a send (e.g., `created`, `enriched`) |
| event_type | TEXT | see list below |
| timestamp | TIMESTAMP | when the event actually happened |
| payload | TEXT | JSON, event-specific (user-agent for opens, URL for clicks, reply preview for replies, etc.) |
| recorded_at | TIMESTAMP | when we wrote the row — may differ from `timestamp` for delayed sources |

Event types:
- `created` — lead inserted into DB
- `enriched` — email or other contact info found
- `queued` — moved to outreach queue
- `sent` — email actually sent (links to `sends.id`)
- `opened` — pixel hit
- `clicked` — link in email clicked (payload includes which link)
- `replied` — reply detected in inbox (payload includes preview metadata)
- `bounced` — bounce notification detected
- `manual_note` — free-text note added by the operator
- `status_changed` — explicit status transition (payload: old → new)

Indexes: `(lead_id, timestamp)`, `(event_type, timestamp)`, `(send_id)`.

---

## 2. Brief schema (YAML)

One file per campaign, e.g. `winston-wolf/data/briefs/richbond-us-institutional-pilot-2026q2.yaml`.

The brief is the audience-side artifact: who we target, where, with which sources, under what trigger conditions.

```yaml
id: richbond-us-institutional-pilot-2026q2
customer: richbond
name: Richbond US Institutional Pilot
created: 2026-05-14
updated: 2026-05-14
status: draft

spine_pitch: |
  Bulk durability + Morocco-made supply diversification, for institutional
  high-turnover bedding buyers.

geography:
  calibration_tier:
    description: Lower-stakes states where we test the message
    regions:
      - { country: US, state: MT }
      - { country: US, state: WY }
      - { country: US, state: SD }
      - { country: US, state: ND }
      - { country: US, state: NE }
      - { country: US, state: IA }
      - { country: US, state: KS }

  scaling_tier:
    description: High-value markets, only after calibration validates the message
    regions:
      - { country: US, state: NY }
      - { country: US, state: FL }
      - { country: US, state: MA }
      - { country: US, state: IL }
      - { country: US, state: TX }
      - { country: US, state: CA }

sub_niches:
  - id: edu_university_dorms
    label: University dormitories
    industry: Education
    included: true
    rationale: Direct decision-makers reachable; large universe via IPEDS + ACUHO-I

  - id: edu_boarding_schools
    label: Boarding schools (K-12)
    industry: Education
    included: true
    rationale: ~300 schools globally via TABS, end-to-end manageable

  - id: edu_summer_camps
    label: Summer camps
    industry: Education
    included: false
    rationale: Seasonal/light buyers; defer

  - id: mf_student_housing_operators
    label: Student housing operators
    industry: Multi-family
    included: true
    rationale: ~25 operators control most beds (SHB Top 25)

  - id: mf_coliving_operators
    label: Co-living operators
    industry: Multi-family
    included: true
    rationale: Co-Liv directory covers the small universe

  - id: mf_corporate_housing
    label: Corporate housing
    industry: Multi-family
    included: false
    rationale: Different pain profile (executives, brand-driven); would dilute pitch

  - id: mf_senior_independent_living
    label: Senior independent living
    industry: Multi-family
    included: true
    rationale: Same archetype as AL; included per user decision

  - id: hc_assisted_living
    label: Assisted living
    industry: Healthcare
    included: true
    rationale: Full state licensure data is free and rich

  - id: hc_memory_care
    label: Memory care
    industry: Healthcare
    included: true
    rationale: Mostly operated by AL chains; overlap with Argentum

  - id: hc_skilled_nursing
    label: Skilled nursing facilities
    industry: Healthcare
    included: true
    rationale: CMS Nursing Home Compare = highest-leverage public source on our entire map

  - id: hc_hospitals
    label: Hospitals
    industry: Healthcare
    included: false
    rationale: GPO-bound, cold email is the wrong tool

  - id: hc_hospice
    label: Hospice
    industry: Healthcare
    included: false
    rationale: Low volume per facility; defer

niche_details:
  edu_university_dorms:
    size_estimate: "~900 institutions (IPEDS)"
    procurement_model: internal
    target_titles:
      - Housing Director
      - Director of Residence Life
      - Assistant Director of Housing
      - Facilities Director
    company_size: any
    buying_trigger: Academic calendar (summer turnover); replacement cycle ~7-10 yrs
    value_angle: Durability + cost-per-bed-night + ADA / fire code compliance
    findability: high

  edu_boarding_schools:
    size_estimate: "~300 globally (TABS)"
    procurement_model: internal
    target_titles:
      - Head of School
      - Director of Boarding
      - Director of Facilities
    company_size: small-to-mid
    buying_trigger: Multi-year refresh; new dorm construction
    value_angle: Durability + safety codes + long-life cost framing
    findability: high

  # (one block per included sub-niche; same shape)

source_channels:
  edu_university_dorms:
    - { id: ipeds,                type: public_record, access: free,         priority: 1 }
    - { id: acuhoi_directory,     type: directory,     access: paid_approx,  priority: 2 }
    - { id: linkedin_job_postings, type: signal,       access: free,         priority: 3 }

  edu_boarding_schools:
    - { id: tabs_directory,       type: directory,     access: free,         priority: 1 }
    - { id: nais_directory,       type: directory,     access: paid_approx,  priority: 2 }

  hc_skilled_nursing:
    - { id: cms_nursing_home_compare, type: public_record, access: free, priority: 1 }
    - { id: ahca_directory,           type: directory,     access: paid_approx, priority: 2 }

  # (one block per included sub-niche)

retrospective:
  filled: false
  missed_niches: []
  best_source_channels: []
  best_titles: []
  best_pitch_angles: []
  lessons: ""
```

The retrospective block is empty at draft time; gets filled after the campaign by the Brief Builder step 6.

---

## 3. Pitch schema (YAML)

One file per customer, e.g. `winston-wolf/data/pitches/richbond.yaml`. Reused across every campaign for that customer.

```yaml
customer: richbond
created: 2026-05-14
updated: 2026-05-14
version: 1

one_liner: |
  Industrial-scale mattress manufacturer based in Morocco, serving institutional
  bulk buyers in hospitality, healthcare, education, and government.

pains_solved:
  - id: bulk_durability
    label: Bedding durability under high-turnover use
    description: |
      Institutions cycle bedding 3-5x faster than residential. Standard mattresses
      fail under that load. Richbond builds for it.

  - id: tco_framing
    label: Total cost of ownership / cost-per-bed-night
    description: |
      Procurement teams care about lifetime cost, not unit price. Richbond mattresses
      last longer per dirham than commodity imports.

  - id: regulatory_compliance
    label: Fire-safety and regulatory compliance
    description: |
      Healthcare and dorm bedding has strict flammability and material requirements.
      Richbond's bedding passes them.

  - id: supply_diversification
    label: Supply-chain risk reduction (China +1)
    description: |
      Buyers exposed to China tariffs, lead-time variance, and political risk are
      actively seeking alternative manufacturing geographies. Richbond is the
      Morocco answer to that.

differentiation:
  - id: china_plus_one
    label: Morocco manufacturing — direct China alternative
    proof: |
      EU FTA in place; geographic proximity to EU and US East Coast ports; no
      Section 301 tariff exposure; English / French / Arabic-speaking sales team.

  - id: vertical_integration
    label: In-house foam, fabric, and finishing
    proof: |
      Single-source accountability across the bill of materials; faster customization
      cycles than buyers used to from Asian factories.

  - id: institutional_track_record
    label: Long history with institutional buyers in MENA
    proof: |
      [TO FILL: specific reference accounts in hospitality, healthcare, military]

proof_points:
  - type: certification
    label: "[TO CONFIRM with Richbond] Fire-safety: UL, CertiPUR-US, BS 7177"
  - type: customer_reference
    label: "[TO FILL] Major MENA hospitality group reference"
  - type: factory_capacity
    label: "[TO FILL] Production capacity in unit-equivalents per month"
  - type: certification
    label: "[TO CONFIRM] ISO 9001 / ISO 14001"

cta:
  primary:
    label: Sample request + 20-minute discovery call
    rationale: Lowest-friction first step; gives Richbond presence in their RFQ shortlist next time
  secondary:
    label: Spec sheet PDF download
    rationale: For lurkers not yet ready to talk

price_framing: value
# value = quality-and-durability-justified, mid-to-premium pricing
# premium = top-tier-only positioning
# parity = compete on price with commodity

tone: |
  Professional, direct, industrialist-to-industrialist. Not salesy or aspirational.
  Concrete numbers preferred over adjectives. French/English bilingual register fine.

common_objections:
  - objection: "We don't know Moroccan manufacturers"
    handling: |
      Offer factory visit (Richbond covers travel for serious prospects), share
      institutional references, link to certifications.

  - objection: "We have existing supplier relationships"
    handling: |
      Position as supply diversification (China +1), not replacement. "Add us as
      a second source — see if we earn the volume over time."

  - objection: "We're too small for international supply"
    handling: |
      Containerized orders with MOQ flexibility; consolidate with other regional
      institutions; spec sheets allow direct comparison without commitment.

  - objection: "Shipping cost makes Morocco non-viable"
    handling: |
      Compare landed cost, not FOB. Tariff exposure on Chinese imports often eats
      the shipping advantage. Specific routes: Casablanca → US East Coast, ~2 weeks.

# Placeholders Richbond should fill in before going live:
to_confirm_with_client:
  - Specific certifications held (current/expired)
  - 2-3 reference accounts permitted for cold-email mention
  - Production capacity (units/month) for honesty in sales conversations
  - Lead times by container size
  - Sample policy (free / cost / who pays shipping)
```

The `to_confirm_with_client` block is the spec sheet Richbond should fill in before email #1.

---

## How everything connects

When the drafting layer (built last) composes an email for lead `L` in campaign `C`:

1. Load `C.brief` — get the campaign's spine pitch, the niche `L.niche_id`, the niche's pain points, the value angle, the geography context.
2. Load `C.customer.pitch` — get the offer side: pains solved, differentiation, proof points, CTA, tone, objections.
3. Load `L` — get the person's name, title, company, source channel.
4. Compose: subject + body, with pixel and click-tracked links injected.
5. On send: create a row in `sends`, log a `sent` event.
6. Tracking server writes `opened`/`clicked` events as they arrive.
7. Reply detector writes `replied`/`bounced` events as it polls.

Every event is queryable for the retrospective + per-source rollups + cross-campaign learning.

---

## What's deliberately not in v1

- **Multi-touch sequences** — the schema supports it (multiple sends per lead) but the queue logic isn't built yet.
- **Templates with variables** — drafter composes fresh each time; no template engine.
- **A/B variant tracking** — `sends` could grow a `variant_id` column when needed.
- **Multi-tenant** — schema works for many customers but the SQLite-on-disk model assumes one operator. When WW has a real second customer, we migrate to Postgres.
- **Per-niche rollup tables** — computed on demand via SQL for v1. Materialized rollups added if queries get slow.

---

## Review checklist

Things worth disagreeing with or editing:

- Field names that feel wrong
- Missing pain points / differentiation / objections specific to Richbond
- Sub-niche list — anything to add or drop
- Source-channel slugs (the `id` values in source_channels) — want them more descriptive?
- Lead status state machine — is the right set of statuses there?
- Anything else this is missing

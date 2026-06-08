# Feature Specification: Proof-of-Life Experiment

**Feature branch:** `004-proof-of-life-experiment`
**Created:** 2026-06-08
**Status:** Draft — spec gate (awaiting operator review)
**Supersedes:** the `004-instantly-skeleton` walking-skeleton scope

---

## Overview

This feature is a **30-day, time-boxed experiment**, not a slice of the product. It
tests whether the thesis Winston Wolf is built on is true for Richbond *before* the
product is built at scale.

**The hypothesis (falsifiable):** Richbond can generate a meaningful number of
qualified sales conversations per month from cold outreach when each email is the
product of deep prospect research, a deliberate strategy choice, and human approval —
sent in low daily volumes from a real Richbond mailbox.

**Verdict rule (accepted before the first send):**
- **Reply rate ≥ 5%** over 30 days → thesis **validated**.
- **Reply rate < 2%** → thesis **killed**; cold outreach is the wrong channel for
  Richbond's market and the product strategy is redirected.
- **2%–5%** → iterate; adjust and run a second experiment.

Reply rate is measured as **unique prospects who replied ÷ unique prospects
contacted** (a reply is a "conversation", which is per-prospect, not per-send).

**Secondary hypothesis (the learning loop):** by day 30 the drafts are measurably
better than on day one, because each day's feedback informed the next day's strategy
choices. If day-30 drafts are no better than day-one drafts, the learning concept
needs rethinking even if the reply rate is good.

The experiment is informative even if it fails: a sub-2% reply rate on disciplined,
deeply-researched, human-approved emails is itself strong evidence that redirects the
product strategy. The conclusions log from a failed run is still valuable.

---

## Locked decisions (operator, 2026-06-08)

These were decided before specification and are not Claude Code's to revisit:

1. **Sending identity — real Richbond mailbox `richbond.ma`, via the existing M365
   Graph path (`ww-outreach`).** This is a primary-domain account. Per the
   Constitution Article 16 **validation-pilot exception** (amended 2026-06-08), the
   operator accepts the reputation risk to the primary domain in writing as a
   deliberate experiment cost. No Instantly, no secondary domains, no warm-up network.
2. **Open + click tracking — KEPT.** Engagement is measured via the existing
   `ww-tracking` open-pixel + click-redirector (un-retired for this experiment). Reply
   rate remains the **verdict** metric; opens/clicks are secondary signal.
3. **Reply detection — MANUAL.** The operator flags a prospect as "replied"; the
   system then suppresses that prospect. No automated inbox poller; the system never
   reads reply content (Article 15).
4. **Sample size — accepted as directional.** 30–50 prospects is a small sample; the
   experiment yields a direction, not a precise rate. This is accepted, not a defect.
5. **Follow-up / multi-touch — INCLUDED, engagement-tiered, one follow-up at +7 days.**
   Seven days after the first send, any prospect not flagged replied (and not suppressed)
   becomes eligible for **one** follow-up. The follow-up is **not** hard-gated on raw
   opens — open tracking is noisy (Apple Mail Privacy Protection and Gmail's image proxy
   pre-fetch the pixel on delivery → phantom opens; images-off readers → false non-opens).
   Instead the strongest observed engagement signal **shapes** the follow-up
   (clicked → stronger/more direct; opened → light nudge; silent → different-angle retry),
   while everyone-not-replied stays eligible. "7-day open-gated follow-up" also exists as
   an explicit **strategy-library entry whose effectiveness the experiment measures**.
   Every follow-up passes the morning approval gate (the human backstop against
   manual-flag lag). Pilot is capped at **2 touches** (initial + one follow-up); deeper
   sequences are a later refinement using the same machinery. Expected total volume:
   ~55–95 sends over the month (initial 30–50 + follow-ups to most non-repliers), well
   inside the daily ceilings.

---

## What survives from the prior architecture (inheritance)

This experiment **builds on** committed assets; it does not restart.

| Need | Reused asset | Change |
|---|---|---|
| Approval state machine (approve / edit / reject) | `ww-engine` `modes.py` | Add a per-draft **comment** field |
| AI Writer | `ww-engine` drafting seam (`drafting/base.py`) | Ground in KB + strategy library; carry the strategy/reasoning note in `message_recipe` |
| Send | `ww-outreach` M365 Graph send/auth (**un-retired**) + `ww-engine` `sender.py` | Reuse as-is; verify the OAuth connection is live |
| Follow-up sequencing | `ww-engine` 002 sequencing scaffolding (`touch_number`, US2) | Reuse for the +7d follow-up; engagement-tiered angle |
| LLM for research, drafting, conclusions | `ww-llm` registry + provider engines | Reuse wholesale |
| Open/click tracking | `ww-tracking` (**un-retired**) | Reuse as-is |
| Tenant + campaign spine, loaders | `ww-core` | Reuse |
| Strategy library seed | 002 `email_playbook.md`, `email_decisions.md`, `email_foundation.md` + drafter prompt rules | Externalize into editable library docs |
| Richbond KB seed | `data/pitches/richbond.yaml` (`pitch.yaml`) | Seed v0 of the living KB document |

**Not reused:** `detector.py` reply/bounce body-scanning (decision #3 makes reply
detection manual; porting it would read reply content, violating Article 15).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The operator reviews a nightly batch of researched, reasoned drafts (Priority: P1)

Overnight, the system researches each prospect in the next batch, chooses one or more
strategies from the library based on what the research surfaced, drafts the email, and
writes a strategy-and-reasoning note. In the morning the operator opens one interface
and works through each draft — reading the email, the reasoning note, and the research
summary — then records a verdict (approve / edit / reject) and an optional comment.
The morning review takes ~30–60 minutes for 5–15 drafts.

**Acceptance:** every draft presented carries (a) the email, (b) a strategy/reasoning
note naming the strategies chosen, why for this prospect, and how applied, and (c) a
research summary. A verdict and comment can be recorded for each. No draft can be sent
without an explicit approve (or edit-then-approve).

### User Story 2 — An approved draft is sent from the real Richbond mailbox at the prospect's local mid-day (Priority: P1)

An approved (or edited-and-approved) draft is scheduled to leave `richbond.ma` via M365
Graph so it lands in the recipient's inbox during their local **10am–2pm** window, on
**Tuesday–Thursday** only. Daily volume ramps from 3–5/day in week one to a ceiling of
~10–15/day by week four.

**Acceptance:** sends occur only Tue–Thu within the recipient's local mid-day window;
the daily count never exceeds the current week's ceiling; the system never sends a draft
lacking a recorded approval.

### User Story 3 — A reply stops outreach to that prospect, without the system reading it (Priority: P1)

When a prospect replies, the operator flags that prospect as "replied" (and records a
reply category for the tracking sheet). The system records that a reply occurred, halts
all further outreach to that prospect, and logs the event for the learning loop. The
system never reads or drafts a response to the reply.

**Acceptance:** once a prospect is flagged replied, no further draft or send targets
them; the reply event is logged; no reply content is ever ingested by the system.

### User Story 4 — The system learns across the 30 days (Priority: P2)

After each day's feedback is captured, the system reads the new comments and updates a
conclusions log when patterns emerge (which strategies get approved as-is vs. edited
heavily, which personalization the operator consistently improves, which prospect types
produce the strongest first drafts). The next nightly batch incorporates the latest
comments, the conclusions log, and any edits to the strategy library.

**Acceptance:** the conclusions log accumulates dated observations tied to feedback;
each nightly batch demonstrably consumes the current comments + conclusions + library
state as drafting input.

### User Story 5 — A follow-up goes out a week later, shaped by engagement (Priority: P2)

Seven days after the first send, any prospect who has not replied (and is not suppressed)
becomes eligible for one follow-up. The system reads the strongest engagement signal
observed — clicked, opened, or silent — and shapes the follow-up accordingly (a clicker
gets a stronger, more direct second touch; an opener a lighter nudge; a silent prospect a
different-angle retry). The follow-up is drafted with its own strategy/reasoning note,
threaded to the original message, and placed in the morning review like any other draft.

**Acceptance:** follow-ups are drafted only for non-replied, non-suppressed prospects at
~+7 days; the follow-up's strategy note records the engagement tier and how it shaped the
draft; raw opens are never a hard include/exclude gate; every follow-up passes the
approval gate before sending; no prospect receives more than 2 touches in the pilot.

### Edge Cases

- **No prospects left in the batch** → the nightly run completes cleanly, drafts nothing,
  logs the empty run.
- **Research yields nothing usable** for a prospect → the draft is still produced but the
  reasoning note flags thin research; the operator can reject without penalty.
- **OAuth connection expired** → the send pass fails loud (Article 11/12), surfaces a
  re-auth instruction, and queues nothing blindly.
- **A draft contains an unsourced claim/offer** → it is flagged at approval (Article 17),
  not silently presented as fact.
- **Operator skips a morning** → un-actioned drafts carry to the next review; nothing
  auto-sends.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Inputs (operator-provided before day one)
- **FR-001** The system MUST consume a manually-built prospect list (30–50 companies/
  contacts). The system MUST NOT discover or acquire prospects in this phase.
- **FR-002** The system MUST read a Richbond **knowledge base** — a single living
  document (or small set) describing what Richbond sells, who buys, buying-intent
  triggers, common objections, and differentiators — maintained manually by the operator.
- **FR-003** The system MUST read a **strategy library** — a folder of editable documents,
  each describing one cold-email strategy/principle/technique. The operator can add,
  refine, or remove documents at any time during the experiment.

#### Research & drafting
- **FR-004** For each prospect, the system MUST perform research (web, company site,
  recent news, LinkedIn) and produce a research summary visible at approval.
- **FR-005** The system MUST select one or more strategies from the library per draft,
  grounded in what the research surfaced — not chosen at random.
- **FR-006** Every factual claim or offer in a draft MUST be grounded in the knowledge
  base; unsourced or low-confidence claims MUST be flagged at approval, never presented
  as fact (Article 17).
- **FR-007** For every draft the system MUST write a **strategy-and-reasoning note**
  recording which strategies were chosen, why for this prospect, and how applied. The
  note MUST be visible alongside the draft at approval.
- **FR-008** Drafting MUST remain behind the existing replaceable drafter seam.

#### Approval & feedback
- **FR-009** Every send MUST be preceded by an explicit operator approval of that specific
  draft (Article 6). The approval gate is default-on for this experiment; autonomous send
  is out of scope here.
- **FR-010** The feedback interface MUST capture, per draft, a **verdict** (approve / edit
  / reject) and an optional free-text **comment**.
- **FR-011** Captured comments MUST be readable by the system as input to subsequent
  nightly batches.

#### Sending
- **FR-012** The system MUST send approved drafts from the real `richbond.ma` mailbox via
  the existing M365 Graph path; replies MUST return to that mailbox.
- **FR-013** Sends MUST occur only Tuesday–Thursday, scheduled to land in the recipient's
  local 10am–2pm window.
- **FR-014** Daily send volume MUST respect a weekly ceiling that ramps from 3–5/day
  (week 1) to ~10–15/day (week 4).
- **FR-015** The system MUST NOT send any draft without a recorded approval.

#### Follow-up sequencing
- **FR-016a** ~7 days after the first send, the system MUST draft one follow-up for each
  prospect that has not replied and is not suppressed. No prospect MUST receive more than
  2 touches in the pilot (initial + one follow-up).
- **FR-016b** The follow-up MUST be shaped by the strongest observed engagement signal
  (clicked / opened / silent). Raw opens MUST NOT be used as a hard include/exclude gate
  (open tracking is unreliable); they only influence the follow-up's angle and priority.
- **FR-016c** The follow-up MUST carry its own strategy/reasoning note (recording the
  engagement tier and how it shaped the draft) and MUST pass the approval gate (FR-009)
  before sending. The follow-up MUST thread to the original message.

#### Reply boundary
- **FR-016** The system MUST support a manual operator flag marking a prospect "replied".
- **FR-017** On a replied flag, the system MUST halt all further outreach to that prospect,
  record the reply event, and update suppression. It MUST NOT read or respond to the reply
  (Article 15).

#### Learning
- **FR-018** After each day's feedback, the system MUST update a **conclusions log** when
  patterns emerge, with dated observations tied to the feedback.
- **FR-019** Each nightly batch MUST incorporate current comments, the conclusions log,
  and the current strategy-library state as drafting input.

#### Measurement
- **FR-020** The system MUST support a per-prospect tracking record: send date, open
  status, click status, reply status, and reply category. Opens/clicks via `ww-tracking`;
  reply status/category set manually by the operator.
- **FR-021** The system MUST be able to report the experiment's reply rate (per the Overview
  definition) over the 30-day window.

#### Boundaries
- **FR-022** The system MUST NOT integrate any lead database (Apollo etc.), any cold-email
  infrastructure (Instantly/Smartlead), secondary-domain management, warm-up, or inbox
  rotation in this phase. Data-source and sending adapters remain as architectural seams
  only.

### Key Entities

- **Prospect** — a hand-chosen target (company + contact); carries research summary,
  tracking record, suppression state.
- **Knowledge base** — the living Richbond fact document(s); the source of grounded claims.
- **Strategy library** — editable strategy documents; the menu the writer chooses from.
- **Draft** — email subject/body + strategy-and-reasoning note + research summary + verdict
  + comment.
- **Conclusion entry** — a dated observation about what is/ isn't working.
- **Engagement event** — open / click (from `ww-tracking`) or reply (manual flag).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** The daily cycle (nightly draft → morning review → mid-week send → conclusions
  update) ran consistently across the 30 days.
- **SC-002** Reply rate over the window is computed and compared against the verdict rule
  (≥5% / 2–5% / <2%).
- **SC-003** Day-30 drafts are judged measurably better than day-one drafts (secondary
  hypothesis) — evidenced by the conclusions log and the feedback trend (fewer heavy edits,
  more approve-as-is).
- **SC-004** The strategy log, conclusions log, and feedback together produced insight
  substantial enough to inform the full WW product design.
- **SC-005** No email was ever sent without a recorded approval; no reply content was ever
  ingested by the system.

---

## Assumptions

- The operator prepares three inputs **before day one** (not Claude Code's responsibility):
  the 30–50 prospect list, a working-draft knowledge base, and a v0 strategy library
  (3–4 docs from initial research). The quality of these inputs governs everything
  downstream.
- The `richbond.ma` M365 OAuth connection from 002 is reusable; if expired, a ~2-minute
  device-code re-auth restores it (not a rebuild).
- Implementation form is Claude Code's discretion (see below).

## Claude Code discretion (HOW, decided with hands on the code)

- The feedback interface form (web app / CLI / markdown-file system / hybrid).
- Storage format for prospects, drafts, feedback, conclusions.
- The research approach (which sources, how combined).
- How strategies are selected from the library.

**Not** Claude Code's to decide: the locked decisions above, the success thresholds, and
the experiment-vs-product scope. When uncertain, ask before expanding.

## Dependencies

- `ww-outreach` (M365 Graph send/auth — un-retired), `ww-engine` (approval/draft/send),
  `ww-llm`, `ww-tracking` (un-retired), `ww-core`.
- Constitution Article 16 validation-pilot exception (amended 2026-06-08).

## Deferred (until the experiment justifies it)

Deeper multi-touch sequences beyond the pilot's 2-touch cap, Apollo/lead-DB integration,
Instantly/sending infrastructure, secondary domains, inbox rotation, multi-tenant,
industry-adaptive KB configuration, the dashboard as a product surface, fuller
learning-engine and reasoning panel.

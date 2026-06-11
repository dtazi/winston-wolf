# Winston Wolf — Project Constitution
**Project:** winston-wolf  
**Ratification Date:** 2026-05-04  
**Last Amended:** 2026-06-11

---

## Purpose

Winston Wolf is an AI-powered B2B outreach platform. It automates 
lead discovery (Scout), personalised email outreach (Outreach), 
and performance learning (Learning Engine), surfaced through a 
unified Dashboard. It is built first for Richbond as a single-tenant 
deployment, architected from day one to become a multi-tenant SaaS.

---

## Article 1 — Build for Scale from Day One

Every feature MUST be built as if a second client will use it 
tomorrow, even if only one client exists today. No shortcuts that 
create single-tenant assumptions in the code. Client data MUST 
always be scoped to a tenant ID, even in Phase 1 where only one 
tenant exists.

---

## Article 2 — Simplicity Over Cleverness

The simplest working solution is always preferred over an elegant 
but complex one. If two approaches solve the same problem, choose 
the one that is easier to read, debug, and explain. Do not 
over-engineer. Build what is needed now, not what might be needed 
in three years.

---

## Article 3 — Security is Non-Negotiable

The platform handles personal prospect data (names, emails, job 
titles, company data). The following rules are absolute:

- Prospect data MUST never be logged in plain text
- All data in transit MUST use HTTPS/TLS
- All stored sensitive data MUST be encrypted at rest
- API keys and secrets MUST live in environment variables, 
  never in code
- Each tenant's data MUST be completely isolated — no query 
  may access another tenant's data under any circumstance
- Email sending credentials MUST be stored encrypted, 
  never in plain text

---

## Article 4 — AI Cost Awareness

**Code-first principle.** If a task can be accomplished with 
deterministic code, it MUST be done with code, not with an LLM. 
LLMs are reserved for natural-language generation (composing 
copy), judgment over ambiguous input (classifying sentiment, 
ranking subjective relevance), and conversational synthesis 
where the rules cannot be specified up front. Parsing structured 
data, applying well-defined classifications, computing 
aggregates, and pattern matching MUST be done in code.

**Cost is a second-order concern during the build phase.** Be 
mindful of token cost, but do not let it block progress. 
Prompt/context trimming, caching, and similar optimizations are 
deferred until a feature works correctly. Correctness first, 
efficiency second.

---

## Article 5 — Modular Architecture

The platform's modular boundaries exist to enable disciplined 
extension across industries. Industry knowledge lives in 
configuration, prompts, data sources, and tenant settings, 
never in module internals.

The platform's modules sit in the **intelligence + workflow 
layer**: Signal Filter, Knowledge Base, AI Writer, Approval 
Workflow, and Learning Engine, surfaced through the Dashboard. 
Each module MUST be independently deployable and testable. No 
module may be tightly coupled to another's internal logic — 
they communicate through defined interfaces only.

All external systems — the sending tool, lead data, CRMs, 
tracking signals — MUST be reached ONLY through a narrow 
adapter layer. No module outside that adapter layer may know 
that a specific vendor exists or call a vendor API directly. 
This preserves the option to add or swap providers without 
rewriting the system.

---

## Article 6 — Human Approval Gates

Every new campaign starts in approval-required mode: each cold 
email is reviewed by a human before sending. Autonomous mode is 
optional, enabled only by an explicit, deliberate, per-campaign 
operator action, and is reversible back to review at any time. 
The system MUST never send an email without either recorded 
human approval of that specific email or explicitly-enabled 
automation.

The approval gate exists so a human can apply industry knowledge 
the AI lacks and catch fabricated or unauthorized content before 
it reaches a prospect. At approval, the draft MUST show the AI's 
reasoning and the source of every factual claim or offer it 
makes, so the reviewer can distinguish grounded statements from 
invented ones.

---

## Article 8 — Testing Standards

Every module MUST have tests before it is considered complete. 
At minimum: one test that proves the happy path works, one test 
that proves errors are handled gracefully. No feature is done 
until it has been tested.

---

## Article 9 — Documentation Separation

Specifications describe WHAT the system does and WHY. Plans 
describe HOW it is built. These must never be mixed. A spec 
must be readable by a non-technical person. A plan is for 
engineers.

---

## Article 10 — Instrument Everything

Every module MUST include logging before it is considered 
production-ready. Every significant action the system takes 
— a lead being scored, an email being queued, a sequence 
being triggered, an AI model being called — MUST write a 
log entry that captures: what happened, which module did it, 
which tenant it belongs to, and a timestamp. If a bug 
occurs, the logs must be sufficient to identify the source 
without guesswork. Logging is not optional and is not added 
after the fact.

---

## Article 11 — Contain Failures

Each module MUST fail independently. If the Learning Engine 
crashes, the Outreach module continues sending. If Scout 
fails to find leads, the Dashboard still loads. No module 
may take down another. Errors MUST be caught at module 
boundaries and handled gracefully — logged, reported, and 
recovered from — never allowed to propagate silently across 
the system.

---

## Article 12 — Diagnose Before Iterating

If a fix or implementation attempt fails twice, STOP. Do 
not attempt a third approach blindly. Instead: read the 
logs, identify the actual root cause, and propose a 
diagnosis before writing any more code. Fast broken 
solutions are worse than slow correct ones. When in doubt, 
the slower and more deliberate path is always preferred.

---

## Article 13 — Rent the Plumbing

Winston Wolf builds only the intelligence and workflow layer. 
It MUST NOT build commoditized sending infrastructure — lead 
databases, email verification, domain purchasing, DNS 
configuration, inbox provisioning, warm-up management, inbox 
rotation, SMTP-level sending, infrastructure-level 
deliverability monitoring, or compliance-link injection. These 
are delegated to the integrated sending tool. Building them 
ourselves would consume months and produce zero 
differentiation; nobody chooses an outreach tool for the 
elegance of its DKIM signing.

---

## Article 14 — Compliance is Enforced, Not Configured

When the platform sends on behalf of a customer, the platform 
is co-liable (CAN-SPAM per-email penalties, GDPR by recipient 
location). Therefore suppression-list enforcement and opt-out 
propagation MUST happen automatically on every send across all 
campaigns. Compliance behavior MUST NOT be a tenant-toggleable 
feature that anyone can forget to enable.

---

## Article 15 — The Reply Boundary

When a prospect replies, the AI's scope for that prospect ends. 
The system MUST record that a reply occurred, halt all further 
outreach to that prospect, update the suppression list, and log 
the event for the learning engine. The system MUST NOT read the 
reply's content or draft a response. The conversation belongs 
to the human salesperson from that point forward.

---

## Article 16 — Sending Hygiene

Cold outreach MUST use secondary domains, never the tenant's 
primary domain — the primary domain's reputation is reserved 
for transactional and marketing email through the tenant's 
existing infrastructure. Each tenant's sending reputation and 
suppression lists MUST be isolated: one tenant's campaign 
cannot poison another tenant's results.

**Validation-pilot exception (added 2026-06-08).** Before the 
platform is built at scale, a tenant MAY run a bounded, 
time-boxed validation pilot that sends cold outreach from a 
real tenant mailbox — including a primary-domain account — 
when ALL of the following hold: (a) every send is 
human-approved (Article 6); (b) daily volume stays low 
(single/low-double digits) and the pilot is explicitly 
time-boxed; (c) the reputation risk to the primary domain is 
accepted in writing by the tenant as a deliberate experiment 
cost. This exception exists to validate the outreach motion 
before asking the tenant to buy and warm secondary domains. 
Outside such a pilot, the secondary-domain rule above is 
absolute, and a validated motion MUST migrate to 
secondary-domain sending before scaling volume.

---

## Article 17 — Grounded Claims, No Fabricated Commitments

The AI writer MUST NOT invent facts, capabilities, prices, lead 
times, certifications, or offers/commitments (e.g. free samples, 
discounts, guarantees). Every factual claim or offer in a draft 
MUST be grounded in the tenant's knowledge base of approved 
facts and offers. Anything not sourced from the knowledge base 
MUST NOT appear as a commitment, and any unsourced or 
low-confidence claim MUST be flagged at approval rather than 
presented as fact. The knowledge base is the single source of 
what the tenant is authorized to say.

---

## Article 18 — Living Documentation

The project's durable records — this constitution, specs, 
`knowledge/`, the agent memory, and tenant knowledge bases — MUST 
be maintained, not merely appended. A record that contradicts 
current reality is a defect, equal in severity to broken code.

- **Resolve and remove.** When an open question is answered, an 
  experiment concluded, a task validated, or an `[UNCONFIRMED]` 
  fact confirmed: record the outcome in the correct layer AND 
  delete the now-stale open item, TODO, or marker. Leaving a 
  resolved question open is a violation. (E.g. once a smoke test 
  passes, document the result and remove the "smoke pending" item 
  — never leave it hanging.)
- **Supersede, never silently overwrite.** When a decision is 
  reversed, mark the prior record *superseded* with a dated 
  pointer to what replaced it. Reasoning and history are 
  preserved; current truth is never left to contradict a stale 
  entry.
- **One source of current truth.** "What we are building now" 
  lives in the active spec. Forward-looking ideas live in VISION; 
  historical decisions live in their dated ledgers. Scope MUST 
  NOT be smeared across all three.
- **Maintenance is part of done.** A change is not complete until 
  the records it invalidated are updated or closed in the same 
  pass.

---

## Article 19 — Evidence Before Investment

The motion MUST be proven with the cheapest viable tooling before 
money is spent scaling it. No investment in paid lead databases, 
email-verification services, additional domains, or mass-sending 
platforms is made until a minimum-cost test produces evidence the 
motion works. Spend is earned by signal, not assumed up front. 
This is a cost-discipline gate, not a permanent ban: once a 
bounded test validates the motion, investing to scale it is the 
correct next step — justified by the evidence the test produced.
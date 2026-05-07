# Winston Wolf — Project Constitution
**Project:** winston-wolf  
**Ratification Date:** 2026-05-04  
**Last Amended:** 2026-05-04

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

Every feature that uses an AI model MUST be designed with token 
cost in mind. Prompts MUST be concise. Context passed to models 
MUST be trimmed to only what is necessary. No feature may send 
the full database to a model when a summary will do. Caching MUST 
be used wherever AI responses can be reused.

---

## Article 5 — Modular Architecture

The platform's modular boundaries exist to enable disciplined 
extension across industries. Industry knowledge lives in 
configuration, prompts, data sources, and tenant settings, 
never in module internals.

The platform has six distinct modules: Configuration, Scout, 
Outreach, Engagement Tracker, Knowledge Base, Learning Engine. 
Each module MUST be independently deployable and testable. 
No module may be tightly coupled to another's internal logic — 
they communicate through defined interfaces only.

---

## Article 6 — Human Approval Gates

The Outreach module MUST support an approval mode where emails 
are queued for human review before sending. Fully automated mode 
is optional and must be explicitly enabled per campaign. The 
default for any new campaign is approval-required. The system 
MUST never send emails without either explicit human approval 
or explicit automation mode being turned on.

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
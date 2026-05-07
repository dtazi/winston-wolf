# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md`

For each gate below, mark ✅ pass, ⚠ N/A (one-line reason), or ❌ violation.
Every ❌ MUST be recorded in **Complexity Tracking** with a tradeoff
justification, or the plan does not proceed.

### Article 1 — Build for Scale from Day One

- [ ] Every new table, query, and API surface scopes by `tenant_id` (or
      equivalent). No implicitly single-tenant code paths are introduced,
      even though only Richbond exists in Phase 1.

### Article 2 — Simplicity Over Cleverness

- [ ] The chosen approach is the simplest one that meets the requirements.
      Any new abstraction, framework, or service layer is justified in
      Complexity Tracking.

### Article 3 — Security is Non-Negotiable

- [ ] Prospect data is never written to logs in plain text.
- [ ] All network calls use HTTPS/TLS; all stored sensitive data is
      encrypted at rest.
- [ ] API keys, secrets, and email-sending credentials live in environment
      variables (or an encrypted secret store), never in source.
- [ ] Tenant isolation is enforced at the query layer; no code path can
      read another tenant's data.

### Article 4 — AI Cost Awareness

- [ ] Every AI/LLM call has a defined input shape and a token budget;
      whole-table or whole-DB dumps to a model are avoided.
- [ ] AI responses that can be reused are cached, with cache key and TTL
      documented in the plan.

### Article 5 — Modular Architecture

- [ ] Feature respects the six module boundaries (Configuration, Scout,
      Outreach, Engagement Tracker, Knowledge Base, Learning Engine).
      Cross-module access goes through defined interfaces only — no
      reaching into another module's internals.
- [ ] Any new module is independently deployable and testable.

### Article 6 — Human Approval Gates

- [ ] If the feature touches Outreach: new campaigns default to
      approval-required; fully automated mode requires explicit
      per-campaign opt-in. The system cannot send email without one of
      those modes being set.

### Article 8 — Testing Standards

- [ ] Plan includes at least one happy-path test and one error-path test
      for every new module or service the feature introduces.

### Article 9 — Documentation Separation

- [ ] Spec stays WHAT/WHY (no implementation choices); plan stays HOW.
      No implementation details have leaked into spec.md, and no
      product/UX rationale lives only in plan.md.

### Article 10 — Instrument Everything

- [ ] Every significant action this feature performs (lead scored, email
      queued, sequence triggered, AI model called, etc.) emits a
      structured log entry with action, module, `tenant_id`, and timestamp.
- [ ] Logging is in scope from the first implementation task, not deferred
      to a polish phase.

### Article 11 — Contain Failures

- [ ] Failures inside this feature's module cannot cascade to other
      modules. Errors are caught at the module boundary, logged, reported,
      and recovered from — never allowed to propagate silently.

### Article 12 — Diagnose Before Iterating

- [ ] If implementation hits two failed attempts at the same problem, the
      plan calls for a stop-and-diagnose pause (read logs, identify root
      cause, propose a diagnosis) before a third attempt.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

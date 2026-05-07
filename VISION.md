# Winston Wolf — Vision Document

This file captures strategic ideas under consideration for future phases. These ideas are NOT part of the current constitution or specs. They are noted here so they are not forgotten and can be properly evaluated when the time comes.

## Out of Scope / Anti-Goals

These are deliberate strategic exclusions, not oversights. Re-opening any of them requires an explicit decision. (Constitutional rules live in `.specify/memory/constitution.md` and are not repeated here.)

- **No scraping behind-login databases or attendee lists.** Conflicts with source-platform terms of service and platform reputation. Public exhibitor lists, speaker lists, and post-event press are acceptable.
- **No "framework for any outreach use case."** Industry-adaptive is not industry-agnostic. The framework trap is a known anti-goal.
- **No hardcoded industry concepts in the core schema.** No enum values like "hotel opening" or "plastics buyer" in core schema. Industry knowledge lives in configuration, prompts, data sources, and tenant settings.
- **No "any B2B" Phase 2 generality.** Phase 2 is deliberate vertical-by-vertical evaluation, not blanket horizontal expansion.

## Hypotheses Under Test

These are bets, not commitments. Phase 1 will validate or invalidate them through real-world use by Richbond Group and the plastics company.

1. **Cost-effectiveness** — Winston Wolf can deliver a lower per-lead cost than horizontal SaaS competitors like Gojiberry AI ($99/seat/month).
2. **Research depth** — Industry-adaptive research outperforms a horizontal LinkedIn-primary signal taxonomy on relevance and conversion. Five "knobs" are available to specialise in: data sources, search/matching, RAG quality, A/B testing rigor, and tenant-specific learning loops. We expect to pick 1–2 to lead with based on what Richbond's parallel Gojiberry experiment reveals.

## Ideas Parking Lot

Not in scope yet. Kept here so they are not lost; revisit when the conditions noted are met.

- **Open-source positioning.** Bet: an open-source posture would attract a customer segment closed SaaS cannot serve (data-sensitive buyers, non-US jurisdictions, customers needing deep customisation). Revisit when there is conviction that the trade-offs of public publishing are worth it for a specific audience.
- **Bootstrapped ICP from exemplars.** Derive an Ideal Customer Profile from 3–5 of the customer's existing best clients. Diagnostic-tree (doctor / mechanic) approach, not blank-form entry.
- **Vertical event-data ingestion.** Public exhibitor lists, speaker lists, post-event press releases as a structured input to Scout.
- **Client-base-as-seed-data.** A customer's existing client list as exemplar input for Scout, feeding both the tenant's matching and the platform-wide Learning Engine.
- **Diagnostic flow for ICP definition.** Guided narrowing rather than open-ended description.

## Future SaaS Considerations

### Tiered pricing with optional data-sharing tier
Idea: offer two pricing tiers for SaaS clients —
- Premium tier: full data isolation, no learnings shared across tenants.
- Standard tier (lower price): clients opt in to contribute anonymised performance data to a shared learning pool, and benefit from the collective intelligence.

This idea is NOT being built into Phase 1. It would require:
- Legal framework for cross-tenant data sharing (GDPR, CAN-SPAM, CCPA review).
- Robust anonymisation strategy that withstands re-identification attacks against B2B data.
- Explicit opt-in consent mechanisms in every standard-tier contract.
- Architectural rework of the Learning Engine to support pooled learning while maintaining tenant isolation.
- Sufficient client base (estimated 10+ active tenants) for the shared pool to provide meaningful value.

Revisit when: the platform has 10+ active tenants AND legal review is complete AND there is documented client demand for a lower-priced tier.

# Winston Wolf — Vision Document

This file captures strategic ideas under consideration for future phases. These ideas are NOT part of the current constitution or specs. They are noted here so they are not forgotten and can be properly evaluated when the time comes.

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

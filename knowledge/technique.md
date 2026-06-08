# Technique — craft: cold-email, tracking behavior, scouting

## Email-tracking reality
- **Gmail** fires the open pixel **on open, not on delivery**, routed through
  Google's image proxy (UA shows `GoogleImageProxy`). So a Gmail "opened" = a
  human action, but proxied. (Confirmed by a control email left unopened →
  recorded SENT only.)
- **Apple Mail Privacy Protection prefetches on delivery** → phantom opens with
  no human. So across a mixed prospect base, **opens are SOFT**.
- **Clicks (minus automated scanners) are the trustworthy signal.** Mail-security
  scanners click within seconds of send — **intermittent**, not guaranteed; don't
  treat every fast click as human or assume their absence means safety.
- Evidence: live smokes 2026-06-08 → `data/scouting/lessons.md` L4/L5.

## Email finding / deliverability
- **Hunter-guessed emails bounce**, and bounces burn the primary-domain
  reputation we're deliberately spending (Art 16). **Hand-verify at pilot scale.**

## Scouting
- Method / question template: `data/scouting/playbook.md`
- Methods catalog (find industries / companies / emails, classified):
  `data/scouting/methods.md`
- Lessons (each with rationale + a stated doubt): `data/scouting/lessons.md`
- Run as an **AI co-pilot session** now; **intent-data sources** (import records,
  trade-show exhibitor lists) beat generic industry scraping.

# Scouting lessons — self-taught, with rationale and doubt

Append-only. Each lesson: the claim · **why** we believe it · confidence ·
**open doubt** (the reason we might be wrong). Doubt is a first-class field — a
lesson without a stated way it could be wrong is suspect.

## 2026-06-08

**L1 — Intent-data sources beat generic industry scraping for finding companies.**
Why: import records and expo lists signal *actual buying behaviour*, not just
category membership. Confidence: med-high. Doubt: import records may be stale or
name the *distributor/importer*, not the end-buyer — must verify the role before
treating as a prospect.

**L2 — At pilot scale, hand-verify emails; avoid bulk Hunter guesses.**
Why: guessed emails bounce, and bounces burn the richbond.ma primary-domain
reputation we're deliberately spending under the Art 16 exception. Confidence:
high. Doubt: doesn't scale — past a few hundred, manual verification fails and
we'll need a verified-email vendor + secondary domains.

**L3 — Run scouting as an AI co-pilot session now; build the autonomous Scout
tool only if the thesis validates.** Why: ~50 one-time prospects don't justify a
persistent pipeline (Art 2); productionize the *reasoning* later. Confidence:
med. Doubt: if co-pilot scouting proves trivially repeatable, the build
threshold may be lower than assumed.

**L4 — Email opens are unreliable; clicks (minus automated scanners) are the
real signal.** Why: the live smoke produced 2 opens via Gmail's image proxy and
1 "click" 6s after send from a scanner UA — only the later Android clicks were
human. Confidence: high. Doubt: scanner/proxy behaviour varies by the
recipient's mail security; not every fast click is a bot.

**L5 — Gmail fires opens on *open*, not on delivery; the scanner click is
intermittent (control test).** Why: a control email left unopened recorded
SENT only — zero opens, zero clicks. So Gmail opens require recipient action
(via Google's image proxy), and the earlier 6s scanner click did NOT recur.
Confidence: med-high (n=1 control). Doubt: this is Gmail-specific — Apple Mail
Privacy Protection *does* prefetch on delivery (phantom opens), so across a
mixed prospect base opens stay soft. Re-test with an Apple Mail recipient before
generalising.

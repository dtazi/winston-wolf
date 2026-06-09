# Product — strategy, scope, hypotheses, findings

## Scope history (two pivots)
- **2026-06-05:** narrowed to the **intelligence + workflow layer on top of
  Instantly** (away from the build-everything 3-pillar plan).
- **2026-06-08:** narrowed again to a **30-day proof-of-life EXPERIMENT**;
  **Instantly deferred entirely.** Test the thesis before building the product.
  Detail: `specs/004-proof-of-life-experiment/`.

## The thesis under test
Deeply-researched + deliberate-strategy + human-approved cold email, low volume
from a real **richbond.ma** mailbox, yields qualified replies. **Verdict:** reply
rate (unique repliers ÷ contacted) **≥5% validate / <2% kill / 2–5% iterate.**

## Key decisions
- **Art 16 amended:** primary-domain cold send allowed for a bounded, low-volume,
  human-approved pilot (operator accepted the reputation risk in writing).
- **Scout (auto acquisition) deferred → Phase 2** if the thesis validates.
  Scouting runs now as an **AI co-pilot session** (technique.md / data/scouting/).
- **Follow-ups:** one at +7 days, **engagement-tiered, not raw-open-gated**.
- **Reply handling:** manual flag; never read reply content (Art 15).

## Phase-2 backlog (triggered by a validated thesis)
- Scout tool + Hunter + enrichment — productionize the co-pilot scouting logic.
- **Controlled "Richbond Export" landing page + CONSENTED first-party on-site
  analytics** (session duration / pages viewed), keyed by the lead token already
  passed through `/c/` — a far richer engagement signal than opens/clicks;
  requires a GDPR consent layer. (the "cookie" discussion)
- Open/click-tracking real client IP (capture `X-Forwarded-For`).

## Market findings — Step-1 demand map (2026-06-09, deep-research run wf_7bb356a7-007; 23 sources, 25 claims verified → 18 confirmed / 7 refuted)

**Ranked beachhead for the 30-day cold-email pilot (by credibility + reachability, NOT raw TAM):**
1. **Hospitality FF&E purchasing agents** — outsourced firms that buy mattresses on
   hotel owners' behalf: Beyer Brown, Benjamin West, R-W Purchasing (fka Bray Whaler),
   Stroud Group, Innvision, Curve, RFP Design. Named, coldable decision-makers
   (Procurement Mgr / Interior Designer / Project Mgr). No TAA gate. Fastest cycle.
   *Best Richbond fit — Beautyrest/Simmons hospitality heritage.* (confirmed 3-0)
2. **Avendra & hospitality GPOs** — Avendra self-reports ~$20.5B purchasing power,
   21k locations, explicitly procures "mattresses and box springs" (FF&E). Largest
   aggregated volume but requires winning a supplier agreement = longer cycle. (confirmed 3-0)
3. **Healthcare GPOs (Vizient/Premier)** — Vizient #1 by staffed beds (~468k, ~29% of
   all US beds, self-reported ~$100B member purchases); hospitals run dedicated
   procurement depts. TAA-friendly for VA. BUT re-buy-cycle + unit-volume data is THIN
   (see refuted). Longer onboarding. (concentration confirmed 3-0; cycle/volume unconfirmed)

**Sizing (all flagged directional — secondary/syndicated, ISPA primary data is paywalled):**
- US hospitality mattress market ~$1.87B (2024) → ~$1.96B (2025), hotels & resorts
  ~72% revenue share (Polaris/Grand View/RnM — medium confidence, opaque methodology).
- Buying trigger = brand **PIPs every ~6-7yr** + ownership change / conversion /
  franchise renewal (confirmed 3-0 — concrete timing hook for outreach).
- Mattress replacement ~5-8yr (soft, blog-grade, no primary survey).

**TAA gate (hard filter for federal/VA/military):** Morocco IS a TAA-designated FTA
country (FAR 52.225-5 names it verbatim; VA OPAL lists it) → Richbond is federally
ELIGIBLE — *conditional on* certifying "substantial transformation" in Morocco AND the
buy clearing the ~$100K FTA threshold. (confirmed 3-0). Military demand is real ($55M
USMC barracks allocation, FY25-26) but episodic + formal-RFP, NOT cold-email-addressable
→ excluded from the pilot, kept as an opportunistic federal play.

**REFUTED in verification (do NOT cite these — they failed adversarial check):**
- "Hotels = 74% of commercial bedding demand / ~89M units" (0-3, marketgrowthreports).
- "97% of US hospitals have GPO affiliations" (1-2) — GPO-mediation share is UNquantified.
- "AHA recommends 5-yr hospital mattress replacement" (0-3) + Medline 5,000-surface &
  33,000-nursing-home replacement-pool stats (0-3 each) — healthcare re-buy cycle UNKNOWN.
- "C-suite (CEO/CFO/COO) are the healthcare budget-holders" (1-2) — title unconfirmed.
- "Order.co / Fohlio / Houzz Pro are FF&E procurement intermediaries" (1-2) — those are
  software/marketplaces, not buyers; don't target them as a channel.

**Open questions (gating real list-building):** real institutional UNIT volumes by
segment (needs paid ISPA Mattress Industry Trends "contract sales" line); true healthcare
GPO-mediation share + re-buy cycle; education/assisted-living/corrections never
independently sized (only appear inside Avendra's customer base); can Richbond actually
certify substantial-transformation origin; named current contacts at the agent firms +
Avendra supplier-onboarding. Full report: workflow run wf_7bb356a7-007.

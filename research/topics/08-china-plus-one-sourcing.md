# Topic 08 — China +1 sourcing intelligence

**Status**: Planned investigation, scheduled for Phase 3. Initiated 2026-05-07.

## Why this matters

Possible product re-positioning angle for Winston Wolf. Both Phase 1 customers — Richbond Group (Moroccan hospitality FF&E manufacturer) and Richbond's plastics company — are textbook "China +1" alternatives: non-China manufacturers selling to global buyers diversifying away from Chinese sourcing. The "China +1" trend has been structural in global supply chains since 2018 (US-China tariffs), accelerated by COVID supply shocks, and shows no sign of fading.

If Winston Wolf positions specifically around **finding buyers who are actively diversifying away from China, in your industry**, the data sources, signal taxonomy, and product wedge all change. The customer base also expands meaningfully — every non-China manufacturer trying to sell into Western buyer markets shares the same problem.

This investigation determines whether the re-positioning is viable.

## Key questions to answer

### 1. Direct-data feasibility

Can we get reliable, queryable, company-level data about which Western companies import what categories from China?

- **Primary source: US Bill of Lading data.** Public via US Customs and Border Protection. Aggregated commercially by:
  - **Panjiva** (S&P Global) — largest, oldest, has API. Enterprise-priced.
  - **ImportYeti** — has free tier; consumer-friendly.
  - **Datamyne** (Descartes) — competitor to Panjiva.
  - **ImportGenius**, **TradeNGS**, **52WMB** — smaller players.
- Test methodology: query a known US hospitality chain Richbond would want to sell to. Does the data return useful signals? At what cost?
- Coverage gaps: EU buyer data is much weaker (Eurostat / Comext are aggregate-only, not company-level). Asia / Africa: almost no public data.

### 2. Indirect-signal feasibility

When direct BoL data isn't available, can we build a probabilistic "China-dependency" score for a company?

- **HS code aggregate trade data** (Eurostat, UN Comtrade) — which industries import what % from China.
- **SEC 10-K filings** — public US companies often disclose Chinese-supplier dependency in risk factors. Searchable via EDGAR.
- **Job-posting signals** — LinkedIn / Indeed listings for sourcing roles mentioning diversification, China +1, nearshoring.
- **Public LinkedIn / news posts** — keyword signals around supplier diversification.
- **Industry reports** — McKinsey, BCG, Deloitte regularly publish China-dependency analyses.

### 3. Market sizing

How many non-China manufacturers worldwide are positioned to sell as "China +1 alternatives"?

- By geography: Mexico, Vietnam, India, Turkey, Eastern Europe, Morocco, Bangladesh, Indonesia, Thailand, etc.
- By industry: furniture, plastics, electronics, textiles, food packaging, automotive, etc.
- Realistic addressable market for Winston Wolf at solo / early-team scale.

### 4. Buyer geography of Winston Wolf's actual customers

- Where are Richbond's actual sales targets? EU? US? Both?
- If primary EU: BoL data weaker, indirect signals matter more.
- If primary US: BoL data dominant, direct queries possible.
- Determines which data investments are worth making first.

### 5. Competitor landscape

- Are there existing China +1-specialised outreach tools? Likely no (generic horizontal SaaS like Gojiberry doesn't have this angle).
- Adjacent: supply chain platforms (TradeBeyond, Sourcing Innovation, Resilinc) — different category, different buyer, but related.
- Likely white space.

## Activities (estimated 2–3 days within Phase 3)

| Day | Activity | Output |
|---|---|---|
| 1 | Test Panjiva and ImportYeti on a real query (a known US hospitality chain). Verify data quality, pricing tiers, API access. | Notes in this file: what's findable, at what cost. |
| 2 | Map indirect signal sources. Test what's actually findable from LinkedIn, SEC EDGAR, news APIs, industry reports. | Notes in this file. |
| 3 | Market sizing + competitor landscape research. Decision document. | `research/decisions/DEC-003-china-plus-one-positioning.md`. |

## What "done" looks like

`research/decisions/DEC-003-china-plus-one-positioning.md` — written and committed, with one of three recommendations:
1. **Re-position** Winston Wolf around China +1 entirely. Update VISION.md, README, Scout MVP plan.
2. **Partial re-position** — China +1 becomes the lead vertical / GTM angle, but the platform stays multi-vertical-capable.
3. **Stay** with current generic-but-industry-adaptive positioning. Capture China +1 as a parking-lot item.

The decision is data-backed, not aesthetic.

## References for Phase 3

- Panjiva, ImportYeti, Datamyne docs and pricing pages.
- US Customs and Border Protection (CBP) public-records guidance.
- *"Risk, resilience, and rebalancing in global value chains"* — McKinsey (2020+ updates).
- *"China +1: An emerging strategy for global manufacturers"* — BCG and similar reports.
- Reshoring Initiative annual reports (US reshoring trends).
- Eurostat / Comext (EU trade data).
- UN Comtrade.
- SEC EDGAR full-text search of 10-K risk factors.

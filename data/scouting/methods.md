# Scouting methods — catalog

Living catalog of ways to find **industries**, **companies**, and **emails**.
Each method: what it finds · yield · difficulty · status · notes. Rated from
experience; ratings are provisional and meant to be revised as we learn.

Status legend: `in-use` · `planned` · `untested` · `caution` · `retired`.

## A. Finding industries / demand
| Method | Yield | Difficulty | Status | Notes |
|---|---|---|---|---|
| AI/LLM market reasoning (Claude/Perplexity w/ web) | high (breadth) | low | in-use | Fast, broad. Market-size claims MUST be sourced, not guessed. |
| Industry reports / trade associations | med | med | untested | Authoritative sizing; often paywalled. |

## B. Finding companies
| Method | Yield | Difficulty | Status | Notes |
|---|---|---|---|---|
| US import/customs records (ImportYeti free; Panjiva/ImportGenius paid) | high | low–med | planned | **Intent signal** — who actually imports mattresses. Verify importer is an end-buyer vs distributor. |
| Trade-show exhibitor/attendee lists (hospitality FF&E, healthcare procurement) | med–high | low–med | planned | Intent signal; public exhibitor lists. |
| LinkedIn (company + people search) | high | med | planned | Strong for people; rate-limited. |
| Public directories (e.g. CMS provider lists for healthcare) | med | low | untested | The retired `cms_nursing_home` scraper targeted this category. |
| Track "what they buy/sell" — RFP/bid databases, GPO membership, procurement portals | ? | ? | untested | Djaafar's idea; promising, unproven. |

## C. Finding emails
| Method | Yield | Difficulty | Status | Notes |
|---|---|---|---|---|
| LinkedIn + company site (manual) | med | low (per contact) | in-use | Low bounce; right for pilot scale. |
| Hunter.io (pattern guess + SMTP verify) | high | low | **caution** | Guessed emails bounce; bounces burn the richbond.ma **primary-domain** reputation (Art 16). Use verified only, sparingly. |
| Pattern inference (first.last@domain) | high | low | caution | Verify before sending. |

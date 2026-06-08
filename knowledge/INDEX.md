# Winston Wolf — Knowledge Index

**Read this first.** Durable findings and lessons from building WW, across *all*
sides — not just code — so nothing is siloed or forgotten. This file is the
router: each entry points to where a kind of knowledge lives. You should be able
to find the right file from here **without reading everything**.

**How to maintain:** when we learn something durable, append it to the matching
file below and add a one-line pointer here. A finding without a home goes in the
closest file; split a file into a folder only when it gets unwieldy.

| File | What lives here |
|---|---|
| [operations.md](operations.md) | Live/prod state, credentials, what's actually deployed & **done**. *(e.g. WW has really sent email; M365 auth; tracking is live; DB state)* — check here before assuming a capability doesn't exist. |
| [architecture.md](architecture.md) | System structure: the adapter → intelligence → workflow layering, how vendors are reached, the public edge, module map. |
| [engineering.md](engineering.md) | Code conventions, gotchas (SQLite timestamps, two-pass migrations), testing approach. |
| [product.md](product.md) | Strategy, the two pivots, the experiment thesis + verdict thresholds, key decisions, Phase-2 backlog, market findings. |
| [technique.md](technique.md) | Craft: email-tracking reality (Gmail vs Apple opens), deliverability, scouting (→ `data/scouting/`). |

**Related, not duplicated here:** the Constitution (`.specify/memory/constitution.md` = law) · per-feature specs (`specs/`) · scouting working files (`data/scouting/`).

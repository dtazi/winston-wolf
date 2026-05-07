# Winston Wolf — Research

This folder is the **specialisation phase**: structured learning about lead-discovery technology before we commit to a search backend, embedding strategy, or B2B-contact-discovery approach. The goal is for the project owner to become deeply expert in this corner of the technology landscape — not just to pick a tool off a shelf.

The primary artefact of this phase is **understanding** (captured in `topics/`). Code prototypes are disposable. Decisions get formal records.

## Current state

- **Phase**: 1 — Landscape mapping
- **Started**: 2026-05-07
- **In progress**: Topic 01 — Search algorithms
- **Blocked on**: Old-Mac setup for the Telegram bot (deferred until user is at the device)

## Folder structure

| Folder | Purpose |
|---|---|
| `topics/` | Durable notes per topic. The primary artefact. Rewrite as understanding deepens. |
| `topics/07-vendor-deep-dives/` | One file per vendor (Tavily, Brave, Exa, Perplexity, etc.). |
| `experiments/` | Small Python prototypes. Disposable. |
| `synthesis/` | Weekly write-ups (`YYYY-MM-DD-week-N.md`) — what we learned, decisions, open questions. |
| `decisions/` | Formal decision records (`DEC-NNN-name.md`) with rubric, evidence, and verdict. |

## Roadmap (compressed)

| Phase | Days | Done when |
|---|---|---|
| 1. Landscape mapping | 3 | All 6 topic files drafted in `topics/`; vendor stubs in `topics/07-vendor-deep-dives/` |
| 2. Hands-on prototypes | 5 | 5–10 prototypes in `experiments/`; topic files updated with hands-on notes |
| 3. B2B contact-discovery deep-dive | 4 | Topic 05 expanded; data-sourcing map for Apollo, ZoomInfo, Hunter, Clay |
| 4. Comparative evaluation | 3 | Bake-off harness in `experiments/`; rubric scores in `decisions/DEC-001-search-backend.md` |
| 5. Synthesis | 2 | `decisions/DEC-002-research-architecture.md` written; topic files polished |

Total: ~3 weeks of focused work.

## Topic index

1. [Search algorithms](topics/01-search-algorithms.md) — sparse, dense, hybrid, reranking
2. Web search stack — crawlers, indexes, ranking economics *(not yet started)*
3. Agent loops — LLM tool use, multi-step research, failure modes *(not yet started)*
4. RAG fundamentals — chunking, embeddings, vector DBs, lost-in-the-middle *(not yet started)*
5. B2B contact discovery — how Apollo/ZoomInfo source data, public sources *(not yet started)*
6. LLM orchestration — LiteLLM, LangChain/LlamaIndex, multi-LLM routing *(not yet started)*
7. Vendor deep-dives — one file per vendor *(not yet started)*

## Process

- **Weekly synthesis**: every Friday, write a short note in `synthesis/` covering what was learned, what was built, what's still confusing, what's next.
- **Rabbit-hole timer**: if a sub-question takes >half a day and isn't on a decision's critical path, capture it in the relevant `topics/` file under "open questions" and move on.
- **Decision discipline**: a formal decision goes in `decisions/` only after the relevant topic notes back it up.

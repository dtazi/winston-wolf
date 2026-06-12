# Winston Wolf Scout

Lead-pipeline visibility over the shared lead database (`data/leads.db`).
Schema is owned by `ww-core` — run `ww-core init` first (idempotent).

**Status (2026-06-12):** Scout is **built as it is used**. Automated acquisition
(the source-ingester framework: CMS Nursing Home Compare, IPEDS, TABS, …) was
retired with the Pivot-2 scope cut — see `pivot-disposition.md`. During the
proof-of-life experiment, scouting runs as an AI co-pilot session
(`data/scouting/`); capabilities are added to this module only when a real
scouting session needs them, so every piece gets practical testing immediately
(operator decision 2026-06-12, `knowledge/product.md`). The retired ingesters
are recoverable from git history if a structured source returns to scope.

What remains in-code today: the DB writer with idempotent dedupe
(`(campaign_id, source_channel_id, source_record_id)`), the cost ledger, the
enrichment adapter seams (`enrichment/base.py`), and the `status` command.

## Setup

From the `scout/` directory:

    uv sync

## Commands

### Show pipeline status

    uv run ww-scout status --campaign <campaign-id>

Counts leads per niche / source / region, plus how many have an email.

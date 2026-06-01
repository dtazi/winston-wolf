# Winston Wolf Scout

Discovers leads from public sources and writes them into the shared lead database
(`data/leads.db`). Schema is owned by `ww-core` — run `ww-core init` first
(idempotent).

## Setup

From the `scout/` directory:

    uv sync

## Concept

Scout is built around a fixed contract: each public source (CMS, IPEDS, TABS,
state licensure, etc.) becomes one `SourceIngester` class that yields
`IngestedLead` records. The lead-writer dedupes on
`(campaign_id, source_channel_id, source_record_id)` so re-running the same
ingest never produces duplicates.

Most public datasets are facility-level. The Scout MVP ingests company-level
shell leads with `person_*` fields empty. A later enrichment phase (Hunter for
verified emails, manual or LinkedIn for the person) fills those in before the
engine can draft.

## Commands

### Ingest from a source

    uv run ww-scout ingest \
      --source cms_nursing_home_compare \
      --customer richbond \
      --campaign richbond-us-institutional-pilot-2026q2 \
      --niche hc_skilled_nursing \
      --file ~/Downloads/NH_ProviderInfo.csv \
      --region-filter MT,WY,SD,ND,NE,IA,KS

`--region-filter` is optional. When set, only rows with `Provider State`
matching one of those state codes are kept — useful for the calibration tier
of the Richbond brief.

### Show ingest status

    uv run ww-scout status --campaign richbond-us-institutional-pilot-2026q2

Counts leads per niche / source / region, plus how many have been enriched
with an email.

### List known sources

    uv run ww-scout list-sources

## Available sources (v1)

| Source channel id | Sub-niche it covers | Where to get the input |
|---|---|---|
| `cms_nursing_home_compare` | `hc_skilled_nursing` | https://data.cms.gov/provider-data/dataset/4pq5-n9py — download "Provider Information" CSV |

More ingesters planned (in priority order):

- `state_al_licensure` — per-state assisted living facility lists (covers `hc_assisted_living` and `hc_memory_care`)
- `ipeds` — universe of US universities + bed counts (covers `edu_university_dorms`)
- `tabs_directory` — boarding schools (covers `edu_boarding_schools`)
- `shb_top25` — student housing operators (covers `mf_student_housing_operators`)
- `senior_housing_news_rankings` — senior independent living operators

## What's not built yet

- **Email enrichment.** Hunter integration to find verified person emails from
  (company_domain, name) is the next Scout phase. Until then, ingested leads have
  `person_email = NULL` and the engine cannot draft to them.
- **Domain discovery.** Many public datasets (CMS included) don't give the
  facility's website. A domain-finder step is needed before Hunter can be
  called. Web search across the evaluated backends will do this — also next
  Scout phase.
- **Web-search-based discovery** (Scout v2) — for niches without a clean
  public dataset.

# Quickstart — Scout Enrichment & Qualification (operator runbook)

End-to-end: turn ingested shell leads into a quality-ranked, ready-to-email list.
Assumes the ingest MVP already loaded company-level leads (`ww-scout ingest`).

## 0. One-time: schema + engines

```bash
# Schema (owned by ww-core; idempotent — adds the enrichment columns/tables)
cd ~/winston-wolf/core && uv run ww-core init

# Engine room (optional). Defaults to the Claude subscription — skip to use it.
# To add another engine later, set its key in the environment and assign a tool:
export DEEPSEEK_API_KEY=...            # example
cd ~/winston-wolf/scout
uv run ww-scout engines --set scout=deepseek     # Scout's judge now uses DeepSeek
uv run ww-scout engines                          # show the current tool→engine map
```

## 1. Describe the ideal target (the ICP)

```bash
uv run ww-scout set-profile --campaign richbond-us-institutional-pilot-2026q2 \
  --roles "procurement,facilities,operations" \
  --niche hc_skilled_nursing \
  --size-metric beds --size-min 120 \
  --regions US:MT,US:WY,US:SD,US:ND,US:NE,US:IA,US:KS \
  --description-file ./profile-richbond.txt
uv run ww-scout show-profile --campaign richbond-us-institutional-pilot-2026q2
```

(`--size-min` is your "big enough" bar; everything here is per-campaign.)

## 2. Find the person + website

```bash
uv run ww-scout enrich --campaign richbond-us-institutional-pilot-2026q2 --batch 50
```

Idempotent — re-running only touches leads still `pending`. Leads with no findable
site are marked `not_found` and parked; the batch keeps going.

## 3. Qualify (rules → AI), then look at the ranked list

```bash
uv run ww-scout qualify --campaign richbond-us-institutional-pilot-2026q2 --batch 50
uv run ww-scout review  --campaign richbond-us-institutional-pilot-2026q2
# add --reflect to qualify only if you see the AI making sloppy calls (doubles AI cost)
```

`review` shows qualified leads best→worst with score + reason, plus how many were
rejected by the free rules layer (no AI spent on those).

## 4. Uncover emails for the keepers

```bash
uv run ww-scout email --campaign richbond-us-institutional-pilot-2026q2 --batch 50
uv run ww-scout costs --campaign richbond-us-institutional-pilot-2026q2
```

Only qualified leads get a (paid) lookup. `costs` shows per-stage spend.

## 5. Hand-off

Qualified leads now carry a verified `person_email` and are ready for the Outreach
engine (002), which applies its own send-time approval gate. This feature sends
nothing itself.

## Vendor selection (needs API keys — do once)

Before `enrich`/`email` can hit real providers, pick vendors via the harness:

```bash
cd ~/winston-wolf/evaluation && cp .env.example .env   # fill EXA/TAVILY/HUNTER/... keys
uv run ww-eval run   --customer richbond --backends exa,tavily
uv run ww-eval score --customer richbond --run-id <ts>
```

Wire the highest-recall backend into Scout's config. Until then, the pipeline runs
against the `null` stub backend for dry-runs.

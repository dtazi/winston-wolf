# Quickstart — Outreach Campaign Engine (operator runbook)

Assumes `ww-core` DB exists with a customer, a campaign, a pitch, a brief, and **leads already loaded** with `campaign_id` (lead intake is a separate tool — FR-024a), and `ww-outreach auth` already done (token at `~/.winston-wolf/outreach-token.json`).

## 1. Install (from `engine/`)

```
uv sync
uv run ww-engine init          # idempotent migrations
```

## 2. Enrol the campaign's leads

```
uv run ww-engine enroll --campaign richbond-us-institutional-pilot-2026q2
# assigns rotation groups; prints per-position balance (expect ~33/33/33)
```

## 3. First batch — validate the message (campaign starts in `review` mode)

```
uv run ww-engine draft   --campaign <id> --batch 20     # off-peak; drafts touch 1
uv run ww-engine review  --campaign <id>                 # read every draft; thin ones flagged
uv run ww-engine edit    <draft_id> --body-file fix.txt  # fix any
uv run ww-engine reject  <draft_id>                      # drop any
uv run ww-engine approve-all --campaign <id>             # once happy
uv run ww-engine deliver --campaign <id>                 # sends only inside the window
uv run ww-engine detect  --campaign <id>                 # start watching for replies/bounces
```

## 4. Go autonomous (only when you trust the message)

```
uv run ww-engine go-autonomous --campaign <id>     # explicit, reversible
uv run ww-engine go-review     --campaign <id>     # pull back any time
```

## 5. Cron (operator-controlled host — the "lives on its own" part)

```cron
# draft off-peak, small batches (subscription trough)
30 2-5 * * *  cd /path/engine && uv run ww-engine draft   --campaign <id> --batch 15
# deliver hourly; the command itself no-ops outside the send window
0  *   * * *  cd /path/engine && uv run ww-engine deliver  --campaign <id>
# detect hourly — the hard stop depends on this staying fresh
20 *   * * *  cd /path/engine && uv run ww-engine detect   --campaign <id>
```

## 6. Watch it

```
uv run ww-engine status --campaign <id>     # funnel, sequence states, last run per pass, detect freshness
uv run ww-engine costs  --campaign <id>     # cost-per-email + per-stage (SC-011) — the subscription-vs-API data
```

## Safety notes
- **Detect must stay green.** If `status` shows the detect pass stale or errored, `draft`/`deliver` deliberately stop advancing (never follow up blind). Fix Graph access, re-run `detect`.
- A reply or bounce **permanently halts** that lead — including its manual LinkedIn note (shown cancelled in `status`).
- `deliver` re-checks reply/bounce immediately before each send, so a reply between draft and send cancels the send.
- In `review` mode nothing sends without per-email approval. Default is `review`.

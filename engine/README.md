# Winston Wolf Engine (`ww-engine`)

The outreach campaign engine: a self-running 3-touch email sequence for the
Richbond pilot. Spec: `specs/002-outreach-campaign-engine/`.

Deterministic code owns selection, rotation, idempotency, scheduling, the
per-send marker, and the reply/bounce hard stop. An LLM is used only for
drafting copy, behind the swappable `Drafter` seam (`drafting/base.py`), invoked
headless on the Claude Code subscription — no Anthropic API key.

## Install

```
cd engine && uv sync --dev
uv run ww-engine init        # idempotent migrations on data/leads.db
```

## Operating model

Three idempotent cron passes (depends on `ww-outreach auth` having been run):

```cron
30 2-5 * * *  cd /path/engine && uv run ww-engine draft   --campaign <id> --batch 15
0  *   * * *  cd /path/engine && uv run ww-engine deliver  --campaign <id>
20 *   * * *  cd /path/engine && uv run ww-engine detect   --campaign <id>
```

- **draft** runs off-peak in small batches (subscription trough); stops cleanly
  and resumes next run if the usage cap is hit.
- **deliver** only sends inside the configured US-business-hours window
  (`WW_SEND_TZ`/`WW_SEND_HOUR_START`/`WW_SEND_HOUR_END`); re-checks reply/bounce
  immediately before each send; refuses follow-ups while detect is stale.
- **detect** is the safety pass — a reply or bounce permanently halts that
  lead. If it errors, draft/deliver refuse to advance follow-ups.

Full operator runbook: `specs/002-outreach-campaign-engine/quickstart.md`.

## Modes

A campaign starts in **review** mode — every batch needs per-email approval
(`review` / `approve` / `reject` / `edit` / `approve-all`). `go-autonomous`
flips it to unattended (reversible with `go-review`). Never auto-promotes.

## Tests

```
uv run --dev pytest -q
```

Happy + error path per module (constitution Article 8).

## Diagnose before iterating (constitution Article 12)

If a change fails twice on the same problem, **stop**. Read the structured logs
(stderr JSON) and the `engine_runs` table (`ww-engine status --campaign <id>`)
to find the actual root cause and write a one-line diagnosis before a third
attempt. A `capped`/`error` run row is the first place to look. Slow and correct
beats fast and broken.

## Boundaries

- Lead intake is **out of scope** — a separate tool populates `leads.db`.
- Reuses `ww-core` (data), `ww-outreach` (M365 send/auth) via their public APIs.
- Logs never contain prospect PII (`logging.py` rejects it — Article 3).

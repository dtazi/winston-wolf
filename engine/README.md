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

## Operating model — proof-of-life experiment (004)

The experiment runs **two idempotent cron passes + two manual operator actions**.
Reply detection is MANUAL (no mailbox is ever read — Article 15), so there is **no
`detect` cron pass** here (that was the 002 model). Depends on `ww-outreach auth`
having minted a richbond.ma token on the box.

```cron
# nightly: research → KB-grounded draft + reasoning note → review file (small batches)
30 2-5 * * *  cd /path/engine && uv run ww-engine draft    --campaign <id> --batch 15
# hourly: send approved drafts whose scheduled slot is in the RECIPIENT's local window
0  *   * * *  cd /path/engine && uv run ww-engine deliver   --campaign <id>
# evening: feed new feedback comments → append dated observations to conclusions log
0  20  * * *  cd /path/engine && uv run ww-engine conclude  --campaign <id>
```

- **draft** runs off-peak in small batches (subscription trough); stops cleanly and
  resumes next run if the usage cap is hit. Handles the +7-day follow-up (touch #2)
  internally — no separate pass. Writes a per-draft review file; sends nothing.
- **deliver** runs hourly so it can catch each recipient's local Tue–Thu 10–14 window
  (`WW_SEND_TZ`/`WW_SEND_HOUR_START`/`WW_SEND_HOUR_END` set the per-lead default);
  re-checks the reply hard-stop immediately before each send.
- **conclude** is the learning loop — turns your review comments into dated
  observations the next `draft` pass reads.

**Manual (operator), not cron — the human backstop:**
- `ww-engine review --campaign <id>` — the **morning approval gate**. Nothing sends
  until you `approve`/`edit`/`reject` each draft. This is the safety valve.
- `ww-engine flag-replied --lead <id> [--category …]` — when a prospect replies, you
  flag it; the system halts that lead and voids pending drafts. It never reads the reply.

Ready-to-install crontab: `ops/crontab.example`. Scoreboard any time:
`ww-engine report --campaign <id>` (reply rate vs the ≥5% / 2–5% / <2% verdict rule).

Full operator runbook: `specs/004-proof-of-life-experiment/quickstart.md`.

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

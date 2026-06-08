# Quickstart — Proof-of-Life Experiment (operator runbook)

## Before day one (operator prep — not Claude Code's job)

1. **M365 connection (blocks first send).** Put the Richbond Azure AD app ids in
   `outreach/.env`:
   ```
   AZURE_CLIENT_ID=...
   AZURE_TENANT_ID=...
   ```
   Then authenticate the richbond.ma mailbox:
   ```
   ww-outreach auth      # device-code flow; sign in as the richbond.ma sender
   ```
   Phase 0 found no existing token on this box — this is a first-time auth.

2. **Three inputs** (quality here governs everything downstream):
   - `data/prospects/richbond.yaml` — 30–50 hand-built targets
     (`company, person_name, person_email, country/city, notes`).
   - `data/knowledge/richbond-kb.md` — working-draft KB (seed from
     `data/pitches/richbond.yaml`): what Richbond sells, who buys, buying triggers,
     objections, differentiators. **Only facts/offers here are authorized to appear in
     emails** (Article 17).
   - `data/strategies/*.md` — 3–4 strategy docs to start (seed from
     `specs/002-outreach-campaign-engine/email_playbook.md` / `email_decisions.md` /
     `email_foundation.md`).

3. **Import + tracking config:**
   ```
   export WW_TRACKING_BASE_URL=https://track.richbondgroup.eu
   ww-engine import-prospects data/prospects/richbond.yaml --campaign <id>
   ```

4. **Accept the thresholds in writing** (≥5% validate / 2–5% iterate / <2% kill) and the
   Article 16 primary-domain risk — both recorded in the spec.

## The daily cycle

| When | Who | Command |
|---|---|---|
| 01:00–05:00 | WW (cron) | `ww-engine draft --campaign <id>` → research, strategy, draft, reasoning note, review files |
| morning (~30–60 min) | You | `ww-engine review --campaign <id>` → read each draft + reasoning + research; `--verdict approve\|edit\|reject [--comment …]` |
| mid-day, Tue–Thu | WW (cron) | `ww-engine deliver --campaign <id>` → sends approved drafts in each recipient's local 10am–2pm |
| on a reply | You | `ww-engine flag-replied --lead <id> --category …` (suppresses; never reads the reply) |
| after feedback | WW | `ww-engine conclude --campaign <id>` → updates the conclusions log |
| anytime | You | `ww-engine report --campaign <id>` → reply rate vs thresholds |

Follow-ups: 7 days after touch #1, non-replied prospects get one engagement-shaped
follow-up (clicked → stronger; opened → nudge; silent → new angle), reviewed like any draft.

## Volume ramp
Week 1: 3–5/day → Week 4: ~10–15/day. Sends only Tue–Thu. ~55–95 sends over the month.

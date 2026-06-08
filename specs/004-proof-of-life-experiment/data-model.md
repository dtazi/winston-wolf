# Data Model — Proof-of-Life Experiment

Deltas only. Base schema = `ww-core/schema.sql` + `ww-engine/schema_engine.sql`.
SQLite has no `ADD COLUMN IF NOT EXISTS`; new columns are applied conditionally by
`db.py` (the existing migration pattern).

## Schema deltas

### `campaigns` (config for sequencing)
| Column | Type | Default | Purpose |
|---|---|---|---|
| `max_touches` | INTEGER | 2 | Pilot touch cap (was hardcoded 3 in `selection.py`) |
| `touch_gap_days` | INTEGER | 7 | Follow-up spacing (was hardcoded 14) |
| `send_tz_default` | TEXT | `'America/New_York'` | Fallback when a prospect's tz is unknown |

### `leads` (prospect annotations)
| Column | Type | Default | Purpose |
|---|---|---|---|
| `send_timezone` | TEXT | NULL | IANA tz for the per-recipient send window (D2); NULL → campaign default |

### `send_drafts` (feedback capture)
| Column | Type | Default | Purpose |
|---|---|---|---|
| `comment` | TEXT | NULL | Operator's free-text verdict comment (FR-010) |
| `reply_category` | — | — | *not here* — lives on the `replied` event payload (D4) |

The verdict itself reuses the existing `review_state`
(`pending`/`approved`/`edited`/`rejected`/`delivered`) — no new column. "edit" = the
existing `edited` state with `body_text` replaced (`modes.set_review_state`).

The strategy/reasoning note rides in the existing `send_drafts.message_recipe` (TEXT JSON)
— no new column. Shape:
```json
{
  "strategies": ["trigger-opener", "sub-80-words"],
  "why": "Prospect announced a new factory (research §2); trigger-opener fits.",
  "how_applied": "Opened on the factory news; tied to Richbond lead-time advantage.",
  "claims": [
    {"text": "12-week lead time", "source": "kb#lead-times", "grounded": true},
    {"text": "free sample", "source": null, "grounded": false}
  ],
  "engagement_tier": "clicked"
}
```
`grounded:false` claims are the Article 17 flags surfaced at approval.

## Engagement tier query (D5)
For a lead, since its first `sent` event:
```sql
-- clicked > opened > silent
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM events WHERE lead_id=? AND event_type='clicked') THEN 'clicked'
  WHEN EXISTS (SELECT 1 FROM events WHERE lead_id=? AND event_type='opened')  THEN 'opened'
  ELSE 'silent' END;
```
Tier **shapes** the follow-up; it is never an eligibility gate (FR-016b).

## Selection deltas (`selection.py`)
- `MAX_TOUCHES` / `TOUCH_GAP_DAYS` → read from the campaign row (D3).
- Eligibility otherwise unchanged: enrolled + `active` + `current_touch < max_touches` +
  no `replied`/`bounced` event + gap elapsed. The hard-stop `NOT EXISTS replied/bounced`
  already makes the manual flag (D4) suppress correctly.

## Tracking integration (D10)
- `sends.pixel_token` already exists. Sender emits the pixel at `{base}/p/<token>.gif`
  (fixes the `/pixel/` mismatch).
- Per body URL: insert `tracked_links(id, send_id, lead_id, original_url)` and rewrite the
  link to `{base}/c/<id>`. The tracker's `/p` and `/c` routes already append
  `opened`/`clicked` events.

## Review file (feedback interface, D1)
One markdown file per nightly draft under `data/reviews/<date>/<draft-id>.md`:
email (subject/body) + reasoning note (rendered from `message_recipe`) + research summary
+ engagement tier (follow-ups) + a `Verdict:` and `Comment:` field. `ww-engine review`
reads the verdict/comment back and applies it via `modes.set_review_state` (+ `comment`).

## New entities (file-based, operator-maintained)
- `data/knowledge/richbond-kb.md` — grounded facts/offers (Article 17 source of truth).
- `data/strategies/*.md` — one strategy per file; the writer's menu.
- `data/conclusions/richbond.md` — system-appended dated observations.
- `data/prospects/richbond.yaml` — intake list (D8).

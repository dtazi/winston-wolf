"""The feedback interface (D1): one markdown review file per draft.

Each nightly draft is rendered to data/reviews/<date>/<draft-id>.md so the
operator reads the email, the strategy/reasoning note, and the research summary
together, then records a verdict + comment via the `review` CLI. The reasoning
note (from the draft's message_recipe) is what makes the approval gate
meaningful — the operator approves the judgment, not just the prose.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .knowledge import data_dir
from .research import ResearchResult


def reviews_dir(date: str | None = None) -> Path:
    day = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return data_dir() / "reviews" / day


def _render_note(recipe: dict) -> str:
    lines = []
    strategies = recipe.get("strategies") or []
    if strategies:
        lines.append(f"**Strategies:** {', '.join(strategies)}")
    if recipe.get("why"):
        lines.append(f"**Why for this prospect:** {recipe['why']}")
    if recipe.get("how_applied"):
        lines.append(f"**How applied:** {recipe['how_applied']}")
    if recipe.get("engagement_tier"):
        lines.append(f"**Engagement tier:** {recipe['engagement_tier']}")
    claims = recipe.get("claims") or []
    if claims:
        lines.append("\n**Claims:**")
        for c in claims:
            mark = "✓" if c.get("grounded") else "⚠ UNSOURCED"
            src = c.get("source") or "—"
            lines.append(f"- [{mark}] {c.get('text','')}  _(source: {src})_")
    return "\n".join(lines) or "_(no reasoning note)_"


def render_review(draft: sqlite3.Row, research: ResearchResult | None = None) -> str:
    try:
        recipe = json.loads(draft["message_recipe"] or "{}")
    except (json.JSONDecodeError, TypeError):
        recipe = {}
    research = research or ResearchResult()
    flag = ""
    unsourced = [c for c in (recipe.get("claims") or []) if not c.get("grounded")]
    if unsourced:
        flag = f"  ⚠ {len(unsourced)} UNSOURCED CLAIM(S) — Article 17"

    return f"""# Draft {draft['id']} — touch {draft['touch_number']}{flag}

**Lead:** {draft['lead_id']}

## Email
**Subject:** {draft['subject']}

{draft['body_text']}

## Reasoning note
{_render_note(recipe)}

## Research summary
{research.summary or "_(thin — no research)_"}

_confidence: {research.confidence}_

---
## Verdict: [ approve | edit | reject ]
## Comment:

"""


def write_review_file(draft: sqlite3.Row,
                      research: ResearchResult | None = None,
                      date: str | None = None) -> Path:
    d = reviews_dir(date)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{draft['id']}.md"
    p.write_text(render_review(draft, research), encoding="utf-8")
    return p

"""Offline smoke: produce ONE real Richbond email from the live KB + strategies.

Proves the riskiest part of the machine — that grounding yields sane copy — WITHOUT
needing live web research or an M365 token. Uses the real ClaudeCodeDrafter (the
`claude` CLI on the box, subscription), a real prospect, and a CANNED research summary
so nothing external is called.

Run:  cd engine && uv run python ops/smoke_draft.py
"""
from __future__ import annotations

import dataclasses
import json

from ww_engine import knowledge
from ww_engine.drafting.base import DraftRequest, violates_named_account_guard
from ww_engine.drafting.grounded import GroundedClaudeDrafter
from ww_engine.drafting import personalization
from ww_engine.research import ResearchResult

# --- a realistic dummy prospect: a hospitality FF&E purchasing agent ---
LEAD = {
    "id": "smoke-1",
    "company": "Benjamin West",
    "person_first_name": "Jordan",
    "person_last_name": "Avery",
    "person_email": "jordan.avery@example.com",
    "person_title": "Procurement Manager",
    "country": "US",
    "city": "Denver",
    "send_timezone": "America/Denver",
    "current_touch": 0,
}
LEAD["person_name"] = f'{LEAD["person_first_name"]} {LEAD["person_last_name"]}'

# --- canned research (what research.py would have produced; keeps this offline) ---
RESEARCH = ResearchResult(
    summary=("Benjamin West is a leading global hospitality FF&E procurement firm that "
             "buys furnishings — including mattresses — on hotel owners' behalf. Active "
             "across new-build and PIP-driven refresh projects for major brands."),
    signals=[
        {"type": "segment", "value": "hospitality FF&E purchasing agent"},
        {"type": "pain", "value": "lead-time variance and tariff exposure on imported bedding"},
        {"type": "trigger", "value": "brand PIP refresh cycles every ~6-7 years"},
    ],
    send_timezone="America/Denver",
    confidence="medium",
    sources=["https://www.beyerbrown.com/ffe-procurement-comprehensive-guide/"],
)


def main() -> None:
    kb = knowledge.load_kb("richbond")
    strategies = knowledge.load_strategies()
    assert kb, "KB missing — data/knowledge/richbond-kb.md"
    assert strategies, "no strategies — data/strategies/*.md"
    print(f"[setup] KB {len(kb)} chars · strategies: {[s['name'] for s in strategies]}\n")

    pers = personalization.gather(LEAD)
    req = DraftRequest(
        lead=LEAD, pitch={}, brief_excerpt={}, value_angle="grounded",
        touch_number=1, personalization=pers,
        knowledge_base=kb, strategies=strategies,
        research=dataclasses.asdict(RESEARCH), conclusions="", feedback=[],
        engagement_tier="",
    )

    print("[draft] invoking GroundedClaudeDrafter (claude CLI, subscription)…\n")
    result = GroundedClaudeDrafter().draft(req)

    recipe = result.message_recipe or {}
    print("=" * 70)
    print(f"SUBJECT: {result.subject}")
    print("-" * 70)
    print(result.body_text)
    print("=" * 70)
    print(f"\nwords: {len(result.body_text.split())}")
    print(f"named-account-guard violated: {violates_named_account_guard(result.body_text)}")
    print(f"strategies chosen: {recipe.get('strategies')}")
    print(f"why: {recipe.get('why')}")
    claims = recipe.get("claims", [])
    print(f"\nclaims ({len(claims)}):")
    for c in claims:
        flag = "GROUNDED" if c.get("grounded") else "*** UNGROUNDED ***"
        print(f"  [{flag}] {c.get('text','')}  <- {c.get('source','')}")
    print("\n[full recipe]\n" + json.dumps(recipe, indent=2)[:1500])


if __name__ == "__main__":
    main()

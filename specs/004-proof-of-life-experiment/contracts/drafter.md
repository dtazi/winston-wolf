# Contract — KB-grounded Drafter (D6)

The `Drafter` Protocol seam (`drafting/base.py`) is **unchanged**. Only the Claude-Code
implementation's inputs and the `DraftResult.message_recipe` payload are extended. Swapping
to an API drafter later still satisfies this contract.

## Inputs (extends `DraftRequest`)
The drafter is given, in addition to the existing `lead`/`touch_number`/`personalization`:
- **knowledge base** — `data/knowledge/richbond-kb.md` (the only authorized source of
  facts/offers, Article 17).
- **strategy library** — `data/strategies/*.md`; the drafter selects 1+ grounded in the
  research.
- **research summary** — structured output from `research.py` (see research.md).
- **conclusions** — `data/conclusions/richbond.md` (what's working so far).
- **prior feedback** — recent `send_drafts.comment` values for this campaign.
- **engagement_tier** — `clicked`/`opened`/`silent` (touch #2 only); shapes angle.

## Behavior
- Choose one or more strategies from the library, justified by the research.
- Every factual claim or offer MUST cite a KB anchor. Unsourced/low-confidence claims are
  emitted with `grounded:false` (flagged at approval) — never silently asserted (Art 17).
- Respect the named-account guard (`violates_named_account_guard`, e.g. IKEA).
- Keep copy within the strategy library's stated norms (e.g. sub-80-words if chosen).

## Output (`DraftResult`)
- `subject`, `body_text` — as today.
- `message_recipe` (JSON) — now carries the **strategy/reasoning note** (shape in
  data-model.md): `strategies`, `why`, `how_applied`, `claims[]` (with `source`/`grounded`),
  `engagement_tier`.
- `token_usage` — unchanged (per-stage cost, Article 4).

## Failure
- `DraftError` per lead (caught at boundary; the review file flags thin/failed research).
- `DrafterCapReached` → run records `capped`, resumes next pass (existing behavior).

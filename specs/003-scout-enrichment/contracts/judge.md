# Contract — AI fit judge (`qualification/judge.py`)

The second qualification layer (FR-005). Runs **only on leads that passed the
rules layer**. Calls `ww_llm.registry.engine_for("scout")` — so the engine is
whatever the engine room assigns to Scout (default: Claude subscription).

## Input (assembled in code — fixed shape, Article 4)

- The campaign ICP: `target_roles`, `niche_id`, `size_metric`/`size_min`,
  `regions`, and the plain-language `description`.
- The one lead's gathered facts only: `company_name`, `company_region`, size
  value if known, `company_domain`, contact `title`, and a short website snippet
  if discovered. **No whole-DB dump; no other leads.**

## Output (forced JSON via `response_schema`)

```json
{
  "score": 0-100,
  "confidence": "low" | "medium" | "high",
  "reason": "2-3 sentences citing the specific facts used"
}
```

## Behavior

- The prompt instructs the model to judge fit against the ICP and to **cite the
  facts** it used (grounding — guards against invention; spec edge case).
- `confidence: "low"` → the lead's verdict becomes `needs_review` rather than
  auto-qualified/rejected (spec edge case: AI not confident → human decides).
- A score ≥ the (configurable, code-constant) qualify threshold → `qualified`;
  below → `rejected`. Threshold documented and tunable.
- `Usage` is written to `enrichment_ledger` (stage `judge`), tagged with the
  engine name, regardless of which engine served it.
- Engine outage → typed error → lead `parked`, batch continues (Article 11).
- Optional reflection (`reflection.py`, FR-012): when enabled, a second
  `complete()` call asks the model to critique and, if needed, revise its own
  verdict; both are recorded and `reflection_applied=1`.

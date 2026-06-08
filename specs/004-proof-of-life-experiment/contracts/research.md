# Contract — Research module (`research.py`, D7)

Per-prospect research feeding the drafter and the per-recipient send window. Deterministic
plumbing in code; `ww-llm` only for synthesis (Article 4). Bounded for cost.

## Input
A `leads` row (company, person, email, any operator notes).

## Sources (bounded)
- Web search (a small fixed number of queries: company + person + recent news).
- Company website fetch.
- Recent news.
- LinkedIn where feasible (best-effort; not a hard dependency).

## Output (structured, stored on the lead + surfaced at approval)
```json
{
  "summary": "2-4 paragraph synthesis the operator reads at approval",
  "signals": [{"type": "expansion", "detail": "announced new factory", "source_url": "…"}],
  "send_timezone": "America/Chicago",
  "confidence": "high|medium|thin",
  "sources": ["url", "url"]
}
```
- `signals` are the triggers the drafter grounds the opener in (the thesis: signal-driven).
- `send_timezone` is the IANA tz derived from company HQ location (D2); NULL/absent →
  campaign `send_tz_default`.
- `confidence:"thin"` tells the drafter to flag weak grounding and the operator to expect
  a weaker draft (edge case in spec).

## Storage
Research summary persisted (lead annotation or a `research` payload) so the review file and
the drafter both read the same artifact; not re-run per pass.

## Boundaries
No prospect data logged in plaintext (Article 3). No reply/inbox access (Article 15). No
lead acquisition — researches only the operator-provided list (FR-001).

# Contract — Drafter seam (FR-015)

The single replaceable boundary between the engine and *how copy is generated*. Sequencing, sending, detection, modes, and cost accounting depend ONLY on this contract — never on Claude Code specifics. Swapping `ClaudeCodeDrafter` → `ApiDrafter` later changes nothing else.

## Interface

```python
class Drafter(Protocol):
    def draft(self, req: "DraftRequest") -> "DraftResult": ...
```

### `DraftRequest` (in)
| field | type | source |
|---|---|---|
| `lead` | dict | `leads` row: company/role/person/site/linkedin context (no other tenants) |
| `pitch` | dict | customer pitch YAML (via `ww-core`) |
| `brief_excerpt` | dict | the lead's niche block from the campaign brief (via `ww-core`) |
| `value_angle` | str | one of `china_plus_one` / `60_years_experience` / `trusted_by_heavyweights` |
| `touch_number` | int | 1–3 |
| `personalization` | dict | `{level: dataset|site|web|linkedin|thin, facts: [...]}` from `personalization.py` |

### `DraftResult` (out)
| field | type | rule |
|---|---|---|
| `subject` | str | non-empty |
| `body_text` | str | non-empty; expresses exactly `value_angle`; MUST NOT name/hint any reference account incl. IKEA (FR-014) — validated by code post-generation, draft rejected to `thin`/flagged if violated |
| `message_recipe` | dict | ≥ `{angle, touch, rotation_group, personalization_level, drafter}` |
| `token_usage` | list[dict] | `[{stage, model, input_tokens, output_tokens}]` → `token_ledger` (FR-026) |

## Guarantees

- **Deterministic envelope, probabilistic content**: the engine treats `draft()` as pure I/O; all selection/scheduling/stop logic is outside it (Article 4/5).
- **No side effects**: `draft()` does not write the DB or send mail; the caller persists `send_drafts` and ledgers tokens.
- **Failure**: raises `DraftError` (caught at module boundary → `engine_runs`, Article 11); a subscription cap raises `DrafterCapReached` → run marked `capped`, no partial draft persisted.
- **FR-013 compliance is code-enforced**: the IKEA/named-account guard is a deterministic post-check on `body_text`, not left to the model.

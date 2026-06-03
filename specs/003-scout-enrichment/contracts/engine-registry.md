# Contract — `ww-llm` Engine Protocol + registry

The shared "engine room". Lives in the new `llm/` module
(`scout` depends on `ww-llm`). Delivers per-tool engine selection (FR-013/014/015).

```python
@dataclass
class CompletionRequest:
    system: str | None
    prompt: str
    response_schema: dict | None   # when set, engine must return JSON matching it
    max_tokens: int                # explicit budget (Article 4 — no unbounded calls)
    temperature: float = 0.0

@dataclass
class Usage:
    tokens_in: int
    tokens_out: int
    cost_usd: float | None         # None for the subscription engine (no per-call $)

@dataclass
class CompletionResult:
    text: str
    json: dict | None              # parsed when response_schema was given
    usage: Usage
    engine: str                    # which engine served it (for the ledger/audit)

class Engine(Protocol):
    name: str
    def complete(self, req: CompletionRequest) -> CompletionResult: ...
```

## Registry resolution (`ww_llm.registry`)

```python
def engine_for(tool: str) -> Engine: ...   # tools[tool] or default; raises if engine undefined
```

- Config loaded from `config/engines.yaml` (or `WW_ENGINES_FILE`). Shape per
  data-model.md. `default` is mandatory and is `claude_subscription`.
- A tool with no explicit mapping resolves to `default` (FR-013) — nothing breaks
  when unconfigured.
- Each engine's credentials come from the env var **named** in config
  (`api_key_env`); the registry refuses to start an API engine whose env var is
  unset (fail-loud), but the subscription engine needs no key.

## Engines shipped in v1

| name | type | how it calls | key |
|---|---|---|---|
| `claude_subscription` (DEFAULT) | subprocess | headless `claude -p --output-format json` (reuses 002 pattern); usage parsed from CLI JSON, `cost_usd=None` | `CLAUDE_CODE_OAUTH_TOKEN` (already in env) |
| `anthropic_api` | HTTP | Anthropic Messages API via `httpx` | `ANTHROPIC_API_KEY` |
| `openai` | HTTP | OpenAI Chat Completions via `httpx` | `OPENAI_API_KEY` |
| `deepseek` | HTTP | DeepSeek (OpenAI-compatible) via `httpx` | `DEEPSEEK_API_KEY` |

## Rules of the seam
- Every call has an explicit `max_tokens` and a fixed `prompt` shape — never a
  whole-DB dump (Article 4).
- `Usage` from every call is written to `enrichment_ledger` by the caller, so cost
  is tracked identically across engines.
- An engine outage raises a typed `EngineError`; the caller parks the lead
  (Article 11). The registry/engines are independent of the Zeno sidecar router.

# Topic 06 — LLM orchestration

**Status**: Phase 1 stub. Lighter touch than the previous topics — more about ergonomics than foundational understanding. Final topic in Phase 1 landscape mapping.

## Why this matters for Winston Wolf

Topics 01–05 covered *what* the system does (search, retrieve, agent loops, RAG, contact discovery). This topic covers *how the LLM calls themselves are wired up* — provider abstraction, retries, fallback, caching, multi-LLM routing.

You've already decided (per memory) on a multi-LLM router architecture: tasks get routed to specific providers/models (research → one model, writing → another, fast classification → a third). This topic clarifies what that actually means in code, what libraries help, and what to avoid.

---

## 6.1 What "orchestration" actually covers

Loose term, but in practice these layers stack on top of each other:

```
┌────────────────────────────────────────────┐
│ 4. Application logic (Scout, Outreach, …)  │
├────────────────────────────────────────────┤
│ 3. Patterns (RAG, agents, chains)          │
├────────────────────────────────────────────┤
│ 2. Cross-cutting (retry, fallback, caching,│
│    observability, cost tracking)           │
├────────────────────────────────────────────┤
│ 1. Provider abstraction (one API for many  │
│    LLM providers)                          │
└────────────────────────────────────────────┘
```

Different libraries cover different layers. Some try to cover the whole stack; some are narrowly focused. The trade-off is between **convenience** (full-stack libraries do more for you) and **control** (narrow libraries don't lock you in).

**General rule:** the wider a library's scope, the more likely you'll regret it in production. LangChain is the canonical example — great for prototyping, frequently torn out and replaced once teams hit edge cases.

---

## 6.2 Layer 1 — Provider abstraction

The "one API for many LLMs" layer. Winston Wolf needs this because of the multi-LLM router decision.

| Tool | What it does | Notes |
|---|---|---|
| **LiteLLM** | Open-source proxy + Python library. Unified API across ~100 providers (Anthropic, OpenAI, Google, Cohere, local models, …). | The default choice. Battle-tested. Solid. |
| **OpenRouter** | Hosted service. Like LiteLLM but as someone else's infrastructure; you pay them a small markup. | Useful if you don't want to manage anything; locks you into their pricing/availability. |
| **AISuite** (Andrew Ng's project) | Lightweight unified-API library | Newer; less mature than LiteLLM. |
| **Custom dispatcher** | Write your own thin abstraction | More control, more code. Reasonable for narrow needs. |

For Winston Wolf: **LiteLLM as a Python library** (not the proxy server). You write `litellm.completion(model="anthropic/claude-sonnet-4-6", messages=...)` and it handles the differences. Comes with retry, fallback, cost tracking baked in.

If LiteLLM ever starts dragging (it can be opinionated), swapping to a custom dispatcher is a one-day refactor — the unified-API surface is simple enough.

---

## 6.3 Layer 2 — Cross-cutting concerns

These are the "every call needs this" capabilities:

### Retry / fallback

When a model is rate-limited, errored, or slow, you want to retry — and if that fails, fall back to a different model. LiteLLM has built-in retry and fallback config:

```python
litellm.completion(
    model="anthropic/claude-sonnet-4-6",
    fallbacks=["openai/gpt-4o", "anthropic/claude-haiku-4-5"],
    num_retries=3,
)
```

Don't roll your own — this is solved.

### Caching

Two distinct kinds:

- **Provider-side prompt caching** (Anthropic 5-min default TTL): the API caches a portion of your prompt. Cheap inputs on cache hits. Critical for agents and RAG.
- **Application-side response caching**: storing entire LLM responses for identical inputs. Useful for deterministic queries; not for creative ones.

LiteLLM supports both. Anthropic's prompt caching is configured at request time via cache markers in the message structure.

### Observability

Without observability, debugging an agent is impossible. You need to see:
- Every LLM call (input, output, cost, latency)
- Tool calls (name, arguments, result)
- Errors and retries
- Aggregate cost over time

| Tool | Notes |
|---|---|
| **Langfuse** | Open source; self-hostable. Strong default. |
| **LangSmith** | Hosted (LangChain's). Good UX; tied to LangChain ecosystem. |
| **Helicone** | Hosted proxy. Easy integration. |
| **Custom logging** | Write structured logs to disk / Postgres. Most control, least pretty. |

For Winston Wolf v1: probably **Langfuse self-hosted on the old Mac**, OR custom structured logging to a Postgres table. The custom-logging path is simpler if observability needs are basic; Langfuse is worth the setup once we're running enough agents to need a UI.

### Cost tracking

Per-call cost is computed from input/output token counts × model pricing. LiteLLM tracks this automatically. Aggregating to per-tenant / per-task spending requires application-level grouping.

For Winston Wolf, this matters because of the constitution's Article 4 (AI cost awareness). Logging cost per call into Postgres alongside the action log entries (Article 10) is the right pattern.

### Concurrency / batching

Async / parallel execution of LLM calls when independent. LiteLLM supports `acompletion` (async) directly. For multi-step agents this matters; for batch jobs even more so.

---

## 6.4 Layer 3 — Patterns: full-stack frameworks

Frameworks that try to cover orchestration + RAG + agents + sometimes UI.

| Framework | Strength | Weakness |
|---|---|---|
| **LangChain** | Comprehensive; tons of integrations; many examples | Frequently regretted in production; unstable APIs; hides too much. Heavy abstraction tax. |
| **LlamaIndex** | RAG-focused; strong for retrieval pipelines | Less general; opinionated about data flow. |
| **Haystack** | Production-oriented NLP framework | Heavy; more for traditional NLP than agent loops. |
| **Semantic Kernel** (Microsoft) | C#/Python, Microsoft-aligned | Weak fit for non-Microsoft stacks. |
| **DSPy** | "Programming, not prompting" — focuses on optimisation | Newer paradigm; powerful but complex. |
| **No framework** | Just LiteLLM + your own code | Most control. Recommended for production-grade core code. |

**For Winston Wolf:** mostly skip framework lock-in. Use LiteLLM at Layer 1, write Layers 2–3 as small focused modules. Borrow ideas from LangChain/LlamaIndex docs without importing their packages.

The exception worth flagging: **LlamaIndex for the Knowledge Base ingestion pipeline** specifically. It has good document loaders, chunkers, and metadata management. Worth evaluating in Phase 2 against just writing it ourselves.

---

## 6.5 Multi-LLM routing — the explicit decision

Per memory: Winston Wolf will route different tasks to different LLM providers/models. This is configuration-driven, not hardcoded.

**Routing config sketch (conceptual):**

```yaml
routes:
  scout_research:           # heavy reasoning, multi-step
    model: anthropic/claude-sonnet-4-6
    fallback: anthropic/claude-haiku-4-5
  outreach_email_writing:   # creative, nuanced
    model: anthropic/claude-opus-4-7
    fallback: anthropic/claude-sonnet-4-6
  fast_classification:      # cheap, high-volume
    model: anthropic/claude-haiku-4-5
    fallback: openai/gpt-4o-mini
  reranking:                # specialised
    model: anthropic/claude-haiku-4-5
```

The router is a small function that takes a task name + a prompt and returns the LLM response, dispatching to the configured provider. Trivial to write (~30 lines).

**Why this matters for cost:**
- Scout might use Sonnet ($3/1M input, $15/1M output) for reasoning; Outreach might use Opus ($15/$75) for final draft quality; classification calls use Haiku ($0.80/$4) at 90% lower cost.
- A naive single-model architecture either pays Opus prices for everything (wasteful) or Haiku prices for everything (under-quality on the hard tasks).

**Admin-configurability:** the user wants admins to add/remap models. The simplest model is a config table in Postgres + a UI for editing it (much later — Phase 3+ feature). For now, a YAML file is fine.

---

## 6.6 Build vs. buy in this layer

For each layer, the right call:

| Layer | Build or buy? |
|---|---|
| Provider abstraction | **Buy** — use LiteLLM. Don't reinvent. |
| Retry / fallback | **Buy** — LiteLLM has it. |
| Prompt caching | **Buy** — Anthropic's native cache. |
| Response caching | **Build** — small (one Postgres table); narrowly tuned to needs. |
| Observability | **Hybrid** — start with custom logging to Postgres; add Langfuse if needed. |
| Cost tracking | **Build** — small (LiteLLM gives you the numbers; you store them). |
| Multi-LLM routing | **Build** — ~30 lines; trivial. |
| RAG / agent patterns | **Build** — keep control, avoid framework drag. |

The pattern: **buy the boring infrastructure; build the application logic.**

---

## 6.7 Open questions for Winston Wolf

- **LiteLLM library vs. proxy server?** Library is simpler; proxy server adds value if multiple services share LLM access. v1: library.
- **Where does cost tracking live?** Same Postgres as action log? Separate table? Phase 2 architectural call.
- **Per-tenant LLM API keys** vs. **platform-side keys**? If Winston Wolf eats LLM costs, single platform key. If customers BYO their own, per-tenant keys with secure storage. Initial assumption: platform-side, will revisit.
- **Anthropic prompt caching pattern.** Cache the system prompt, tool definitions, and Knowledge Base context separately. Needs careful integration in the router.
- **Local model fallback?** If the platform runs on the old Mac, an Ollama-hosted local model could be a $0 fallback. Worth Phase 2 testing.

---

## 6.8 References for Phase 2

- LiteLLM docs — particularly the routing, retry, and caching sections.
- Anthropic prompt-caching docs (recently expanded).
- Langfuse self-hosted setup guide.
- *"DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines"* (Khattab et al.) — for the "programming, not prompting" idea.
- Hamel Husain's blog posts on LLM observability and evaluation patterns (consistently strong).
- Anthropic Cookbook examples on tool use + prompt caching together.
- Postgres schema design for LLM action logs (Articles 4 + 10 of the constitution).

---

## End of Phase 1 landscape mapping

With topics 01–06 drafted, we have basic orientation across the territory: how search works (algorithm + index + ranking), how to drive an LLM through tools, how to retrieve from a Knowledge Base, where B2B contact data really comes from, and how to wire the LLM calls.

Phase 2 (hands-on prototypes) is where each of these turns from "I read about it" into "I've built a 100-line version of it." That's where understanding actually lands.

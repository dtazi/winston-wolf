# Topic 03 — Agent loops, tool use, multi-step research

**Status**: Phase 1 stub. The most directly Winston-Wolf-relevant topic in landscape mapping — Scout will likely *be* an agent.

## Why this matters for Winston Wolf

Topics 01 and 02 covered how raw search works — algorithms and indexes. Topic 03 covers how an **LLM-driven agent** turns those raw search capabilities into actual answers like *"here are 10 likely decision-makers at Richbond Group with their roles and emails."*

When Scout runs, it almost certainly won't be a single search call. It'll be a loop: search → read results → search again with refined queries → cross-reference → look up emails → synthesise. Each step uses an LLM to decide what to do next based on what's been found so far. **Designing this loop well is most of the engineering challenge in lead discovery.** Get it right and Scout is intelligent and adaptive; get it wrong and Scout is expensive, slow, and wrong.

---

## 3.1 The basic agent loop

The canonical pattern (sometimes called **ReAct** — Reason + Act):

```
while not done:
    1. LLM thinks about what's needed next
    2. LLM picks a tool to call (search, fetch URL, lookup email, etc.)
    3. Tool runs, returns result
    4. LLM observes the result
    5. LLM decides: am I done, or do I need another step?
```

Each iteration adds the previous step's output to the LLM's context, so by step 5 the LLM has seen everything that's happened so far.

Concrete Scout example:
- Step 1: search "Richbond Group senior leadership Morocco"
- Step 2: read the company About page from results
- Step 3: search "Richbond Group LinkedIn employees"
- Step 4: cross-reference names found
- Step 5: for each likely person, run an email-finder
- Step 6: return structured list

Six steps, six (or more) tool calls, ~1 LLM call per step plus the final answer. That's an agent in action.

---

## 3.2 Tool use / function calling

Tools are how the LLM interacts with the outside world. In the Anthropic and OpenAI APIs, tools are defined as JSON schemas:

```json
{
  "name": "search_web",
  "description": "Search the web for a query, returns top 10 results",
  "input_schema": {
    "query": "string",
    "max_results": "integer"
  }
}
```

The LLM, given a user question and a list of available tools, can:
- Call a tool with arguments (a "tool call" message)
- Read the result (a "tool result" message)
- Decide what to do next, based on the result

**Modern LLM APIs handle the loop natively.** You pass a list of tools, the LLM picks which one to call, you execute, return the result, the loop continues until the LLM says "I'm done." The Claude Agent SDK (which the Telegram bot will use) handles this loop automatically.

**What makes tool use work or fail:**

- **Tool descriptions matter immensely.** A tool described as "searches the web" gets used differently than "searches the web for technical documentation; not for general questions." Description quality is half the battle.
- **Schema clarity matters.** Optional vs required parameters, sensible defaults, clear parameter names.
- **Result formatting matters.** Tool results that are huge dumps of HTML are harder for the LLM to reason about than clean structured JSON.

---

## 3.3 Common patterns beyond simple ReAct

### Plan-and-Execute

Instead of stepping reactively, the LLM first writes a **plan** ("Step 1: search for company exec listing. Step 2: look up each name on LinkedIn. Step 3: find emails."), then executes the plan step by step. Pros: clearer reasoning, easier to debug, can be checkpointed. Cons: rigid — if step 2 returns nothing, the plan is now broken and the agent has to replan.

### Multi-step retrieval (RAG-style agent)

The agent's loop is specifically: search → for each promising result, fetch and read it → synthesise. Not really general agent territory — more a constrained loop. Useful when the task is "find evidence about X."

### Self-correction / reflection

After producing a draft answer, the LLM critiques its own output ("did I find the right number of leads? did I verify their roles?") and can re-loop if the critique surfaces issues. Costs more tokens but improves quality, especially for high-stakes tasks.

### Hierarchical agents

A "manager" agent breaks a task into subtasks and delegates each to a "worker" agent (or to itself recursively). Good for complex tasks; bad for cost predictability.

For Winston Wolf's first Scout MVP: **simple ReAct with 3–6 tools (search, fetch URL, find email, possibly an LLM-rerank tool) is probably enough.** The fancier patterns are Phase 2 territory if needed.

---

## 3.4 Failure modes

This is where most agent projects bleed value. The common failure modes:

| Failure mode | What happens | Mitigation |
|---|---|---|
| **Infinite loop** | Agent keeps calling the same tool with similar args | Hard cap on iterations (e.g., 10 steps max) |
| **Hallucinated tool call** | Agent calls a tool that doesn't exist or with invalid args | Schema validation + clear error messages back to the LLM |
| **Off-task drift** | Agent goes down a tangent unrelated to the task | Periodic "are we still on task?" prompt; clearer system prompt |
| **Context exhaustion** | Tool results pile up, agent context fills, quality degrades | Trim/summarise old tool results in long loops |
| **Cost runaway** | Each step costs tokens; complex tasks can run 50+ steps | Token budget per task + alerts |
| **Hallucinated facts** | Agent fabricates names, emails, roles when search returns thin results | Require citation + verification step + low-confidence flag |
| **Wrong tool chosen** | Agent uses a search tool when it should fetch a known URL | Better tool descriptions + few-shot examples in system prompt |
| **Premature termination** | Agent stops before fully answering | Better task framing in user prompt; explicit completion criteria |

For Winston Wolf, **hallucinated facts is the single biggest risk.** A Scout agent that confidently makes up emails or roles will destroy customer trust faster than any other failure. Mitigation has to be designed in from day 1: every claim must be tied to a source (URL, database record), and "I couldn't find this with confidence" must be an acceptable output.

---

## 3.5 Frameworks and libraries

| Framework | What it is | When to use / avoid |
|---|---|---|
| **Claude Agent SDK** | Anthropic's official SDK for building agents (Python/TS) | Default for Anthropic-first projects. Handles loop, tools, sessions. |
| **LangChain** | Large general-purpose LLM framework | Good for prototyping, often regretted in production. Too many abstractions, breaks frequently. |
| **LlamaIndex** | RAG-focused framework | Good for retrieval-heavy use cases. Less directly applicable to agent loops. |
| **OpenAI Assistants API** | OpenAI's agent abstraction | OpenAI-specific. Reasonable but locks you in. |
| **Haystack** | Open-source NLP pipeline framework | Heavier; more for production search systems than quick agents. |
| **Custom (just the API + a loop)** | ~100 lines of Python | Most control, no framework lock-in. Good for understanding what's happening. |

For Winston Wolf: **Claude Agent SDK for the bot itself** (already decided), and almost certainly **a custom thin agent loop for Scout** to maintain understanding and avoid framework drag.

---

## 3.6 Cost dynamics

A single Scout query might involve:
- 5–10 LLM calls (one per agent step, plus reflection)
- 5–10 tool calls (search, fetch, rerank, email lookup)

At Claude Sonnet pricing (~$3/million input tokens, ~$15/million output tokens), a single Scout query with ~30k input tokens and ~5k output tokens costs ~$0.17. At 100 queries/day that's $17/day or ~$500/month. Manageable for a single tenant; needs careful monitoring at scale.

**Caching matters.** Anthropic's prompt caching (5-min TTL by default) can cut input-token costs by ~90% for cached portions. If the agent's system prompt and tool definitions are cached, only the per-query content gets billed at full rate. Worth implementing from day 1 in Scout.

---

## 3.7 Open questions for Winston Wolf

- **Which LLM for Scout's main reasoning loop?** Claude Sonnet is probably the sweet spot (good tool-use, fast, ~half the cost of Opus). To verify in Phase 2.
- **Step budget per Scout query.** 5? 10? 20? Trade-off between thoroughness and cost. Will surface from prototyping.
- **How to handle "I couldn't find this" gracefully.** Hallucination prevention is critical. Need a structured "insufficient evidence" output mode.
- **Where do industry-specific tools live?** A "trade publication search" tool for plastics might not be relevant for hospitality. Tools probably need to be tenant-configurable (matches the industry-adaptive architecture).
- **Reflection / critique step worth the cost?** Adds 30–50% to per-query cost but probably catches the worst hallucinations. Test in Phase 2.

---

## 3.8 References for Phase 2

- *"ReAct: Synergizing Reasoning and Acting in Language Models"* (Yao et al., 2022) — the foundational paper.
- Anthropic's tool-use cookbook + Agent SDK docs.
- *"Reflexion: Language Agents with Verbal Reinforcement Learning"* (Shinn et al., 2023) — on self-critique loops.
- LangChain blog posts on agent failure modes (LangSmith observability case studies are good).
- *"Generative Agents: Interactive Simulacra of Human Behavior"* (Park et al., 2023) — agent design at scale.
- Recent Anthropic blog posts on prompt caching for agents (cost-saving patterns).

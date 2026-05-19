# Vendor deep-dive — Perplexity

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation in Phase 4.

## What Perplexity is

Perplexity is the most prominent **"search + LLM in one call"** product. The headline pitch: instead of the user (or your code) running a search, parsing results, and feeding them to an LLM separately, Perplexity does all three in a single API call. The output is a synthesised answer with inline citations, ready to consume.

Founded in 2022 (consumer product); API access opened publicly in 2024. Quickly became one of the most-used search-augmented LLM services. For Winston Wolf, Perplexity matters because it represents the **"black-box convenience"** end of the spectrum — opposite philosophy from Tavily (which gives you raw structured results to reason over yourself).

## How it works (mechanism)

This is the most opaque vendor of the four candidates. What's known:

- **Mixed underlying search.** Perplexity does NOT run its own crawler or index at meaningful scale. It uses a combination of:
  - **Google or Bing search results** under the hood (subject to change without notice — they've shifted between providers).
  - **Their own light scraping / live fetching** of the top results.
  - **Some indexed corpus** for fast results on common queries.
  Public statements about this have been inconsistent, and the actual mix has changed multiple times since launch.
- **Their own LLM stack.** Custom-tuned models for the search-and-answer flow. Variants named "Sonar" (proprietary), plus options to use Claude or GPT-4 as the answering model in the API.
- **Citations are extracted from the search results.** The LLM is constrained (by prompting) to cite which sources it used. Citations link back to the source URLs.

The result is a single API call: `query → search → fetch top results → LLM synthesises answer with citations → return`.

## API surface

REST API. SDK available via `pip install requests` (no first-party Python SDK; OpenAI-compatible API endpoints).

```python
import requests

response = requests.post(
    "https://api.perplexity.ai/chat/completions",
    headers={"Authorization": "Bearer ..."},
    json={
        "model": "sonar-pro",       # or "sonar", "sonar-reasoning"
        "messages": [
            {"role": "user", "content": "Who are senior procurement decision-makers at Richbond Group, Morocco?"},
        ],
        "search_domain_filter": [],         # optional whitelist
        "search_recency_filter": "month",   # optional time filter
        "return_citations": True,
    },
)
```

Models available (constantly evolving):

| Model | Purpose |
|---|---|
| **sonar** | Cheap, fast, basic search-and-answer. |
| **sonar-pro** | Better quality. More search depth, longer context. |
| **sonar-reasoning** | Multi-step reasoning over search results. Slower, more expensive. |

The API is **OpenAI-compatible** — meaning your code that talks to OpenAI can also talk to Perplexity with minor changes. Convenient but also reveals the abstraction is shallow.

## Pricing

Tier-based. Approximate (verify in Phase 2):

| Model | Input cost | Output cost | Search cost |
|---|---|---|---|
| sonar | ~$1/M tokens | ~$1/M tokens | $5/1000 searches included |
| sonar-pro | ~$3/M tokens | ~$15/M tokens | $5/1000 searches included |
| sonar-reasoning | Higher | Higher | Higher |

The pricing model is **token-based for the LLM portion, with search bundled in.** Different shape from Tavily/Brave/Exa where search is per-query and LLM is separate. Implication for cost modelling: a single Perplexity call could cost significantly more than (Tavily call + own LLM call), or significantly less, depending on response length.

There's also a **free tier with limited monthly credits** for testing.

## Strengths

- **Fewest possible steps.** Single API call returns a structured, cited answer. Less code, less integration.
- **Good for question-answering use cases.** When the agent needs an answer, not a list of links, Perplexity's design fits.
- **Citation handling is built in.** The LLM is constrained to cite sources, which mitigates one class of hallucination.
- **OpenAI-compatible API.** Minimal switching cost from OpenAI-based code.
- **Recency filtering is genuinely useful.** "What happened in the last month" type queries are well-served.

## Weaknesses / open questions

- **Black box.** You can't see the search results separately. When the answer is wrong, you can't easily diagnose whether search failed or LLM synthesis failed.
- **Locks you into their LLM.** If you've already committed to Claude or another LLM (which Winston Wolf has via the multi-LLM router decision), Perplexity adds a second LLM in the loop you can't fully control. Friction with the multi-LLM router.
- **Hallucinated citations.** Despite the citation constraint, Perplexity has been observed to fabricate citations under load — citing sources that say nothing relevant or don't exist. The constraint is prompt-level, not architectural.
- **Underlying search changes silently.** They've shifted between Google, Bing, and their own infrastructure without announcement. Your reproducibility is limited.
- **Cost is high per "useful answer"** at scale, because every call is a full LLM round trip on top of search.
- **Worse for "give me a list" queries.** Perplexity wants to synthesise a narrative answer; if you want 50 candidate lead URLs, you're often better off with raw Tavily/Brave results.

## How it fits Winston Wolf

Perplexity is the **"convenience" candidate** in the Phase 4 bake-off. The hypothesis it tests: *"Is the all-in-one search-plus-LLM approach better than decomposed search-then-LLM?"*

For Scout's primary use case (find specific people at specific companies), I'd expect Perplexity to be **second-best to Tavily or Brave with our own LLM**, because:
- We want raw candidate lists, not narrative answers.
- We need debuggability — see the search results, then see why the LLM picked what it picked.
- We want our own LLM (per multi-LLM router decision) doing the reasoning, not Perplexity's locked-in LLM.

But that hypothesis needs testing. There are scenarios where Perplexity wins:
- Quick "what does this company do?" lookup — one call, one answer, done.
- Recency-filtered queries (recent news, recent moves).
- Where the "answer" is a paragraph, not a list.

The Phase 4 result might end up as: **Tavily/Brave for the bulk of Scout's heavy-lift research, Perplexity for specific narrative queries where it's cheaper end-to-end.** Or Perplexity might lose entirely. To verify.

## Verification queue (for Phase 2)

1. **Same Richbond query as Tavily / Brave / Exa.** Compare results — but note the format mismatch (narrative answer vs. list).
2. **Test `sonar` vs `sonar-pro` vs `sonar-reasoning`.** Quality and cost trade-offs.
3. **Citation accuracy check.** For the answers it returns, manually verify citations actually support the claims.
4. **Recency filter test.** Use `search_recency_filter` for a query about recent events; see if results actually shift.
5. **Cost per useful answer.** Track tokens used vs. quality of result.
6. **OpenAI-compatible quirks.** Test that `model` param routing works as documented, response format is consistent.

## References

- Perplexity API docs: https://docs.perplexity.ai (verify URL).
- Perplexity blog posts on Sonar models.
- Public posts (LangChain, LlamaIndex, HackerNews) on Perplexity's underlying search infrastructure changes.
- Comparative articles on "search + LLM" vs. "search → LLM" architectures.

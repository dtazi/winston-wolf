# Vendor deep-dive — Tavily

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation in Phase 4.

## What Tavily is

Tavily is a search API designed specifically for AI agents and LLM-driven applications. Founded ~2023 by former NLP / search-infrastructure engineers. The pitch: traditional search APIs (Google, Bing) return results optimised for human consumers, which means the LLM consuming those results has to do a lot of cleanup. Tavily flips this — results are pre-cleaned, structured, summarised, and shaped for LLM consumption from the start.

It's purpose-built for the use case Winston Wolf will hit constantly: an LLM agent needs to look something up on the web, reason over what it finds, and decide what to do next.

## How it works (mechanism)

Tavily runs its own **proprietary search index** (their own crawler + index, not a Google/Bing reseller). Internal architecture details aren't fully disclosed, but their public statements + observed behaviour suggest:

- **Crawler:** their own, optimised for "research-quality" content (deprioritises low-quality, ad-heavy, content-farm pages).
- **Index:** built fresh for AI-agent use. Smaller than Google's, but tuned for relevance over coverage.
- **Ranking:** reportedly hybrid — keyword + semantic + LLM-based reranking. Optimises for "useful information for an agent" rather than "what would a human click."
- **Result post-processing:** snippets are cleaned of HTML/scripts/ads. Optional summarisation by their own LLM.
- **Optional content extraction:** can fetch and parse full page content alongside the search step.

Their main product surfaces:

| Endpoint | What it does |
|---|---|
| `/search` | Standard web search. Returns ranked results with title, URL, snippet, score. Optional `include_answer` produces a summarised answer. |
| `/extract` | Given URLs, fetch and parse clean readable content. Useful for "search → extract → reason" pipelines. |
| `/crawl` (newer, beta) | Recursive site crawl with a query filter. |

## API surface

Python SDK: `pip install tavily-python`. Single-call usage:

```python
from tavily import TavilyClient
client = TavilyClient(api_key="...")
results = client.search(
    query="senior leadership at Richbond Group Morocco",
    search_depth="advanced",     # or "basic"
    max_results=10,
    include_domains=[],          # whitelist filter
    exclude_domains=[],          # blacklist filter
    include_answer=True,         # LLM-synthesised summary
    include_raw_content=False,   # full page content
)
```

Response is a JSON dict with `results` (list of items with `title`, `url`, `content`, `score`) and optional `answer` (string).

The synchronous design is fine for batch / agent workflows. Async support exists in the official SDK.

## Pricing (as of late 2025 / early 2026 — verify in Phase 2)

| Tier | Queries/month | Cost |
|---|---|---|
| Free | 1,000 | $0 |
| Pay-as-you-go | Unlimited | $0.005–0.020/query depending on depth and add-ons |
| Production / Enterprise | Volume contracts | Custom pricing |

For Winston Wolf's testing phase, the free tier covers everything. At customer-scale (hundreds of queries per Scout run × hundreds of customers per month), the cost becomes meaningful — needs modelling.

## Strengths

- **Built specifically for LLM agents.** The result format, summarisation, and ranking all assume an LLM is consuming the output. Less post-processing than search APIs designed for humans.
- **Independent index.** Doesn't depend on Google or Bing licensing. Reasonable defence against vendor lock-in or API changes from those providers.
- **Clean documentation, clean SDK.** Easy to integrate. ~30 lines of Python for a working call.
- **`include_answer` is genuinely useful.** Instead of having a separate LLM step to summarise N search results, Tavily produces a coherent answer with citations as part of the search call. Saves tokens.
- **Free tier is generous enough to validate seriously.** 1,000 queries is more than enough to run the Richbond evaluation.

## Weaknesses / open questions

- **Smaller index than Google.** Coverage of niche, non-English, or older content is unknown. Critical question: how does Tavily handle Moroccan / French / Arabic content? *To verify in Phase 2.*
- **Less battle-tested than older players.** Founded ~2023 vs. Google's decades. Quality may vary across query types.
- **Pricing at scale.** $0.005–0.020 per query is cheap for testing, costly at high volume. Modelling needed once we know Scout's per-customer query rate.
- **Mechanism transparency.** They don't publish architecture details the way some open-source players do. Hard to fully understand why a query returns what it does.
- **Geographic / language coverage.** Their public materials are heavily English-centric; non-English performance is unproven without testing.

## How it fits Winston Wolf

Tavily would slot into the **search backend** layer of Scout (per the architecture in `topics/03-agent-loops.md`). The agent has a tool called `search_web` whose implementation calls Tavily. Other backends (Brave, Exa, Perplexity) implement the same interface and can be swapped in.

For the Richbond evaluation in Phase 4, Tavily's strengths matter most:
- We need clean structured results an LLM can reason over → Tavily designed for this.
- We don't need petabyte-scale coverage → Richbond test is small-volume.
- We need debuggability → Tavily returns raw results, not just a black-box answer.

The open question is *quality on Moroccan/French content.* If Tavily's index is thin there, we'd need to lean more on Brave (independent index) or Google-via-SerpAPI (richest geographic coverage, but ranking optimised for human consumers).

## Verification queue (for Phase 2)

Things to test hands-on before drawing real conclusions:

1. **Run a known-answer query** (e.g., "CEO of Richbond Group") and verify the result. Confidence baseline.
2. **Run a Moroccan-French query** ("directeur achats hospitality Maroc") and judge result quality vs. an English equivalent.
3. **Test `include_answer`** on a research-style query. Compare the synthesised answer to the raw results — does the summarisation lose information?
4. **Test rate limits and latency** under realistic load. Median + 95th percentile.
5. **Pricing math at projected scale.** Verify current pricing tiers match the 2025 numbers above.
6. **Test the `/extract` endpoint** on a few representative URLs (a company About page, a press release, a LinkedIn-style listing). Does it parse cleanly?

## References

- Tavily official docs: https://docs.tavily.com (verify URL — may have changed).
- Tavily Python SDK GitHub repo.
- Tavily blog posts on their architecture and ranking philosophy (limited but useful).
- Comparative articles from agent-framework communities (LangChain, LlamaIndex blog) — they've all integrated Tavily and have opinions.

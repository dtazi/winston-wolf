# Vendor deep-dive — Brave Search API

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation in Phase 4.

## What Brave Search is

Brave Search is the search engine built by Brave Software (the same company behind the Brave browser). Launched in 2021, declared fully independent of Google and Bing in 2023. The headline differentiator: **Brave runs its own crawler and its own index, with no licensing of Google or Bing behind the scenes.** Most "independent" search engines secretly resell Bing or Google; Brave is one of very few that genuinely doesn't.

The API exists primarily as a way to monetise the index — selling search-as-a-service to developers, alongside the consumer search engine.

For Winston Wolf, Brave matters because it's the strongest *non-Tavily, non-Google* comparison anchor. If Tavily and Brave disagree on a query, we're seeing two genuinely different indexes + ranking philosophies, not the same data with different wrappers.

## How it works (mechanism)

The interesting part. Brave's index is built from a few sources combined:

- **Their own crawler.** A traditional web crawler operating since 2021. Smaller than Google's but growing.
- **Web Discovery Project (WDP).** Brave Browser users can opt in to contribute anonymised browsing data. Specifically: which URLs are visited, how long, what the page broadly looks like. This helps Brave's crawler discover sites that aren't well-linked from already-indexed pages — a real cold-start problem any new search engine has.
- **Periodic ingestion of CommonCrawl** (open public web crawl) for breadth.

So the index is a hybrid: their proprietary crawl + opt-in human discovery + open-source web crawl. Reasonable for a player without Google's infrastructure budget.

**Ranking.** Less LLM-tuned than Tavily, more traditional-search-tuned. Their public stance: privacy-respecting, no personalisation tracking, no demographic profiling. Ranking is broadly relevance-based with quality signals derived from the open web (links, domain reputation), but not from user click data the way Google's is.

**One real differentiator: less spam-filtering than Google.** Google's modern ranking heavily downweights pages it judges low quality or "spammy." This is great for human consumers but can hurt for niche / specialised research where the relevant page isn't well-known. Brave doesn't apply Google's degree of curation. Sometimes this surfaces useful obscure content; sometimes it surfaces actual spam.

## API surface

REST API. Python SDK is community-built (not first-party — most users hit the REST endpoints directly).

```python
import requests

response = requests.get(
    "https://api.search.brave.com/res/v1/web/search",
    headers={"X-Subscription-Token": "..."},
    params={
        "q": "senior leadership Richbond Group Morocco",
        "count": 10,
        "country": "ma",          # ISO country code, optional
        "search_lang": "fr",      # language hint
        "safesearch": "off",
    },
)
results = response.json()
```

Response is a structured JSON dict with `web` (results), `news`, `videos`, `infobox` (knowledge-graph-style data), etc. Less LLM-friendly than Tavily — you get raw search results, not pre-summarised answers. You'd typically pass the results to your own LLM call.

Multiple API products:
| Product | Purpose |
|---|---|
| **Web Search API** | General web search. The default. |
| **News Search API** | Recent news results (last 24h to year). |
| **Image Search API** | Image results. |
| **AI Grounding API** (newer) | Designed for LLM grounding — cleaner result format, optional content extraction. Closer to Tavily's positioning. |

The AI Grounding API is recent and worth investigating in Phase 2 — it's Brave's response to the AI-search market.

## Pricing

| Tier | Quota | Cost |
|---|---|---|
| Free / Data for Free | 2,000 queries/month | $0, requires displaying Brave Search attribution |
| Data for Pay | Volume-priced | ~$5 per 1,000 queries (≈ $0.005/query) |
| Data with Storage | Volume-priced + caching rights | More expensive; allows caching results |

Notable: the free tier is 2x Tavily's free tier in query count, and at paid rates Brave is roughly comparable (~$0.005/query) to Tavily's basic depth. Their pricing has been more stable than newer entrants.

## Strengths

- **Genuinely independent index.** No hidden Google or Bing dependency. Diversifies the risk surface — if Google's API access changes, Brave keeps working.
- **Less spam-filtering than Google.** Surfaces obscure / niche content Google might downweight. Useful for vertical research (industry-specific trade press, smaller business sites).
- **Stable, mainstream company.** Brave has been around since 2016 (browser launch) and has revenue from multiple lines (browser ads, Search API, BAT). Less startup-failure risk than Tavily.
- **Privacy-respecting posture.** No tracking, no demographic profiling. Means results are the same regardless of who's querying — predictable and debuggable.
- **Generous free tier.** 2,000 queries/month covers serious testing.

## Weaknesses / open questions

- **Smaller index than Google.** Specifically thinner outside of well-indexed mainstream English content. **Coverage of Moroccan / French / Arabic content is the critical question for Winston Wolf** — to verify in Phase 2.
- **Less LLM-tuned than Tavily.** Result format is closer to traditional search — you get web pages, not pre-cleaned snippets or summarised answers. Need to do more post-processing before feeding to an LLM. AI Grounding API may close this gap (verify in Phase 2).
- **Ranking philosophy is "traditional search."** Optimised for human-consumer reading patterns. Whether this is better or worse than Tavily's AI-tuned ranking for finding specific people at specific companies is unknown — exactly the question the bake-off answers.
- **Less spam-filtering can also be a downside.** Surfaces obscure content but also surfaces real spam more readily than Google. Need rerank/filter step downstream.
- **No Python SDK from Brave directly.** Have to hit REST endpoints. Minor — community SDKs exist.

## How it fits Winston Wolf

Brave's role in Scout: same as Tavily's — search backend for the agent's `search_web` tool. The architectural pattern is identical (pluggable backend implementing the same interface).

For the Phase 4 comparative evaluation, **Brave is essential** as a non-Tavily, non-Google reference point. Without Brave, you'd be testing Tavily vs. Google (via SerpAPI) and Perplexity (which uses Google/Bing internally) — that's three Google-derived stacks vs. one outsider. Brave provides genuine paradigm diversity.

Specific testing hypotheses worth checking:
1. **Brave finds different things than Tavily** on the Richbond test. Same query, different top-10. Both have value.
2. **Brave handles Moroccan / French content differently** than Tavily. Either could win; need to test.
3. **Brave's "less filtering" surfaces useful obscure content** that Tavily's AI-tuned ranking deprioritises. Plausible for niche industries.

## Verification queue (for Phase 2)

1. **Same Richbond query as Tavily test.** Compare top-10 side by side.
2. **Moroccan-French query.** Same as Tavily's test.
3. **AI Grounding API.** Test if available — does it bridge the LLM-friendliness gap with Tavily?
4. **Geographic targeting.** Test `country=ma` and `search_lang=fr` parameters — do they meaningfully affect results?
5. **Latency and rate limits.** Median + 95th percentile.
6. **Result-format post-processing cost.** How much LLM-token cost is added to clean up Brave's results vs. using Tavily's pre-cleaned format?

## References

- Brave Search API docs: https://api.search.brave.com/app/documentation (verify URL).
- Brave Search blog posts on the index and crawler architecture.
- Web Discovery Project documentation.
- Comparative blog posts from agent-framework communities (LangChain, LlamaIndex).

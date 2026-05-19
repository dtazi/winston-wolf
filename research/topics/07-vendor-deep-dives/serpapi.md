# Vendor deep-dive — SerpAPI / Serper

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation in Phase 4.

## What SerpAPI / Serper are

SerpAPI and Serper are **wrappers over Google Search**. They scrape Google's search results page (SERP — Search Engine Results Page), parse the HTML, and return structured JSON. The user gets Google's index quality and ranking via a simple API call.

Two main players:
- **SerpAPI** — the older, larger company. More mature, broader features (also covers Bing, Yahoo, Yandex, Baidu, plus image / video / shopping search).
- **Serper** — newer, cheaper, faster. Focused on Google web search; less surface area, more competitive pricing.

For Winston Wolf, this category matters because **it lets us test Google's ranking against the AI-search alternatives** (Tavily / Brave / Exa / Perplexity) directly. Without this category in the bake-off, we can't answer the question *"is Google actually better?"* — we'd just be comparing AI-search vendors to each other.

## How it works (mechanism)

The mechanism is conceptually simple but operationally fraught:

- **The "search" is just a Google query.** The provider sends the query to Google, gets the HTML SERP back, parses it into structured JSON.
- **Google does not officially license this.** The Search API that Google sells (Custom Search JSON API) is much more limited — capped quotas, restricted to specific custom search engines. SerpAPI / Serper bypass this by scraping the public SERP page.
- **They handle all the scaling and unblocking.** Google aggressively rate-limits and CAPTCHAs scrapers. SerpAPI / Serper use rotating IPs, residential proxies, browser automation, and CAPTCHA-solving services to stay accessible.

What you get back is essentially **Google's index + Google's ranking, with a thin parsing layer.** Same results you'd see if you typed the query into google.com — including organic results, "People also ask" boxes, knowledge panels, news boxes, related searches.

## API surface

REST API. Multiple SDKs available (official Python, community for others).

```python
# SerpAPI
import requests
r = requests.get("https://serpapi.com/search", params={
    "q": "Richbond Group senior leadership",
    "engine": "google",
    "google_domain": "google.com",
    "gl": "ma",          # country code
    "hl": "fr",          # language
    "api_key": "...",
})

# Serper
r = requests.post("https://google.serper.dev/search", 
    headers={"X-API-KEY": "..."},
    json={"q": "Richbond Group senior leadership", "gl": "ma", "hl": "fr"},
)
```

Response: a JSON dict mirroring Google's SERP structure — `organic_results`, `knowledge_graph`, `people_also_ask`, `related_searches`, etc.

## Pricing

| Provider | Free | Paid |
|---|---|---|
| **SerpAPI** | 100 queries/month | $50/mo for 5,000 queries; $250/mo for 30,000; enterprise above |
| **Serper** | 2,500 queries free (one-time) | $50/mo for 50,000 queries (10x cheaper at the entry tier) |

Serper is **dramatically cheaper** per query. SerpAPI's premium is for breadth (multiple engines, more parsers, longer history). For Winston Wolf testing volumes, Serper is the obvious value pick.

## Strengths

- **Best index in the world for general-purpose search.** Google's index is the largest, freshest, and most comprehensively maintained. Period.
- **Best ranking for human-consumer queries.** Decades of optimisation behind it.
- **Geographic + language coverage is unmatched.** Localised results via `gl` and `hl` parameters work well for Moroccan French content.
- **Knowledge graph data is included.** Google's structured data about companies, people, and concepts comes back in the response — sometimes useful as a free contact-data signal.
- **Cheap (Serper) at testing volumes.**

## Weaknesses / open questions

- **Rankings are tuned for human consumers.** When Scout wants "give me 50 candidate lead URLs," Google's ranking optimises for "what would a human click first" — which biases toward big-name, ad-friendly content. May miss niche / vertical sources Tavily or Brave would surface.
- **Aggressive spam filtering can hurt vertical research.** Google downweights pages it judges low-quality, including legitimate small-business sites and vertical trade publications. Brave's "less filtering" advantage is the flip side of this.
- **Legal / ToS uncertainty.** Google does not explicitly approve SerpAPI / Serper. While these services have operated for years without successful legal challenge, the underlying scraping is in a grey area. Winston Wolf depending on this introduces a small but real availability risk.
- **No semantic / agent-tuned ranking.** Whatever Google's ranking does, it doesn't know the consumer is an LLM. You may need an extra rerank step.
- **Less rich result format than Tavily.** No pre-cleaned snippets, no LLM-friendly summarisation. You get raw SERP data and have to do the cleanup yourself.
- **Rate limits at scale.** Even Serper has limits; very high-volume Scout usage might bottleneck.

## How it fits Winston Wolf

SerpAPI / Serper is the **"is Google actually better?"** candidate in the Phase 4 bake-off. The hypothesis: maybe AI-tuned indexes (Tavily, Exa) over-optimise for AI-friendliness at the cost of raw coverage. Maybe what we really want is Google's index, with our own LLM doing the agent-friendly post-processing.

If Serper wins on coverage (especially Moroccan / French content) and the post-processing cost is manageable, it could become Scout's primary search backend.

If it loses (rankings biased toward big-name content, niche vertical sources missing), then the AI-search vendors keep their place.

For the Phase 4 evaluation, I'd recommend **using Serper** (not SerpAPI) — it's 10x cheaper at our scale, and we don't need the multi-engine breadth.

## Verification queue (for Phase 2)

1. **Same Richbond query against Serper.** Compare top-10 to Tavily / Brave / Exa.
2. **Moroccan French query** with `gl=ma` and `hl=fr`. Test localisation.
3. **Knowledge graph data.** When querying for a known company, does the knowledge_graph block return useful structured info (CEO, employee count, founding date, etc.)?
4. **Vertical / niche content.** Query for a specific hospitality FF&E topic; does Google surface trade publications or only mainstream press?
5. **Cost per useful result.** Track Serper spend vs. quality.
6. **Latency.** Is Serper faster or slower than Tavily/Brave/Exa? Important for agent loops.

## References

- SerpAPI docs: https://serpapi.com/docs.
- Serper docs: https://serper.dev/api-key (after sign-up).
- Hacker News and Reddit threads on Google API alternatives.
- LangChain / LlamaIndex blog posts on integrating SerpAPI.
- Comparative articles on "rolling your own Google scraper" vs. SerpAPI / Serper (the underlying ToS / cost trade-off).

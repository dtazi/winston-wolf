# Topic 02 — Web search stack

**Status**: Phase 1 stub. Will deepen in Phase 2 with vendor-by-vendor verification.

## Why this matters for Winston Wolf

Topic 01 covered the algorithms that match queries to documents. This topic covers what those algorithms run *on* — the giant indexed corpus of the web. When Winston Wolf calls Tavily, Brave, Exa, or Perplexity, the quality of results depends primarily on **which underlying web index they hit** and **how that index is ranked**. Understanding the search stack lets us judge whether a vendor has a real differentiation or whether they're reselling the same index as competitors under a different ranking.

---

## 2.1 The search pipeline

Web search has four distinct layers, each engineered separately:

1. **Crawl** — bots visit web pages and download HTML.
2. **Index** — downloaded pages are parsed, tokenised, deduplicated, and stored in a queryable structure.
3. **Rank** — at query time, candidate documents are scored and ordered.
4. **Serve** — top results returned to the client, often with snippets and metadata.

Each layer is a hard engineering problem in its own right. Building a complete stack from scratch at meaningful scale is essentially impossible — Google has thousands of engineers and decades of investment in each layer. **Most "search APIs" you see are either (a) reselling Google/Bing under a wrapper, or (b) building on a shared crawl plus their own index.**

---

## 2.2 Crawling — the foundation

A web crawler downloads pages, extracts links, queues new URLs, repeats. Conceptually trivial; in practice:

- **Scale.** The public web has ~10+ billion pages. Crawling means hundreds of millions of HTTP requests per day.
- **Politeness.** Each domain has rate limits; aggressive crawling gets you blocked.
- **Coverage decisions.** What to recrawl and how often is its own optimisation problem.
- **Quality filtering.** Spam, mirrors, low-value pages have to be excluded before indexing.

**Major active crawlers:**

| Crawler | Feeds |
|---|---|
| Googlebot | Google search |
| Bingbot | Bing → DuckDuckGo, Yahoo, parts of ChatGPT search |
| CommonCrawl | Non-profit; monthly public snapshot. Free for researchers. |
| Brave | Brave Search (independent, recent) |
| Mojeek | UK-based, independent. Smaller but distinct. |

**Most other "search engines" do not run their own crawler.** They license one of the above. This is the single most important fact in the search-API landscape.

---

## 2.3 Indexing — making search fast

The index is the data structure that lets a query return results in <100ms. Conceptually an inverted index (term → list of documents) plus per-document metadata. In practice:

- **Sharded** across hundreds or thousands of machines.
- **Deduplicated** so the same page on multiple URLs doesn't dilute results.
- **Spam-filtered** at index time (low-quality pages downweighted or excluded entirely).
- **Update lag** — how soon a freshly-crawled page becomes searchable. Varies by index.

**What an index "knows" matters as much as how big it is.** Google's index is huge but heavily curates against perceived spam, which means rare or specialised content can be hard to find. CommonCrawl is just a raw dump — different trade-offs.

---

## 2.4 Ranking — where engines differ most

Ranking decides which of potentially millions of matching documents shows up first. Signals fall into a few categories:

- **Relevance** — keyword/topic match (Topic 01 territory).
- **Authority** — links from other pages, domain reputation (PageRank descendants).
- **Freshness** — newer is often better, especially for news/event queries.
- **User signals** — click-through rate, dwell time. Usually proprietary, often the secret sauce.
- **Quality** — perceived spam, content depth, originality.
- **Geographic / personalisation** — location, language, query history.

**The ranking layer is where search engines most differ from each other.** Google's ranking is tuned for human consumer queries with ad-relevant intent; Brave is privacy-respecting and unfiltered; Tavily and Exa are tuned for AI-agent use cases (clean structured results, not "what would you click?"). The same query against the same underlying crawl can produce very different top-10s.

---

## 2.5 What's actually under each AI-search vendor (best current understanding)

| Vendor | Crawler / Index | Ranking |
|---|---|---|
| **Tavily** | Proprietary, built for AI agents | AI-agent-tuned (clean structured results) |
| **Brave Search API** | Brave's independent crawler/index | Privacy-respecting, unfiltered |
| **Exa** (formerly Metaphor) | Proprietary, embedding-first | Semantic / dense-retrieval-first |
| **Perplexity API** | Mixed (uses Google/Bing-ish + own) | LLM-driven re-ranking + answer synthesis |
| **SerpAPI / Serper** | Google's | Google's |
| **You.com** | Own crawler/index (newer) | Hybrid AI ranking |
| **Bing Search API** | Bing's | Bing's |

⚠️ Some of these need verification in Phase 2 — vendors change crawl/index sources without much announcement, especially Perplexity. Vendor deep-dives in `topics/07-vendor-deep-dives/` will pin down the current state.

**Implication:** If you test SerpAPI and Tavily and they disagree, you are not seeing "Tavily is better/worse" — you are seeing "Google's index + Google's ranking" vs "Tavily's index + Tavily's ranking." Different at every layer. Comparisons are only meaningful when you understand what you're comparing.

---

## 2.6 The economics of search

Why do search APIs cost what they cost?

- **Crawling + storage** — petabytes of data, ongoing recrawl, redundant storage.
- **Query compute** — each query fans out across shards, plus reranking.
- **Network egress** — sending results to clients.

Rough per-query unit cost at scale: $0.0005–$0.005 for major engines, with vendor markup on top.

**Implication for Winston Wolf:**
- At Phase 1 testing volumes (hundreds of queries), search costs are negligible.
- At customer scale (millions of queries/month), search can become a meaningful operational expense — worth modeling.
- Free tiers (Tavily 1000/mo, etc.) are loss-leaders to acquire customers; do not assume they survive long-term.

---

## 2.7 Open questions for Winston Wolf

- **Which index has the best Moroccan / French / Arabic content coverage?** Likely Google leads on raw coverage; Brave / Tavily / Exa are uncertain. To be tested in Phase 2 against real Richbond-vertical queries.
- **Does AI-agent-tuned ranking (Tavily/Exa) outperform Google's ranking** for finding specific people at specific companies? This is essentially the comparative-eval question of Phase 4.
- **How much do we lose by NOT running our own crawl?** Probably very little for general queries; could matter for niche industries (vertical event data, trade publications) where general-purpose indexes are thin.
- **Industry-specific data sources** (business registries, exhibitor lists, conference data, trade publications) — should we ingest these into our own index, or is search-API alone enough? Topic 05 territory.
- **Latency expectations**: API search latencies are 200ms–2s typically. Acceptable for batch lead-gen; might bite for interactive flows.

---

## 2.8 References for Phase 2

- *"Anatomy of a Large-Scale Hypertextual Web Search Engine"* (Brin & Page, 1998) — the original Google paper. Old but foundational.
- CommonCrawl docs and stats.
- Brave Search blog posts on building an independent index.
- Tavily / Exa public blog posts on their indexing and ranking philosophy.
- *"Search Engines: Information Retrieval in Practice"* (Croft, Metzler, Strohman) — textbook reference covering the full stack.
- Recent posts on Bing API access changes (2026 — verify current state).

# Vendor deep-dive — Exa (formerly Metaphor)

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation in Phase 4.

## What Exa is

Exa (originally Metaphor, rebranded ~2024) is a search engine built around **dense retrieval from the ground up**. Where Tavily and Brave run traditional keyword-based indexes (with LLM tuning bolted on), Exa was designed from day one to do semantic search — queries are converted to embeddings, results are nearest neighbours in vector space.

Their original pitch: **"search the web like an LLM thinks."** A user query like "small Italian companies making sustainable home textiles" doesn't need to literally appear on any indexed page — Exa finds pages that are *semantically similar* to the meaning of the query, regardless of which exact words appear.

For Winston Wolf, Exa matters because it represents a **fundamentally different search paradigm** from Tavily and Brave. Including it in the bake-off tests whether dense-retrieval-first beats keyword-first-with-LLM-tuning for the kinds of queries Scout will actually run.

## How it works (mechanism)

The interesting differentiation:

- **Their own crawler.** Recent and aggressive.
- **Index is structured for dense retrieval.** Every page gets embedded into a vector by their proprietary embedding model (or models — they've experimented with several). The index is essentially a giant nearest-neighbour-searchable vector store, not an inverted-index of words.
- **No traditional ranking signals as the primary axis.** Authority, link graph, freshness — these exist as filters and re-rankers but aren't the primary ordering signal. Semantic similarity is.
- **Hybrid mode available.** Recent versions allow combining dense retrieval with keyword retrieval — recognising that pure semantic search misses some queries.

The "find similar" feature is the original killer demo: give Exa a URL of a page, and it finds other pages similar in *meaning* — not by matching words, but by matching embedded concepts. Useful for "find me companies like this one" queries.

The trade-off: this paradigm wins on conceptual queries ("decision-makers in sustainable manufacturing") and loses on precision queries ("CEO of Richbond Group" — where you want a specific factual answer).

## API surface

Python SDK: `pip install exa_py`. Clean and modern.

```python
from exa_py import Exa
exa = Exa(api_key="...")

# Standard semantic search
results = exa.search(
    query="senior procurement decision-makers in Moroccan hospitality manufacturing",
    num_results=10,
    type="neural",                  # or "keyword" or "auto"
    use_autoprompt=True,            # LLM rewrites query for better neural retrieval
    category="company",             # category filters
    start_published_date="2024-01-01",
)

# Find-similar: given a URL, find pages like it
similar = exa.find_similar(
    url="https://www.richbond.com/",
    num_results=10,
)

# Fetch full content of search results
contents = exa.get_contents(
    ids=["url1", "url2"],
    text=True,
    summary=True,
)
```

Multiple endpoints worth knowing:

| Endpoint | Purpose |
|---|---|
| `search` | Semantic search (neural / keyword / auto-detect). |
| `findSimilar` | Given a URL or document, find similar ones. Unique to Exa. |
| `getContents` | Fetch + parse + optionally summarise content from result URLs. |
| `research` (newer) | Multi-step agent research over Exa's index. |
| `websets` (newer) | Curated collections — "all hospitality companies in Morocco" type buckets. |

The `use_autoprompt=True` parameter is interesting: it has an LLM rewrite the query into a form better-suited to neural retrieval. Often this is the difference between "found nothing useful" and "found exactly what I wanted."

## Pricing

| Tier | Quota | Cost |
|---|---|---|
| Free | Limited monthly quota (current free tier ~1,000 searches/month) | $0 |
| Pro | Pay per call | ~$0.005–0.030 per call depending on endpoint and content fetch |
| Enterprise | Volume discounts + storage rights | Custom |

Pricing is more variable than Tavily or Brave because the different endpoints (search vs. find-similar vs. get-contents) have different costs. `getContents` with full-text parsing is the expensive one. Verify current pricing in Phase 2.

## Strengths

- **Genuinely different paradigm.** Dense retrieval from the ground up, not bolted-on. The find-similar endpoint specifically is unique in the market.
- **Great for vague / conceptual queries.** "Companies like X" or "people who work in roles similar to Y" — Exa handles these much better than keyword search.
- **`use_autoprompt` is actually useful.** Saves the user from having to write LLM-friendly queries manually.
- **Modern Python SDK.** Type-hinted, async support, well-maintained. Easy to integrate.
- **Good for discovery use cases.** Where you don't know exactly what you're looking for and want the system to surface plausible candidates.

## Weaknesses / open questions

- **Smaller index than Google or even Brave.** Exa is newer (~2022) and the crawl is less mature. Niche / non-English content coverage is the critical Phase 2 test.
- **Semantic search can be unintuitive.** The "fluffy similarity" problem — sometimes returns results that match on the wrong axis (style instead of meaning, related-topic instead of the topic itself).
- **Worse for exact-match factual queries.** "CEO of [specific company]" is a Tavily/Brave/Google query, not really an Exa query.
- **Embedding quality is the ceiling.** Whatever embedding model Exa uses determines result quality. They've changed models over time; what's current is opaque.
- **Multilingual support is unproven.** Public materials are English-centric. Performance on Moroccan French / Arabic content is unknown.
- **Find-similar is powerful but narrow.** Useful when you have a known good example; useless when you don't.

## How it fits Winston Wolf

Exa's role in Scout is more specialised than Tavily or Brave. Three plausible patterns:

1. **As a "find similar companies" tool.** When the customer knows one good lead/company and wants to find similar ones, `findSimilar(url=that_company.com)` is uniquely well-suited. This connects directly to the **"Bootstrapped ICP from exemplars"** parking-lot idea in VISION.md — give Exa 3-5 of the customer's existing best clients, ask for similar companies. Very promising.

2. **As a discovery layer.** When the query is vague ("decision-makers diversifying from Chinese furniture suppliers"), Exa's neural search may surface candidates that keyword-based engines miss.

3. **As a complement to Tavily/Brave, not a replacement.** Exa for conceptual / discovery queries, Tavily or Brave for specific / factual queries. The agent picks based on query type.

For the Phase 4 evaluation, Exa is essential to test as a paradigm difference. Three queries to put against it:
- A specific factual query: "CEO of Richbond Group" — likely Exa is not the best choice.
- A conceptual query: "senior decision-makers at non-China hospitality FF&E manufacturers" — Exa should shine.
- A find-similar query: given Richbond's URL, find similar Moroccan or MENA manufacturers.

## Verification queue (for Phase 2)

1. **Same Richbond query as Tavily / Brave tests.** Compare what Exa surfaces.
2. **Find-similar test.** Feed Richbond's URL, evaluate the returned similar-companies list.
3. **Vague conceptual query.** "Furniture buyers diversifying from Chinese suppliers" or similar. See if neural search wins on this kind of query.
4. **Multilingual test.** French-language query; non-English content presence.
5. **`use_autoprompt` impact.** Same query with and without autoprompt; measure quality difference.
6. **Cost per useful result.** Track which endpoint costs what; optimise toward cheap-and-good ratios.
7. **`websets` for hospitality / FF&E.** Investigate whether Exa has pre-curated collections that speed up Richbond's vertical-specific queries.

## References

- Exa docs: https://docs.exa.ai (verify URL).
- Exa blog posts on neural search and the find-similar architecture.
- Original "Metaphor" paper / launch blog (2022) — describes the dense-retrieval-first approach.
- Comparative posts from LangChain / LlamaIndex on Exa vs. other search APIs.

# Topic 04 — RAG fundamentals

**Status**: Phase 1 stub. Most directly relevant to the Knowledge Base module; secondarily relevant to Scout for processing large search-result pages.

## Why this matters for Winston Wolf

**RAG (Retrieval-Augmented Generation)** is how an LLM reasons over content it wasn't trained on — a customer's product catalog, an industry's terminology, past successful email templates, internal Winston Wolf playbooks. The constitution names a Knowledge Base module (Article 5); RAG is the technique that makes it useful.

The Outreach module will likely call RAG every time it drafts an email: *"given this lead's company and role, retrieve the most relevant product positioning, customer success stories, and template fragments from the Knowledge Base, then write the email."* Scout may also use RAG-style processing when a single search result is too large to feed wholesale into an LLM.

Get RAG right and Winston Wolf's outputs feel genuinely informed. Get it wrong and the LLM either hallucinates or produces generic outputs that don't pull on the customer's actual knowledge.

---

## 4.1 The basic RAG pipeline

There are two phases — **ingest-time** (run once or on update) and **query-time** (run per request).

**Ingest-time:**

```
documents → chunk → embed → store
                              ↓
                       (vector DB)
```

**Query-time:**

```
user query → embed → similarity search → top K chunks → LLM with chunks in context → answer
```

The whole thing is conceptually simple. The complexity is in every individual step — chunking choices, embedding model choices, retrieval tuning, context formatting. Each step has dozens of failure modes.

---

## 4.2 Chunking — the most-underestimated step

You can't put a 50-page product catalog into a single LLM context. You have to break it into smaller pieces ("chunks") that can be retrieved individually. **Chunking is where most RAG quality is gained or lost.**

### Strategies

- **Fixed-size chunks** (e.g., 512 tokens with 50-token overlap). Simple, dumb, often the worst at preserving meaning. Will split a sentence mid-clause if the boundary lands there.
- **Sentence-based** — chunk on sentence boundaries. Better than fixed-size for prose; ignores document structure.
- **Structural / semantic** — chunk on document structure (headings, paragraphs, list items) and/or topic shifts. Better for structured docs (manuals, articles, schemas).
- **Late-chunking** (recent technique) — embed the entire document, then chunk the embedded representations. Preserves cross-chunk context but requires a long-context embedding model.
- **LLM-based chunking** — ask an LLM to identify natural chunk boundaries. Expensive but can be very good for messy documents.

### What goes wrong with bad chunking

- **Information cut in half.** A definition on chunk N, the example on chunk N+1, neither retrievable alone makes sense.
- **Lost context.** A chunk that says "this is required" without saying what "this" refers to is a retrieval garbage result.
- **Diluted relevance.** Big chunks that mix relevant and irrelevant content score lower in retrieval than focused ones would.

### Chunk size trade-offs

- **Smaller chunks** (~100–300 tokens): more precise retrieval, higher recall on specific facts, more chunks to embed and store, more chunks per LLM context (more tokens to pay for).
- **Larger chunks** (~1000–2000 tokens): more context preserved, fewer total chunks, less precise retrieval, more "wasted" tokens (irrelevant content riding along).

For Winston Wolf's Knowledge Base: probably 300–600 tokens with strong respect for structural boundaries (headings, list items). Worth testing.

---

## 4.3 Embedding models

The model that turns text into a vector. Topic 01 covered the algorithm side (cosine similarity); this is the model side.

### Major options

| Model | Type | Notes |
|---|---|---|
| **OpenAI `text-embedding-3-small/large`** | Closed, API | 1536 dim (small) / 3072 (large). Strong baseline. ~$0.02/M tokens. |
| **Cohere `embed-multilingual-v3.0`** | Closed, API | Excellent multilingual (100+ languages). 1024 dim. Critical for French/Arabic. |
| **BGE family (`bge-small/base/large-en`)** | Open weights | Free; runs locally; competitive with OpenAI. English-strong. |
| **`bge-m3`** | Open weights | Multilingual; recent; competitive with Cohere. |
| **Voyage AI** | Closed, API | Often tops benchmarks; less mainstream. |
| **NV-Embed-v2** | Open weights | Top of MTEB leaderboard at points; large model. |

### Trade-offs

- **Quality**: hard to predict from leaderboards alone — task-specific.
- **Cost**: API embeddings are paid per token (cheap but adds up). Self-hosted is "free" but uses GPU/CPU.
- **Latency**: API calls are 50–200ms; local inference can be faster.
- **Dimension**: higher dimension ≠ better. 768–1024 is the sweet spot for most use cases.
- **Multilingual**: critical for Winston Wolf given French/Arabic content. **English-only models are a no-go** for Richbond's market.

For Winston Wolf: **Cohere multilingual or `bge-m3`** are the strong candidates. Worth A/B testing in Phase 2.

---

## 4.4 Vector databases

Stores embeddings and supports fast nearest-neighbor search. The landscape:

| Option | Notes |
|---|---|
| **Pinecone** | Managed cloud-only. Easy. Locked-in. |
| **Qdrant** | Open source + cloud. Very fast. Production-grade. |
| **Chroma** | Open source. Simple. Good for prototypes; less battle-tested for production. |
| **Weaviate** | Open source + cloud. Feature-rich. |
| **pgvector** (Postgres extension) | Lives inside Postgres. Lower performance than dedicated VDBs but huge operational simplicity (one database for everything). |
| **Milvus** | Open source. Heavy / production-scale. |
| **FAISS** | Library, not a server. Good for small in-memory cases. |

For Winston Wolf in Phase 1: **pgvector inside Postgres** is probably the right call. Reasons: keeps the architecture single-database (less ops), good enough performance for the volume Phase 1 will see (millions of chunks at most), and trivial to migrate to a dedicated VDB later if quality demands it. Avoids premature optimisation.

---

## 4.5 Retrieval tuning

The "retrieve top K chunks similar to the query" step has multiple knobs:

- **K** (how many chunks to fetch): too low = miss relevant content. Too high = LLM context gets noisy.
- **Similarity threshold**: filter out weak matches. Reduces noise but can cause "no results" on hard queries.
- **Hybrid retrieval**: combine dense (embeddings) + sparse (BM25) — see Topic 01. Improves quality across query types.
- **Re-ranking**: take top K, re-rank with a cross-encoder. Mentioned in Topic 01; very useful in RAG too.
- **Query rewriting**: have an LLM rewrite the user's query into a better retrieval query before embedding. Sometimes huge gains.
- **HyDE** (Hypothetical Document Embeddings): instead of embedding the query, have an LLM hallucinate a hypothetical answer, embed *that*, retrieve similar real documents. Counter-intuitive but works.

---

## 4.6 Why RAG fails

The most common failure modes:

| Failure | Cause | Mitigation |
|---|---|---|
| **Lost-in-the-middle** | LLMs attend less to context in the middle of long inputs | Reduce K; put critical chunks at start/end; use Anthropic's prompt-caching pattern |
| **Off-topic retrieval** | Embedding similarity matched style, not meaning | Re-ranking with cross-encoder; query rewriting |
| **Stale data** | Knowledge Base wasn't reindexed | Robust ingest pipeline; freshness metadata on chunks |
| **Chunking artifacts** | Bad chunk boundaries split key info | Better chunking strategy; overlap; structural awareness |
| **Wrong embedding model** | Multilingual or domain mismatch | A/B test embeddings on real queries |
| **Context dilution** | Too many chunks, too much noise | Lower K; better ranking; chunk re-ranking |
| **Hallucinated synthesis** | LLM ignores retrieved chunks and makes things up | Tighter system prompt requiring citations; fact-check step |

The "hallucinated synthesis" one is shared with Topic 03 — an LLM with retrieval can still ignore the retrieved facts. Citations and verification are non-negotiable for production.

---

## 4.7 RAG vs. fine-tuning vs. long context

When NOT to use RAG:

- If the knowledge base is small enough to fit in a long-context model (Gemini 2M tokens, Claude 1M tokens), you can skip RAG entirely and just stuff everything into context. Simpler, sometimes better, more expensive.
- If the knowledge is truly stable and you need to internalise it, fine-tuning may be more appropriate (rare; expensive; fragile).
- If the knowledge needs to be applied as a *style* rather than as *facts*, fine-tuning is better.

For Winston Wolf: RAG is right because (a) the Knowledge Base will grow over time, (b) it's per-tenant data, fine-tuning per tenant is impractical, (c) it's facts not style.

---

## 4.8 Open questions for Winston Wolf

- **What goes IN the Knowledge Base?** Customer product catalog, industry research, past campaign templates, outbound playbooks — needs a clearer Phase 2 spec. Probably driven by what Outreach actually needs.
- **Multilingual embedding choice.** Cohere multilingual vs `bge-m3` — bake-off needed.
- **Chunk boundaries for the kinds of docs we'll ingest.** Customer docs are often messy (PDFs, web pages, manuals). May need LLM-based chunking for the worst cases.
- **Vector DB choice.** pgvector for v1 is the bet; verify pgvector handles the expected scale.
- **Query rewriting / HyDE worth implementing in v1?** Probably no — start simple, add if quality is bad.
- **How does the Knowledge Base interact with Scout?** Scout might benefit from per-tenant knowledge ("this tenant prefers X kind of leads"), or it might be Outreach-only. Architectural question for later.

---

## 4.9 References for Phase 2

- *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"* (Lewis et al., 2020) — the original RAG paper.
- *"Lost in the Middle: How Language Models Use Long Contexts"* (Liu et al., 2023) — important caveat to "just use more context."
- *"Precise Zero-Shot Dense Retrieval without Relevance Labels"* (Gao et al., 2022) — the HyDE paper.
- Anthropic's prompt-caching docs (RAG-specific patterns).
- Pinecone, Qdrant, Weaviate engineering blogs — practical chunking and retrieval guides.
- Massive Text Embedding Benchmark (MTEB) leaderboard — for current embedding model comparisons.
- *"Late Chunking"* (Mar 2024 paper) — newer chunking approach.

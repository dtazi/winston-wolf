# Topic 01 — Search algorithms

**Status**: Phase 1 stub (landscape level). Will deepen in Phase 2 with hands-on prototypes.

## Why this matters for Winston Wolf

Lead discovery is fundamentally a **search problem**: given a description of an Ideal Customer Profile, find people or companies that match. The algorithms underneath search determine *what kinds of matches the system can find* — exact keyword matches (sparse), conceptual matches (dense), or both.

Even though Winston Wolf will mostly call external services (Tavily, Brave, Apollo, etc.) rather than running its own search index, we need to understand what these services are doing internally. Without that, we can't reason about *why* one returns better results than another, what each is good and bad at, or where to layer additional logic on top.

---

## 1.1 Sparse retrieval — BM25 and TF-IDF

The classical approach. Documents are matched by their **discrete words (terms)**.

**TF-IDF** (Term Frequency × Inverse Document Frequency) was the foundational idea: a document is more relevant to a query if (a) it contains the query's words frequently, and (b) those words are *rare* across the corpus (rare = informative).

**BM25** (Best Matching 25) is the modern refinement, used in Elasticsearch, Lucene, and basically every search system from 1995 to 2018. It's TF-IDF with smarter saturation curves and document-length normalisation. BM25 is still extremely strong for keyword-heavy queries.

**Strengths:**
- Fast, well-understood, no neural networks needed.
- Works well on rare or specialised vocabulary.
- Predictable and debuggable — you can read why a document scored what it did.

**Weaknesses:**
- Misses synonyms and conceptual matches ("CEO" vs "Chief Executive Officer").
- Vocabulary mismatch between query and documents kills recall.
- No semantic understanding.

**For Winston Wolf:** BM25 is what most search engines fall back to when neural retrieval fails. Even if we're calling external APIs, understanding BM25 helps us write queries that work well against keyword-based systems.

---

## 1.2 Dense retrieval — vector embeddings

The neural approach. Queries and documents are converted to **high-dimensional vectors** by an embedding model, then matched by **cosine similarity** (or dot product).

**How it works:**
- Pick an embedding model (OpenAI `text-embedding-3-small`, Cohere `embed-multilingual-v3`, BGE-small-en, etc.).
- Each document → 384/768/1536-dimensional float vector.
- Query → same kind of vector.
- "Most similar" = vectors closest in cosine angle.

**Strengths:**
- Captures semantic similarity across vocabulary mismatches.
- Matches "head of marketing" with "VP marketing" even when words differ.
- Multilingual models can match across languages.

**Weaknesses:**
- Quality is *entirely* dependent on the embedding model.
- Costs money + adds latency (one embedding call per query, plus pre-computed embeddings for all documents).
- Results can feel "fuzzy" — an embedding can match on the wrong axis (style instead of meaning).
- Rare or specialised vocabulary may not embed well.

**For Winston Wolf:** Critical for matching conceptual descriptions ("decision-makers in plastics manufacturing") to noisy real-world data. Embedding model choice matters a lot. **Open question:** does multilingual matter for Moroccan / French content?

---

## 1.3 Hybrid retrieval — sparse + dense combined

Production-grade search systems almost always run **both** sparse and dense, then merge results. The dominant industry pattern in 2025–2026.

**Combination methods:**
- **RRF (Reciprocal Rank Fusion):** merge two ranked lists by summing `1/(k + rank)` for each. Simple, parameter-light, robust.
- **Linear combination:** weighted score-sum across both methods.
- **Two-stage:** dense for initial broad retrieval, sparse for filtering, or vice versa.

**Strengths:**
- Best of both worlds — keyword precision *and* semantic recall.
- Robust to query types neither method alone handles well.
- Industry standard for production B2B search.

**Weaknesses:**
- More compute, more code, more tuning.
- The combination weights are themselves a hyperparameter to tune.

**For Winston Wolf:** likely the right shape for the eventual production search layer, especially for finding leads where the user's brief doesn't match the data's vocabulary exactly.

---

## 1.4 Reranking — improving the top results

After initial retrieval (sparse / dense / hybrid), the top N candidates can be **re-ranked** with a more expensive model that looks at each candidate in detail.

**Methods:**
- **Cross-encoders** — BERT-style models that take `(query, document)` pairs and output a relevance score. Slower than dense retrieval but much higher quality. Examples: `ms-marco-MiniLM-L-6-v2`, `bge-reranker-base`.
- **LLM-based reranking** — send the top N candidates to an LLM along with the query, ask it to rank them or filter. Most expensive, often best quality. Increasingly common in production agents.

**Strengths:**
- Significantly improves quality of *top* results.
- LLM reranking captures nuance and reasoning no embedding can.
- Can also do filtering ("which of these are actual decision-makers?").

**Weaknesses:**
- Slow — each candidate is one model call.
- Expensive at scale.
- Diminishing returns past top 5–10.

**For Winston Wolf:** very likely useful. The Richbond test scenario — "did the system surface the right *people*?" — is exactly where reranking helps. After retrieval finds 50 plausible candidates, an LLM rerank can pick the 5 most-likely-correct.

---

## 1.5 Open questions for Winston Wolf

These need answers before we commit to architecture.

- **Does Winston Wolf even need its own retrieval layer**, or do we just rely on external services (Tavily, Brave, Apollo) that already have their own retrieval inside? Likely a hybrid: external services find a candidate pool, Winston Wolf reranks/filters.
- **Which embedding model?** OpenAI? BGE? Cohere multilingual? Quality varies and so does cost. Hands-on test in Phase 2.
- **How important is multilingual?** Richbond's prospects are in French / Moroccan-Arabic contexts. Most embedding models are English-strong, multilingual-weaker.
- **Is reranking with an LLM cost-justifiable** at the candidate-volume Phase 1 will see? Probably yes given small volumes; needs pricing math.
- **Do we need any sparse retrieval at all in v1**, or can we lean entirely on dense + LLM rerank?

---

## References to read in Phase 2

- *"Pretrained Transformers for Text Ranking: BERT and Beyond"* (Lin, Nogueira, Yates) — the canonical reference on dense retrieval and reranking.
- BGE family of embedding models — Hugging Face docs.
- ColBERT — late-interaction retrieval, useful as a hybrid of dense and sparse intuitions.
- Pinecone / Qdrant / Chroma vector DB docs (Topic 04 territory but adjacent).
- Reciprocal Rank Fusion — original paper (Cormack et al., 2009) is short and clear.

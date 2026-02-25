# Code Guide — Navigating the Project

This guide helps you understand and navigate the codebase. Each file has a module-level docstring; this document ties them together.

---

## Pipeline Flow

```
scripts/download_financial_docs.py  →  sec-edgar-filings/*.txt
                                              ↓
src/tiny_rag/ingest.py: chunk → embed → store  →  pgvector (documents table)
                                              ↓
src/tiny_rag/retrieve.py: embed query → SELECT by similarity  →  top-k chunks
                                              ↓
src/tiny_rag/rag.py: build prompt → Ollama  →  answer with citations
                                              ↓
src/tiny_rag/api.py: GET /ask  →  JSON response
src/tiny_rag/eval.py: run all Q&A  →  eval_results.xlsx
```

---

## File-by-File Walkthrough

### src/tiny_rag/ingest.py

**Purpose:** Turn 10-K txt files into embedded chunks in pgvector.

| Function | What it does |
|----------|--------------|
| `find_filing_txt_files()` | Scans `sec-edgar-filings/{ticker}/10-K/*/full-submission.txt` |
| `load_txt(path)` | Reads file as UTF-8 text |
| `chunk_with_overlap(text, 400, 100)` | Token-based sliding window (tiktoken cl100k_base) |
| `embed_chunks(chunks)` | SentenceTransformer all-MiniLM-L6-v2 → 384-dim vectors |
| `init_pgvector(conn)` | CREATE EXTENSION vector, CREATE TABLE documents |
| `store_in_pgvector()` | INSERT chunks + embeddings |

**Config:** `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`, `DATABASE_URL`

---

### src/tiny_rag/retrieve.py

**Purpose:** Semantic search over stored chunks.

| Function | What it does |
|----------|--------------|
| `_get_embedding_model()` | Lazy-load and cache SentenceTransformer (avoids reload each query) |
| `embed_query(query)` | Encode query → 384-dim vector |
| `retrieve_context(query, k, ticker)` | pgvector `ORDER BY embedding <=> query LIMIT k`; optional `WHERE ticker = X` |

**Optimizations:** Model caching, logging suppression for BertModel warning.

---

### src/tiny_rag/rag.py

**Purpose:** End-to-end RAG: retrieve → prompt → LLM → answer.

| Function | What it does |
|----------|--------------|
| `infer_ticker_from_query(query)` | "Alphabet" → GOOGL, "Apple" → AAPL (TICKER_MAP) |
| `build_rag_prompt(query, contexts)` | Format context blocks [1], [2], ... + citation instructions |
| `call_ollama(prompt)` | ollama.chat(model="llama3.2") |
| `answer_with_rag(query, k, ticker)` | Full pipeline; returns `{answer, sources}` |

**Config:** `TICKER_MAP`, default `k=6`

---

### src/tiny_rag/api.py

**Purpose:** HTTP API for RAG queries.

| Endpoint | Params | Returns |
|----------|--------|---------|
| `GET /` | — | `{status: "ok", docs: "/docs"}` |
| `GET /ask` | `q`, `k`, `ticker` | `{answer, sources_count, ticker_filter}` |

Uses `rag.answer_with_rag()` and `rag.infer_ticker_from_query()`.

---

### src/tiny_rag/eval.py

**Purpose:** Evaluate RAG on 50 Q&A pairs, check keywords, export to Excel.

| Function | What it does |
|----------|--------------|
| `load_qa_pairs()` | Load eval_qa.json |
| `run_eval()` | For each: answer_with_rag → keyword check → record |
| `print_report()` | Summary + per-question details |
| `save_to_excel()` | Write eval_results.xlsx |

**eval_qa.json structure:**
```json
{"q": "What are Alphabet's main risks?", "ticker": "GOOGL", "expected_keywords": ["cybersecurity", "risk"]}
```

---

## Key Concepts

### Chunking (ingest.py)

- **Token-based:** tiktoken cl100k_base (same as GPT-4)
- **Fixed size:** 400 tokens per chunk
- **Overlap:** 100 tokens between consecutive chunks
- **Stride:** 300 tokens (400 − 100)

### Retrieval (retrieve.py)

- **Similarity:** pgvector `<=>` = cosine distance (lower = more similar)
- **Ticker filter:** Optional `WHERE ticker = 'GOOGL'` for company-specific questions

### RAG (rag.py)

- **Prompt:** Context blocks labeled [1], [2], ... + "Cite sources with [1], [2], etc."
- **LLM:** Ollama llama3.2 (local, no API key)

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (see .env.example) |
| `HF_TOKEN` | Hugging Face token (optional, for faster model downloads) |

---

## Adding a New Company

1. Add ticker to `scripts/download_financial_docs.py` (or download manually)
2. Run `python -m tiny_rag.ingest` (processes all filings in sec-edgar-filings/)
3. Add to `TICKER_MAP` in `src/tiny_rag/rag.py`: `"companyname": "TICKER"`
4. Add questions to `eval_qa.json` with `"ticker": "TICKER"`

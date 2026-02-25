# Code Guide — Implementation Reference

---

## Pipeline

```
scripts/download_financial_docs.py  →  sec-edgar-filings/*.txt
scripts/process_documents.py       →  sec-edgar-filings/processed/*.txt
                                              ↓
tiny_rag.ingest                    →  pgvector (documents)
                                              ↓
tiny_rag.retrieve                   →  top-k chunks
                                              ↓
tiny_rag.rag                       →  answer + citations
tiny_rag.api                       →  GET /ask
tiny_rag.eval                      →  eval_results.xlsx
```

---

## Modules

### tiny_rag.ingest

| Function | Signature | Purpose |
|----------|-----------|---------|
| `find_filing_txt_files()` | `() -> list[tuple[Path, str]]` | Scan sec-edgar-filings for full-submission.txt |
| `load_txt()` | `(path: Path) -> str` | Read file |
| `chunk_with_overlap()` | `(text, chunk_size, overlap) -> list[str]` | Token-based sliding window |
| `embed_chunks()` | `(chunks: list[str]) -> list[list[float]]` | SentenceTransformer encode |
| `store_in_pgvector()` | `(chunks, embeddings, ticker, source) -> None` | INSERT into documents |
| `ingest_all()` | `() -> None` | Full pipeline |

**Config:** `CHUNK_SIZE_TOKENS=400`, `CHUNK_OVERLAP_TOKENS=100`, `DATABASE_URL`

---

### tiny_rag.retrieve

| Function | Signature | Purpose |
|----------|-----------|---------|
| `embed_query()` | `(query: str) -> list[float]` | Encode query |
| `retrieve_context()` | `(query, k=5, ticker=None) -> list[dict]` | pgvector `<=>` search |

**Returns:** `[{"content", "ticker", "source"}, ...]`

---

### tiny_rag.rag

| Function | Signature | Purpose |
|----------|-----------|---------|
| `answer_with_rag()` | `(query, k=5, ticker=None) -> dict` | Full RAG pipeline |
| `infer_ticker_from_query()` | `(query: str) -> str \| None` | Map company name → ticker |
| `build_rag_prompt()` | `(query, contexts) -> str` | Format prompt |
| `call_ollama()` | `(prompt, model="llama3.2") -> str` | LLM call |

**Config:** `TICKER_MAP` (rag.py)

---

### tiny_rag.api

| Endpoint | Params | Response |
|----------|--------|----------|
| `GET /` | — | `{status, docs}` |
| `GET /health` | — | `{status, database, ollama}` — 200 if healthy, 503 if not |
| `GET /ask` | `q`, `k`, `ticker` | `{answer, sources_count, ticker_filter}` |

---

### tiny_rag.eval

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_qa_pairs()` | `(path="eval_qa.json") -> list[dict]` | Load Q&A |
| `run_eval()` | `(qa_pairs, k=6) -> list[dict]` | Run RAG + keyword check |
| `save_to_excel()` | `(results, path) -> None` | Export |

**eval_qa.json:** `{"q": str, "ticker": str?, "expected_keywords": list[str]?}`

---

## Retries

`retry_config.py` provides `@retry_db` and `@retry_ollama` decorators. Applied to:
- `retrieve_context` (DB)
- `store_in_pgvector` (DB)
- `call_ollama` (LLM)

Config: 3 attempts, exponential backoff 1s–10s.

---

## Environment

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL + pgvector |
| `HF_TOKEN` | Hugging Face (optional) |

---

## Extending

**Add ticker:** Update `TICKER_MAP` in `rag.py`; add to `download_financial_docs.py` TICKERS.

**Add company to eval:** Append to `eval_qa.json` with `q`, `ticker`, `expected_keywords`.

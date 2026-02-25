# Tiny RAG — Financial Documents

**Status:** Complete — Full pipeline: ingest → retrieve → RAG → API → evaluation.

**Purpose:** This project is for **learning** — to understand RAG pipelines, chunking, embeddings, and retrieval. It is not production-ready. See [Learning Purpose & Gaps vs Production](#learning-purpose--gaps-vs-production) for what differs from enterprise use and what to learn next.

A RAG (Retrieval Augmented Generation) project for financial documents (10-K filings). Uses **pgvector**, **Ollama**, and **SEC EDGAR** data. Designed to be AWS-ready later (Bedrock, pgvector on RDS).

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [How the Project Was Built](#how-the-project-was-built)
3. [Project Structure & File Guide](#project-structure--file-guide)
4. [Tech Stack](#tech-stack)
5. [Setup](#setup)
6. [Data & Documents](#data--documents)
7. [Run](#run)
8. [Chunking Method](#chunking-method)
9. [RAG Optimizations](#rag-optimizations)
10. [API](#api)
11. [Evaluation](#evaluation)
12. [Troubleshooting](#troubleshooting)
13. [Learning Purpose & Gaps vs Production](#learning-purpose--gaps-vs-production)
14. [What's Next](#whats-next)
15. [Git Workflow](#git-workflow)

See [docs/CODE_GUIDE.md](docs/CODE_GUIDE.md) for a detailed file-by-file code walkthrough.

---

## What This Project Does

1. **Download** 10-K filings from SEC EDGAR (Apple, Alphabet)
2. **Extract** text from the full submission (or convert PDF/HTML/XML via `scripts/process_documents.py`)
3. **Chunk** text with token-based overlap (400 tokens, 100 overlap)
4. **Embed** chunks with SentenceTransformers and **store** in pgvector
5. **Retrieve** top-k chunks by semantic similarity
6. **Answer** via Ollama LLM with citations
7. **Serve** via FastAPI `/ask` endpoint
8. **Evaluate** on 50 Q&A pairs with keyword checks and Excel export

---

## How the Project Was Built

### Phase 1: Data & Ingestion

1. Downloaded 10-K filings via `scripts/download_financial_docs.py` → `sec-edgar-filings/{ticker}/10-K/.../full-submission.txt`
2. Extended `tiny_rag.ingest` to load txt, chunk with tiktoken, embed with SentenceTransformers, store in pgvector
3. Set up pgvector (Docker or local PostgreSQL) with `CREATE EXTENSION vector` and `documents` table

### Phase 2: Retrieval & RAG

4. Implemented `tiny_rag.retrieve` with `retrieve_context(query, k)` — vector similarity search
5. Implemented `tiny_rag.rag` with `answer_with_rag()` — retrieve → build prompt → call Ollama → return answer with citations

### Phase 3: Optimizations

6. **Increased k** from 3 to 6 for more context
7. **Ticker filtering** — added `TICKER_MAP` and `infer_ticker_from_query()` so "Alphabet's risks" restricts retrieval to GOOGL
8. **Model caching** — SentenceTransformer loads once and is reused in `retrieve.py`
9. **Suppressed BertModel warning** — `logging.getLogger("sentence_transformers").setLevel(logging.WARNING)`

### Phase 4: API & Evaluation

10. Added FastAPI `tiny_rag.api` with `/ask` endpoint (query params: `q`, `k`, `ticker`)
11. Created `eval_qa.json` with 50 Q&A pairs (25 GOOGL, 25 AAPL) and `expected_keywords`
12. Implemented `tiny_rag.eval` — runs RAG on each question, checks keywords, saves to `eval_results.xlsx`
13. Added progress output in eval for long runs

### Phase 5: Configuration

14. Added `.env` and `.env.example` for `HF_TOKEN`, `DATABASE_URL`
15. Added `python-dotenv` to load env vars in all scripts

---

## Project Structure & File Guide

```
tiny-rag-warmup/
├── README.md
├── docs/
│   └── CODE_GUIDE.md             # File-by-file code walkthrough
├── src/
│   └── tiny_rag/                 # Python package
│       ├── __init__.py
│       ├── ingest.py             # Chunk, embed, store in pgvector
│       ├── retrieve.py           # Vector search: embed query, SELECT by similarity
│       ├── rag.py                # RAG pipeline: retrieve → prompt → Ollama → answer
│       ├── api.py                # FastAPI /ask endpoint
│       └── eval.py               # Evaluation script (50 Q&A, keyword check, Excel)
├── scripts/                     # CLI entry points
│   ├── download_financial_docs.py  # SEC EDGAR download → full-submission.txt
│   └── process_documents.py       # Raw PDF/HTML/XML → txt conversion
├── sec-edgar-filings/            # Downloaded 10-Ks
│   ├── AAPL/10-K/.../full-submission.txt
│   ├── GOOGL/10-K/.../full-submission.txt
│   └── processed/               # Output from process_documents.py
├── data/                         # Raw files (PDF, XML, HTML) for process_documents.py
├── eval_qa.json                  # 50 Q&A pairs with expected_keywords
├── eval_results.xlsx             # Output from eval (generated)
├── .env                          # Secrets (not committed). Copy from .env.example
├── .env.example                  # Template for HF_TOKEN, DATABASE_URL
├── requirements.txt
└── pyproject.toml
```

### File-by-File Guide

| File | Purpose | Key Functions |
|------|---------|---------------|
| **tiny_rag.ingest** | Load 10-K txt, chunk, embed, store | `chunk_with_overlap()`, `embed_chunks()`, `store_in_pgvector()` |
| **tiny_rag.retrieve** | Embed query, search pgvector | `embed_query()`, `retrieve_context()` |
| **tiny_rag.rag** | Build prompt, call Ollama | `build_rag_prompt()`, `answer_with_rag()`, `infer_ticker_from_query()` |
| **tiny_rag.api** | HTTP API | `GET /ask?q=...&k=6&ticker=GOOGL` |
| **tiny_rag.eval** | Run eval, keyword check, Excel | `run_eval()`, `save_to_excel()` |

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Vector DB** | pgvector | Production-ready, SQL, AWS RDS compatible |
| **LLM** | Ollama (llama3.2) | Free, local, no API key |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) | Free, 384-dim, good quality |
| **Chunking** | tiktoken (cl100k_base) | Token-based, aligns with LLM context |
| **API** | FastAPI + uvicorn | Async, auto docs at /docs |

---

## Setup

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .            # Install tiny_rag package in editable mode
```

### 2. PostgreSQL + pgvector

**Option A: Docker (recommended)**

```bash
docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
docker exec -it pgvector psql -U postgres -c "CREATE DATABASE rag_db;"
docker exec -it pgvector psql -U postgres -d rag_db -c "CREATE EXTENSION vector;"
```

**Option B: Homebrew (macOS)**

```bash
brew install postgresql@16
# Create DB and extension manually
createdb rag_db
psql -d rag_db -c "CREATE EXTENSION vector;"
```

### 3. Ollama

```bash
ollama pull llama3.2
```

### 4. Environment variables

```bash
cp .env.example .env
# Edit .env:
#   HF_TOKEN=your-hf-token-here          # Optional, for faster model downloads
#   DATABASE_URL=postgresql://...        # See Troubleshooting for role/db
```

**DATABASE_URL formats:**
- Docker: `postgresql://postgres:postgres@localhost:5432/rag_db`
- Homebrew (macOS): `postgresql://YOUR_USERNAME@localhost:5432/rag_db` (use `whoami` for username)

---

## Data & Documents

### SEC EDGAR — Where to Get Documents

**SEC EDGAR** hosts all public company filings in the US. It's free and requires no API key.

- **Website:** [sec.gov/edgar](https://www.sec.gov/edgar)
- **Search:** [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar)

| Filing | Description |
|--------|-------------|
| **10-K** | Annual report — full-year financials, risk factors, MD&A |
| **10-Q** | Quarterly report — quarterly financials |
| **8-K** | Current report — material events (earnings, acquisitions) |

For RAG, **10-K** is usually the best starting point.

### Two Pipeline Paths

**Path A: Direct (recommended)** — `scripts/download_financial_docs.py` gives you txt directly:

```bash
python scripts/download_financial_docs.py
```

Output: `sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt` — ready for RAG.

**Path B: Raw → Process** — For PDF, XML, or HTML from other sources:

```bash
# 1. Put raw files in data/ (XML, PDF, HTML)
# 2. Run the processor
python scripts/process_documents.py
```

Output: `sec-edgar-filings/processed/*.txt`. Avoid "Inline XBRL Viewer" XML — use the main document.

**Manual download:** Go to [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar) → search by ticker → Filings → 10-K → Documents → download main `.htm` → save to `data/` → run `python scripts/process_documents.py`.

### Ingestion Flow

```
ingest.py:
  find_filing_txt_files()     → list of (path, ticker)
  load_txt(path)              → full text
  chunk_with_overlap(text)    → list of chunks (tiktoken)
  embed_chunks(chunks)        → list of embeddings (SentenceTransformers)
  store_in_pgvector(...)      → INSERT into documents table

retrieve.py:
  embed_query(query)          → query embedding
  retrieve_context(query, k)  → SELECT ... ORDER BY embedding <=> query LIMIT k
```

### Switching to AWS Later

When you deploy to AWS: replace Ollama with Bedrock for LLM; use Bedrock Titan Embeddings; point to pgvector on RDS (same API, different connection).

---

## Run

### Full pipeline (first time)

```bash
# 1. Download 10-Ks (edit COMPANY_NAME, COMPANY_EMAIL in script first)
python scripts/download_financial_docs.py

# 2. Ingest: chunk, embed, store
python -m tiny_rag.ingest

# 3. Test RAG (CLI)
python -m tiny_rag.rag "What are Alphabet's main risks?"

# 4. Start API server
uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001

# 5. Run evaluation
python -m tiny_rag.eval
```

### Quick test

```bash
# If already ingested
python -m tiny_rag.rag "What are Apple's main risk factors?"
curl "http://localhost:8001/ask?q=What%20are%20Alphabet%27s%20main%20risks%3F"
```

---

## Chunking Method

The project uses **token-based fixed-size chunking with overlap**.

| Setting | Value | Reason |
|---------|-------|--------|
| **Chunk size** | 400 tokens | ~300–400 words; fits embedding limits; enough context |
| **Overlap** | 100 tokens | Prevents cutting sentences; keeps related content together |
| **Tokenizer** | tiktoken `cl100k_base` | Same as GPT-4; accurate token counting |
| **Stride** | 300 tokens | 400 − 100; sliding window |

**Why token-based?** Tokens align with how LLMs process text. Character counts don't map to context limits.

**Why overlap?** 10-K risk factors span paragraphs. Overlap reduces losing key phrases at chunk boundaries.

**Why fixed size?** Simple, robust, works across mixed document structure (HTML, tables, narrative).

---

## RAG Optimizations

| Optimization | What | Benefit |
|--------------|------|---------|
| **k=6** | Retrieve 6 chunks instead of 3 | More context, better answers |
| **Ticker filtering** | `infer_ticker_from_query()` maps "Alphabet" → GOOGL | Focused retrieval when company is known |
| **Model caching** | `_get_embedding_model()` loads once | Faster repeated queries |
| **Logging suppression** | `sentence_transformers` set to WARNING | Cleaner output (no BertModel UNEXPECTED) |

---

## API

**Start server:**
```bash
uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001
```

**Endpoints:**
- `GET /` — Health check
- `GET /ask?q=...` — RAG query
- `GET /docs` — Swagger UI

**Query parameters:**
- `q` (required): Your question
- `k` (optional, default 6): Chunks to retrieve (1–20)
- `ticker` (optional): Filter by ticker (GOOGL, AAPL). If omitted, inferred from query.

**Example:**
```bash
curl "http://localhost:8001/ask?q=What%20are%20Alphabet%27s%20main%20risks%3F"
```

**Port conflict:** If port 8000 is in use, use 8001 or run `lsof -i :8000` and `kill <PID>`.

---

## Evaluation

**Run:**
```bash
python -m tiny_rag.eval
```

**What it does:**
1. Loads 50 Q&A pairs from `eval_qa.json`
2. Runs each through `answer_with_rag()`
3. Checks if answer contains `expected_keywords` (PASS/FAIL)
4. Prints progress `[1/50] ... -> done in 12.3s`
5. Saves to `eval_results.xlsx` (question, answer, ticker, sources_count, time_sec, passed, keywords_found, keywords_missed)

**expected_keywords:** You define these in `eval_qa.json`. The LLM doesn't see them; the eval script checks if the answer contains them. Add more questions by appending to `eval_qa.json`.

**Runtime:** ~10–15 minutes for 50 questions (each ~10–20 seconds).

---

## Troubleshooting

### `role "postgres" does not exist`

On Homebrew PostgreSQL, the default role is your macOS username, not `postgres`. Set:
```bash
export DATABASE_URL="postgresql://$(whoami)@localhost:5432/rag_db"
```
Or add to `.env`.

### `database "rag_db" does not exist`

Create it:
```bash
createdb rag_db
# Or with Docker: docker exec -it pgvector psql -U postgres -c "CREATE DATABASE rag_db;"
```

### `vector type not found`

Enable the pgvector extension:
```bash
psql -d rag_db -c "CREATE EXTENSION vector;"
```

### `relation "documents" does not exist`

Run ingestion:
```bash
python -m tiny_rag.ingest
```

### Port 8000 already in use

Use a different port:
```bash
uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001
```

### Eval seems stuck

Eval runs 50 questions; each takes ~10–20 seconds. Total ~10–15 minutes. Progress is printed as `[1/50]`, `[2/50]`, etc.

---

## Learning Purpose & Gaps vs Production

This project is for **learning and prototyping**, not production. Below is what differs from enterprise RAG systems and what to study next.

### Gaps vs. Production

| Area | This Project | Production Expectation | What to Learn Next |
|------|--------------|------------------------|--------------------|
| **Auth** | No auth on API | API keys, OAuth, SSO | FastAPI middleware, JWT, OAuth2 |
| **Security** | Secrets in `.env` | Secret manager (AWS Secrets Manager, Vault) | Secret management, least privilege |
| **Reliability** | Single process, no retries | Load balancing, retries, circuit breakers | Resilience patterns, `tenacity`, `httpx` retries |
| **Scalability** | In-process embedding | Separate embedding service | Microservices, async workers |
| **LLM** | Local Ollama | Managed LLM (Bedrock, Azure OpenAI) with SLAs | AWS Bedrock, OpenAI API, fallbacks |
| **Database** | Local pgvector | Managed pgvector (RDS) | RDS, connection pooling |
| **Ingestion** | Manual `python ingest.py` | Scheduled pipelines, incremental updates | Airflow, Prefect, event-driven ingestion |
| **Observability** | Minimal logging | Structured logs, metrics, tracing | OpenTelemetry, Prometheus, CloudWatch |
| **Evaluation** | Keyword checks only | LLM-as-judge, human review, A/B tests | RAGAS, continuous eval, feedback loops |
| **Compliance** | None | PII handling, audit logs, data residency | Data governance, retention policies |

### Suggested Learning Path

1. **Must-haves for production:** Auth, secret management, error handling, structured logging
2. **Deployment:** Docker, container orchestration (ECS, EKS), CI/CD
3. **Managed services:** Bedrock or Azure OpenAI for LLM; RDS with pgvector
4. **Ingestion pipeline:** Scheduled jobs, incremental indexing, document versioning
5. **Observability:** Metrics, tracing, alerting
6. **Advanced RAG:** Re-ranking, hybrid search, query expansion

---

## What's Next

- [x] Extend `ingest.py`: load txt, chunk, embed, store in pgvector
- [x] Implement `retrieve_context()` in `retrieve.py`
- [x] Implement `answer_with_rag()` in `rag.py`
- [x] Add FastAPI `/ask` endpoint
- [x] Evaluation script + 50 Q&A pairs + Excel export
- [ ] Re-ranking with cross-encoder
- [ ] Dockerize API
- [ ] AWS: Bedrock embeddings, pgvector on RDS

---

## Git Workflow

| Command | Purpose |
|---------|---------|
| `git add .` | Stage changes |
| `git commit -m "message"` | Commit |
| `git push` | Push to remote |

### Branch Setup

| Branch | Purpose |
|--------|---------|
| **main** | Original baseline (PDF + simple chunk) |
| **original** | Backup of original (same as main) |
| **feature/extended** | Extended pipeline; active development |
| **feature/organized** | Current branch with organized docs |

### Workflow

```bash
# Work on a feature branch
git checkout feature/organized   # or feature/extended

# When ready to merge to main
git checkout main
git merge feature/organized
git push origin main
```

### Verify

```bash
git branch -a
git log --oneline -3
```

# Tiny RAG — Financial Documents

RAG pipeline for SEC 10-K filings. Ingest → vector store (pgvector) → retrieve → LLM (Ollama) → FastAPI.

---

## Requirements

- Python 3.10+
- PostgreSQL 16+ with pgvector
- Ollama (llama3.2)
- Docker & Docker Compose (for database)

---

## Quick Start — Full Command Reference

This section lists all commands to run the project from scratch. Use `pip3` and `python3`.

### 1. Clone and setup environment

```bash
cd tiny-rag-warmup
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip3 install -r requirements.txt
pip3 install -e .
```

### 2. Edit download script (required)

Edit `scripts/download_financial_docs.py` and set:

- `COMPANY_NAME` — Your company or institution name (SEC requires this)
- `COMPANY_EMAIL` — Your email (SEC requires this)

### 3. Download 10-K filings

```bash
python3 scripts/download_financial_docs.py
```

This downloads SEC 10-K filings and extracts text to `sec-edgar-filings/` and `data/`.

### 4. Start database (Docker)

```bash
docker compose up -d db
```

PostgreSQL with pgvector runs on **port 5433** (avoids conflict with local Postgres on 5432).

### 5. Ingest documents (chunk, embed, store)

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/rag_db"
python3 -m tiny_rag.ingest
```

Run once after download. May take a few minutes for embedding.

### 6. Pull Ollama model

```bash
ollama pull llama3.2
```

### 7. Start API server

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/rag_db"
uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001
```

Keep this terminal open. API runs on **http://localhost:8001**.

### 8. Test (in another terminal)

```bash
# Health check
curl http://localhost:8001/health

# Ask a question
curl "http://localhost:8001/ask?q=What%20are%20Alphabet%27s%20main%20risks%3F"
```

### 9. Optional: run evaluation

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/rag_db"
python3 -m tiny_rag.eval
```

Produces `eval_results.xlsx`.

---

## Alternative: Docker Compose (DB + API)

If you prefer running the API in Docker:

```bash
# 1. Setup (one-time)
python3 -m venv .venv && source .venv/bin/activate
pip3 install -r requirements.txt && pip3 install -e .

# 2. Edit COMPANY_NAME, COMPANY_EMAIL in scripts/download_financial_docs.py
python3 scripts/download_financial_docs.py

# 3. Start DB + API
docker compose up -d --build

# 4. Ingest (from host — Docker API may have connectivity issues on some setups)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/rag_db"
python3 -m tiny_rag.ingest

# 5. Test API (Docker)
curl http://localhost:8000/health
curl "http://localhost:8000/ask?q=What%20are%20Alphabet%27s%20main%20risks%3F"

# If Docker API returns empty response, run API locally instead:
# docker compose stop api
# export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/rag_db"
# uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001
```

---

## Alternative: Fully local (no Docker)

```bash
# 1. Environment
python3 -m venv .venv && source .venv/bin/activate
pip3 install -r requirements.txt && pip3 install -e .

# 2. Database (Docker)
docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
docker exec -it pgvector psql -U postgres -c "CREATE DATABASE rag_db;"
docker exec -it pgvector psql -U postgres -d rag_db -c "CREATE EXTENSION vector;"

# 3. Config
cp .env.example .env
# Set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_db

# 4. Download, ingest, run
ollama pull llama3.2
python3 scripts/download_financial_docs.py   # Edit COMPANY_NAME, COMPANY_EMAIL first
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag_db"
python3 -m tiny_rag.ingest
uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8000

# 5. Test (another terminal)
curl http://localhost:8000/health
curl "http://localhost:8000/ask?q=What%20are%20Alphabet%27s%20main%20risks%3F"

# 6. Optional: eval
python3 -m tiny_rag.eval
```

---

## Project Structure

```
tiny-rag-warmup/
├── src/tiny_rag/          # Package: ingest, retrieve, rag, api, eval
├── scripts/               # download_financial_docs, process_documents
├── docs/CODE_GUIDE.md     # API reference
├── sec-edgar-filings/     # Downloaded 10-Ks (gitignored)
├── data/                  # Raw PDF/HTML/XML input (gitignored)
├── eval_qa.json           # Eval Q&A pairs
├── pyproject.toml
└── requirements.txt
```

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `API_KEY` | No | API key for `/ask`. If empty, auth disabled (dev) |
| `LOG_FORMAT` | No | `console` (default) or `json` |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `HF_TOKEN` | No | Hugging Face token (faster model downloads) |

**DATABASE_URL examples:**
- Docker Compose (port 5433): `postgresql://postgres:postgres@localhost:5433/rag_db`
- Local Postgres (port 5432): `postgresql://postgres:postgres@localhost:5432/rag_db`

---

## Commands Reference

| Command | Purpose |
|---------|---------|
| `python3 scripts/download_financial_docs.py` | Download 10-Ks from SEC EDGAR |
| `python3 scripts/process_documents.py` | Convert raw PDF/HTML/XML in `data/` → txt |
| `python3 -m tiny_rag.ingest` | Chunk, embed, store in pgvector |
| `python3 -m tiny_rag.rag "query"` | CLI RAG query |
| `uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001` | Start API |
| `python3 -m tiny_rag.eval` | Run eval suite → eval_results.xlsx |
| `pytest` | Run tests |
| `ruff check src/ tests/` | Lint |

---

## API

| Endpoint | Method | Params |
|----------|--------|--------|
| `/` | GET | Liveness |
| `/live` | GET | Minimal liveness (no DB/Ollama) |
| `/health` | GET | Readiness (DB + Ollama) |
| `/ask` | GET | `q` (required), `k` (default 6), `ticker` (optional) |
| `/docs` | GET | Swagger UI |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `role "postgres" does not exist` | Use `postgresql://$(whoami)@localhost:5432/rag_db` for local Postgres |
| `port 5432 already allocated` | Docker Compose uses 5433; use `localhost:5433` |
| `database "rag_db" does not exist` | `createdb rag_db` or Docker `CREATE DATABASE` |
| `vector type not found` | `psql -d rag_db -c "CREATE EXTENSION vector;"` |
| `relation "documents" does not exist` | Run `python3 -m tiny_rag.ingest` |
| `could not translate host name "db"` | Run ingest from host: `DATABASE_URL=postgresql://postgres:postgres@localhost:5433/rag_db python3 -m tiny_rag.ingest` |
| `Empty reply from server` (Docker API) | Run API locally: `uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001` |
| Port in use | Use different port: `uvicorn tiny_rag.api:app --port 8001` |

---

## Retries

DB and Ollama calls use tenacity retries (3 attempts, exponential backoff 1s–10s) for transient failures.

---

## Deployment Notes

- **Secrets:** Use a secret manager (AWS Secrets Manager, Vault); avoid `.env` in production.
- **Database:** Use managed pgvector (RDS, Neon, Supabase).
- **LLM:** Replace Ollama with Bedrock/OpenAI for production SLAs.
- **API:** Add auth (API keys, OAuth), rate limiting, structured logging.
- **Ingestion:** Schedule via cron, Airflow, or event-driven pipeline.

See [docs/PRODUCTION_OPTIMIZATIONS.md](docs/PRODUCTION_OPTIMIZATIONS.md) for a comprehensive overview. See [docs/CODE_GUIDE.md](docs/CODE_GUIDE.md), [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md), [docs/AUTH_GUIDE.md](docs/AUTH_GUIDE.md), [docs/LOGGING_GUIDE.md](docs/LOGGING_GUIDE.md), [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md), [docs/CI_GUIDE.md](docs/CI_GUIDE.md).

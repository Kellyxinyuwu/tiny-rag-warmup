# Tiny RAG — Financial Documents

RAG pipeline for SEC 10-K filings. Ingest → vector store (pgvector) → retrieve → LLM (Ollama) → FastAPI.

---

## Requirements

- Python 3.10+
- PostgreSQL 16+ with pgvector
- Ollama (llama3.2)

---

## Quick Start

```bash
# 1. Environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 2. Database (Docker)
docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
docker exec -it pgvector psql -U postgres -c "CREATE DATABASE rag_db;"
docker exec -it pgvector psql -U postgres -d rag_db -c "CREATE EXTENSION vector;"

# 3. Config
cp .env.example .env
# Set DATABASE_URL, HF_TOKEN (optional)

# 4. LLM
ollama pull llama3.2

# 5. Pipeline
python scripts/download_financial_docs.py   # Edit COMPANY_NAME, COMPANY_EMAIL first
python -m tiny_rag.ingest
uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8000
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
| `HF_TOKEN` | No | Hugging Face token (faster model downloads) |

**DATABASE_URL:** `postgresql://user:pass@host:5432/rag_db`

---

## Commands

| Command | Purpose |
|---------|---------|
| `python scripts/download_financial_docs.py` | Download 10-Ks from SEC EDGAR |
| `python scripts/process_documents.py` | Convert raw PDF/HTML/XML in `data/` → txt |
| `python -m tiny_rag.ingest` | Chunk, embed, store in pgvector |
| `python -m tiny_rag.rag "query"` | CLI RAG query |
| `uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8000` | Start API |
| `python -m tiny_rag.eval` | Run eval suite → eval_results.xlsx |

---

## API

| Endpoint | Method | Params |
|----------|--------|--------|
| `/` | GET | Health check |
| `/ask` | GET | `q` (required), `k` (default 6), `ticker` (optional) |
| `/docs` | GET | Swagger UI |

---

## Config Reference

| Setting | Location | Default |
|---------|----------|---------|
| Chunk size | `ingest.py` | 400 tokens |
| Chunk overlap | `ingest.py` | 100 tokens |
| Retrieval k | `rag.py`, API | 6 |
| Ticker map | `rag.py` | AAPL, GOOGL, MSFT, etc. |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `role "postgres" does not exist` | Use `postgresql://$(whoami)@localhost:5432/rag_db` |
| `database "rag_db" does not exist` | `createdb rag_db` or Docker `CREATE DATABASE` |
| `vector type not found` | `psql -d rag_db -c "CREATE EXTENSION vector;"` |
| `relation "documents" does not exist` | Run `python -m tiny_rag.ingest` |
| Port in use | `uvicorn tiny_rag.api:app --port 8001` |

---

## Deployment Notes

- **Secrets:** Use a secret manager (AWS Secrets Manager, Vault); avoid `.env` in production.
- **Database:** Use managed pgvector (RDS, Neon, Supabase).
- **LLM:** Replace Ollama with Bedrock/OpenAI for production SLAs.
- **API:** Add auth (API keys, OAuth), rate limiting, structured logging.
- **Ingestion:** Schedule via cron, Airflow, or event-driven pipeline.

See [docs/CODE_GUIDE.md](docs/CODE_GUIDE.md) for implementation details.

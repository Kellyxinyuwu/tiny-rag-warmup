# Ingestion & Retrieval Guide

## Prerequisites

1. **PostgreSQL + pgvector** (Docker):
   ```bash
   docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
   ```

2. **Create database**:
   ```bash
   docker exec -it pgvector psql -U postgres -c "CREATE DATABASE rag_db;"
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Connection

Copy `.env.example` to `.env` and set your values:

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL, HF_TOKEN, etc.
```

Or override with env: `export DATABASE_URL="postgresql://user:pass@host:5432/dbname"`

## Run Ingestion

```bash
python ingest.py
```

This will:
1. Find `full-submission.txt` in `sec-edgar-filings/AAPL/` and `GOOGL/`
2. Chunk with 400 tokens, 100 overlap
3. Embed with SentenceTransformers (all-MiniLM-L6-v2)
4. Store in pgvector `documents` table

## Run Retrieval

```bash
python retrieve.py "What are Apple's main risk factors?"
```

## Code Flow

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

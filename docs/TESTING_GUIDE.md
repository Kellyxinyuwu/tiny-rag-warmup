# Testing Guide

## Run tests

```bash
# Install dev deps
pip install -r requirements.txt
pip install pytest httpx

# Run all tests
pytest

# Verbose
pytest -v

# Specific file
pytest tests/test_rag.py -v
```

## Test structure

```
tests/
├── conftest.py      # Fixtures (TestClient)
├── test_rag.py      # Unit: infer_ticker_from_query, build_rag_prompt
├── test_ingest.py   # Unit: chunk_with_overlap, load_txt
└── test_api.py      # Integration: /, /health, /ask (mocked)
```

## What's tested

| Module | Tests |
|--------|-------|
| **rag** | Ticker inference (Alphabet→GOOGL, Apple→AAPL), prompt building |
| **ingest** | Chunking with overlap, load_txt |
| **api** | Root, health (mocked), ask (mocked) |

## Mocks

- `/ask` mocks `answer_with_rag` — no Ollama/DB needed
- `/health` mocks `check_database` and `check_ollama` for 200/503 cases

Tests run without PostgreSQL or Ollama.

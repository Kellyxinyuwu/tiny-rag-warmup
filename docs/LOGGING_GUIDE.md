# Structured Logging Guide

This project uses **structlog** for structured logging. Logs include timestamps, levels, and key-value fields for easier parsing and monitoring.

---

## Quick Reference

| Env var | Values | Default | Purpose |
|---------|--------|---------|---------|
| `LOG_FORMAT` | `console`, `json` | `console` | Output format |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Minimum log level |

---

## Output Formats

### Console (default)

Human-readable, colored output for local development:

```
2024-01-15T10:30:00.123Z [info    ] ingest_start        filings_count=2
2024-01-15T10:30:01.456Z [info    ] processing_ticker   ticker=AAPL
2024-01-15T10:30:02.789Z [info    ] loaded              ticker=AAPL chars=125000
```

### JSON (production)

One JSON object per line for log aggregators (CloudWatch, Datadog, etc.):

```json
{"event": "ingest_start", "filings_count": 2, "timestamp": "2024-01-15T10:30:00.123Z", "level": "info"}
{"event": "processing_ticker", "ticker": "AAPL", "timestamp": "2024-01-15T10:30:01.456Z", "level": "info"}
```

Set `LOG_FORMAT=json` in production.

---

## Request ID

For API requests, each request gets a `request_id` (UUID). It appears in:

- All logs during that request (via contextvars)
- Response header `X-Request-ID`

**Use case:** Trace a request across logs. If a client reports an error, they can send the `X-Request-ID` from the response; you search logs for that ID.

```bash
curl -v "http://localhost:8000/ask?q=test"
# Response headers include: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

## Usage in Code

```python
from tiny_rag.logging_config import get_logger

logger = get_logger(__name__)

logger.info("event_name", key1="value1", key2=123)
logger.warning("something_wrong", detail="...")
logger.error("failure", error=str(e))
```

**Convention:** Use `event` or the first positional arg as the event name; use keyword args for structured data.

---

## Log Events by Module

### ingest

| Event | Keys | When |
|-------|------|------|
| `ingest_start` | filings_count | Start of ingest |
| `processing_ticker` | ticker | Start processing a ticker |
| `loaded` | ticker, chars | File loaded |
| `chunked` | ticker, chunks | Chunking done |
| `embedded` | ticker, count | Embedding done |
| `stored` | ticker | Stored in DB |
| `ingest_complete` | — | All done |
| `no_filings_found` | hint | No files found (warning) |

### eval

| Event | Keys | When |
|-------|------|------|
| `eval_start` | questions | Start eval |
| `eval_progress` | index, total, question | Per-question start |
| `eval_done` | index, elapsed_sec | Per-question done |
| `eval_report` | total, passed, failed, no_check | Summary |
| `eval_result` | index, question, ticker, ... | Per-result detail |
| `eval_saved` | path | Excel saved |
| `eval_qa_not_found` | path | Config error |

### api

| Event | Keys | When |
|-------|------|------|
| `request_start` | method, path | Incoming request |
| `request_end` | status_code, elapsed_ms | Response sent |
| `ask_request` | query, k, ticker | /ask called |
| `ask_response` | sources | /ask completed |

### rag, retrieve

| Event | Keys | When |
|-------|------|------|
| `rag_query` | query, ticker | CLI query start |
| `rag_answer` | answer, sources | CLI answer |
| `retrieve_query` | query, results | CLI retrieve |
| `retrieve_result` | index, ticker, content_preview | Per-chunk |

---

## Docker

Add to `docker-compose.yml` for JSON logs in production:

```yaml
api:
  environment:
    LOG_FORMAT: json
    LOG_LEVEL: INFO
```

---

## Example: Search Logs by request_id

```bash
# If using JSON logs and jq
docker compose logs api 2>&1 | grep '550e8400-e29b-41d4-a716-446655440000'
```

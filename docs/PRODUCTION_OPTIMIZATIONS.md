# Production Optimizations — Comprehensive Guide

This document explains all optimizations implemented to make this project production-ready and enterprise-scale. Each section covers what was done, why it matters, and where to find the implementation.

---

## Overview

| # | Optimization | Purpose |
|---|--------------|---------|
| 1 | Docker | Reproducible deployment, portable environment |
| 2 | API authentication | Secure the API |
| 3 | Structured logging | Observability, debugging, log aggregation |
| 4 | Health checks | Load balancer / orchestration readiness |
| 5 | Retries | Resilience to transient failures |
| 6 | Tests | Regression prevention, confidence in changes |
| 7 | CI/CD | Automated quality checks on every push |

---

## 1. Docker

### What was done

- **Dockerfile** — Builds the API image (Python 3.11, dependencies, `tiny_rag` package)
- **docker-compose.yml** — Runs API + PostgreSQL (pgvector) together
- **.dockerignore** — Excludes venv, `.git`, data, docs from build context
- **docker/init-db.sql** — Enables pgvector extension on first DB start

### Why it matters

- **Consistency** — Same Python version and dependencies everywhere (dev, CI, prod)
- **Portability** — Runs on any host with Docker
- **Deployment** — One command to start app + DB; no manual setup

### Key files

| File | Purpose |
|------|---------|
| `Dockerfile` | Image build instructions |
| `docker-compose.yml` | Service definitions (db, api) |
| `.dockerignore` | Build context exclusions |
| `docker/init-db.sql` | DB initialization |

### Run

```bash
docker compose up -d --build
```

See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for a full walkthrough.

---

## 2. API Authentication

### What was done

- **API key** — Clients send `X-API-Key` header
- **Optional** — If `API_KEY` is empty in `.env`, auth is disabled (for local dev)
- **Protected routes** — `/ask` requires valid key when `API_KEY` is set
- **Unprotected** — `/` (liveness) stays open for load balancers

### Why it matters

- **Security** — Prevents unauthorized access to the RAG endpoint
- **Access control** — Different keys for different clients
- **Production baseline** — API keys are a minimal, standard form of auth

### Key files

| File | Purpose |
|------|---------|
| `src/tiny_rag/api.py` | `verify_api_key()` dependency, `APIKeyHeader` |
| `.env.example` | `API_KEY=` template |

### Usage

```bash
curl -H "X-API-Key: your-secret-key" "http://localhost:8000/ask?q=..."
```

See [AUTH_GUIDE.md](AUTH_GUIDE.md) for details.

---

## 3. Structured Logging

### What was done

- **structlog** — Structured, key-value logs instead of plain `print`
- **Formats** — Console (dev) and JSON (production)
- **Request ID** — Each API request gets a UUID; logged in all related entries
- **Response header** — `X-Request-ID` returned for client-side tracing
- **Replaced print** — ingest, eval, rag, retrieve, api now use `logger.info()` etc.

### Why it matters

- **Observability** — Log aggregators (CloudWatch, Datadog) can parse JSON and filter by `request_id`
- **Debugging** — Trace a single request across logs
- **Production** — Structured logs are the standard for production systems

### Key files

| File | Purpose |
|------|---------|
| `src/tiny_rag/logging_config.py` | structlog setup, `get_logger()` |
| `src/tiny_rag/api.py` | Request ID middleware, `structlog.contextvars` |

### Env vars

| Variable | Values | Default |
|----------|--------|---------|
| `LOG_FORMAT` | `console`, `json` | `console` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

### Example (JSON)

```json
{"event": "ask_request", "query": "What are...", "request_id": "550e8400-...", "level": "info", "timestamp": "..."}
```

See [LOGGING_GUIDE.md](LOGGING_GUIDE.md) for details.

---

## 4. Health Checks

### What was done

- **`/health` endpoint** — Checks DB and Ollama connectivity
- **200** — All checks pass
- **503** — Any check fails (with details in JSON)
- **`/`** — Simple liveness (no dependencies)
- **Docker healthcheck** — API container has a healthcheck for orchestration

### Why it matters

- **Load balancers** — Use `/health` to decide if the instance can receive traffic
- **Kubernetes** — Liveness and readiness probes
- **Monitoring** — Alerts when health fails

### Key files

| File | Purpose |
|------|---------|
| `src/tiny_rag/health.py` | `check_database()`, `check_ollama()` |
| `src/tiny_rag/api.py` | `/health` endpoint |
| `docker-compose.yml` | `healthcheck` for api service |

### Response

```json
{"status": "healthy", "database": "ok", "ollama": "ok"}
```

---

## 5. Retries

### What was done

- **tenacity** — Retry decorators for transient failures
- **DB retries** — `retrieve_context`, `store_in_pgvector` retry on `psycopg2.OperationalError`, `InterfaceError`
- **Ollama retries** — `call_ollama` retries on `ConnectionError`, `TimeoutError`, `httpx.ConnectError`
- **Config** — 3 attempts, exponential backoff 1s–10s

### Why it matters

- **Resilience** — Brief DB or network glitches don’t immediately fail requests
- **Stability** — Common pattern in production systems
- **User experience** — Fewer transient errors visible to users

### Key files

| File | Purpose |
|------|---------|
| `src/tiny_rag/retry_config.py` | `retry_db`, `retry_ollama` decorators |
| `src/tiny_rag/retrieve.py` | `@retry_db` on `retrieve_context` |
| `src/tiny_rag/ingest.py` | `@retry_db` on `store_in_pgvector` |
| `src/tiny_rag/rag.py` | `@retry_ollama` on `call_ollama` |

---

## 6. Tests

### What was done

- **pytest** — Test framework
- **Unit tests** — `infer_ticker_from_query`, `build_rag_prompt`, `chunk_with_overlap`, `load_txt`
- **Integration tests** — API endpoints (`/`, `/health`, `/ask`) with mocks
- **Mocks** — No DB or Ollama required; tests run in CI and locally

### Why it matters

- **Regression prevention** — Catch breaking changes before deploy
- **Refactoring** — Safe to change code with test coverage
- **CI** — Automated quality gate on every push

### Key files

| File | Purpose |
|------|---------|
| `tests/conftest.py` | TestClient fixture |
| `tests/test_rag.py` | RAG unit tests |
| `tests/test_ingest.py` | Ingest unit tests |
| `tests/test_api.py` | API integration tests |

### Run

```bash
pytest tests/ -v
```

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for details.

---

## 7. CI/CD

### What was done

- **GitHub Actions** — Workflow on push/PR to `main`, `feature/organized`
- **Lint job** — `ruff check src/ tests/`
- **Test job** — `pytest tests/ -v`
- **Build job** — Docker image build (after lint and test pass)
- **ruff.toml** — Lint configuration

### Why it matters

- **Automation** — No manual lint/test before merge
- **Quality** — Broken code is caught before it reaches main
- **Confidence** — Every commit is validated

### Key files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Workflow definition |
| `ruff.toml` | Ruff lint config |

### Local pre-push

```bash
ruff check src/ tests/
pytest tests/ -v
```

See [CI_GUIDE.md](CI_GUIDE.md) for details.

---

## Summary: Before vs After

| Area | Before | After |
|------|--------|-------|
| **Deployment** | Manual Python setup | `docker compose up` |
| **Security** | Open API | API key auth |
| **Logs** | `print` statements | Structured JSON logs, request IDs |
| **Readiness** | None | `/health` with DB + Ollama checks |
| **Failures** | Immediate error | Retries with backoff |
| **Quality** | Manual testing | Automated tests + CI |
| **Checks** | Manual | Lint + test + build on every push |

---

## Reference: All docs

| Doc | Content |
|-----|---------|
| [DOCKER_GUIDE.md](DOCKER_GUIDE.md) | Docker walkthrough |
| [AUTH_GUIDE.md](AUTH_GUIDE.md) | API authentication |
| [LOGGING_GUIDE.md](LOGGING_GUIDE.md) | Structured logging |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Tests |
| [CI_GUIDE.md](CI_GUIDE.md) | CI/CD |
| [CODE_GUIDE.md](CODE_GUIDE.md) | Implementation reference |

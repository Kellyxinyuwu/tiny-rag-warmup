# Docker Guide — Complete Walkthrough

This guide explains every Docker file in this project and how to use them step by step.

---

## What is Docker?

**Docker** packages your application and its dependencies into a **container** — a lightweight, portable environment that runs the same way everywhere (your laptop, a server, the cloud).

| Concept | Meaning |
|---------|---------|
| **Image** | A snapshot/blueprint of your app (built from a Dockerfile) |
| **Container** | A running instance of an image |
| **Dockerfile** | Instructions to build an image |
| **docker-compose** | Defines and runs multiple containers together (app + database) |

---

## File Overview

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the API image (Python + dependencies + your code) |
| `.dockerignore` | Tells Docker which files to skip when building |
| `docker-compose.yml` | Runs the API + database together |
| `docker/init-db.sql` | Runs when the database starts (creates pgvector extension) |

---

## 1. Dockerfile — Line by Line

**Location:** `Dockerfile` (project root)

**Full content:**

```dockerfile
# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system deps (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY requirements.txt pyproject.toml ./

# Copy source
COPY src/ ./src/

# Install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt && pip install -e .

# Expose API port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "tiny_rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Line-by-line explanation

| Line(s) | What it does |
|---------|---------------|
| `FROM python:3.11-slim` | Start from the official Python 3.11 image. `slim` = smaller image (no extra tools). |
| `WORKDIR /app` | Set the working directory inside the container to `/app`. All later commands run here. |
| `RUN apt-get update && apt-get install...` | Install system packages. `build-essential` is sometimes needed for Python packages that compile C code. `rm -rf /var/lib/apt/lists/*` keeps the image smaller. |
| `COPY requirements.txt pyproject.toml ./` | Copy dependency files into the container. We do this before copying source code so Docker can cache this layer when only code changes. |
| `COPY src/ ./src/` | Copy your Python package into the container. |
| `RUN pip install...` | Install Python dependencies and the `tiny_rag` package in editable mode. `--no-cache-dir` reduces image size. |
| `EXPOSE 8000` | Document that the app listens on port 8000. Does not publish the port by itself (docker-compose does that). |
| `CMD ["uvicorn", ...]` | Default command when the container starts. Runs the FastAPI app with uvicorn. `0.0.0.0` means "listen on all interfaces" so it accepts requests from outside the container. |

---

## 2. .dockerignore — Line by Line

**Location:** `.dockerignore` (project root)

**Full content:**

```
venv/
.venv/
__pycache__/
*.pyc
*.egg-info/
.git/
.gitignore
.env
*.pdf
sec-edgar-filings/
data/
eval_results.xlsx
docs/
scripts/
*.md
```

### What it does

When Docker runs `COPY`, it sends a **build context** (your project files) to the Docker daemon. `.dockerignore` excludes files/folders from that context.

### Line-by-line explanation

| Line | Why exclude |
|------|-------------|
| `venv/`, `.venv/` | Virtual environment — we install fresh in the container |
| `__pycache__/`, `*.pyc` | Python bytecode — not needed, rebuilt automatically |
| `*.egg-info/` | Package metadata — generated during `pip install` |
| `.git/`, `.gitignore` | Version control — not needed in the image |
| `.env` | Secrets — never put in images |
| `*.pdf`, `sec-edgar-filings/`, `data/` | Large data — we mount these at runtime instead |
| `eval_results.xlsx` | Generated output — not needed to run the app |
| `docs/`, `scripts/`, `*.md` | Documentation and scripts — API container only needs `src/` |

**Result:** Faster builds and smaller images.

---

## 3. docker-compose.yml — Line by Line

**Location:** `docker-compose.yml` (project root)

**Full content:**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: rag_db
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./sec-edgar-filings:/app/sec-edgar-filings
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/rag_db
      OLLAMA_HOST: http://host.docker.internal:11434
    depends_on:
      db:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  pgdata:
```

### Service: `db`

| Key | Value | Meaning |
|-----|-------|---------|
| `image` | `pgvector/pgvector:pg16` | Use the official pgvector image (PostgreSQL 16 + vector extension) |
| `environment` | `POSTGRES_USER`, etc. | Create user `postgres`, password `postgres`, database `rag_db` on first run |
| `ports` | `"5433:5432"` | Expose container port 5432 as host port 5433 (avoids conflict with local Postgres on 5432) |
| `volumes` | `pgdata:/var/lib/postgresql/data` | Persist database data in a named volume (survives container restarts) |
| `volumes` | `./docker/init-db.sql:...` | Mount init script — PostgreSQL runs `.sql` files in `docker-entrypoint-initdb.d/` on first start |
| `healthcheck` | `pg_isready` | Check every 5s if DB is ready. Used by `depends_on` so the API waits for a healthy DB. |

### Service: `api`

| Key | Value | Meaning |
|-----|-------|---------|
| `build` | `.` | Build the image from the Dockerfile in the current directory |
| `ports` | `"8000:8000"` | Expose API on host port 8000 |
| `volumes` | `./sec-edgar-filings:/app/sec-edgar-filings` | Mount host's `sec-edgar-filings` into the container so ingest can read downloaded 10-Ks |
| `environment` | `DATABASE_URL` | Connection string. `db` is the service name — Docker's internal DNS resolves it to the DB container's IP. |
| `environment` | `OLLAMA_HOST` | Ollama runs on your host. `host.docker.internal` = host machine from inside the container. |
| `depends_on` | `db: service_healthy` | Start API only after DB passes its healthcheck |
| `extra_hosts` | `host.docker.internal:host-gateway` | Ensures `host.docker.internal` works (needed on Linux) |

### Volumes section

| Key | Meaning |
|-----|---------|
| `pgdata` | Named volume for database persistence. Docker manages it. |

---

## 4. docker/init-db.sql

**Location:** `docker/init-db.sql`

**Full content:**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**What it does:** When the PostgreSQL container starts for the first time, it runs this SQL. It enables the pgvector extension so you can store and query vector embeddings.

---

## Step-by-Step Workflow

### Prerequisites

- Docker Desktop installed ([docker.com](https://www.docker.com/products/docker-desktop))
- Ollama installed and running on your host

### Step 1: Pull the LLM model (on host)

```bash
ollama pull llama3.2
```

Ollama runs on your machine. The API container connects to it via `host.docker.internal`.

---

### Step 2: Download 10-K filings (on host)

```bash
# Activate venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows

# Edit scripts/download_financial_docs.py: set COMPANY_NAME, COMPANY_EMAIL
# Then run:
python scripts/download_financial_docs.py
```

This creates `sec-edgar-filings/` with the downloaded files. The API container will read from this folder via the volume mount.

---

### Step 3: Build and start containers

```bash
docker compose up -d --build
```

| Flag | Meaning |
|------|---------|
| `up` | Create and start containers |
| `-d` | Detached mode (run in background) |
| `--build` | Build the API image before starting (use when Dockerfile or code changed) |

**What happens:**
1. Builds the API image from the Dockerfile
2. Pulls the pgvector image (if not cached)
3. Creates the `db` container, runs init-db.sql on first start
4. Waits for DB healthcheck to pass
5. Starts the `api` container

---

### Step 4: Ingest documents (inside API container)

```bash
docker compose exec api python -m tiny_rag.ingest
```

| Part | Meaning |
|------|---------|
| `docker compose exec` | Run a command in a running container |
| `api` | The service name (your API container) |
| `python -m tiny_rag.ingest` | Run the ingest module |

This reads from `sec-edgar-filings/` (mounted), chunks, embeds, and stores in the database.

---

### Step 5: Use the API

```bash
curl "http://localhost:8000/ask?q=What%20are%20Alphabet%27s%20main%20risks%3F"
```

Or open http://localhost:8000/docs for Swagger UI.

---

### Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Liveness — app is running |
| `GET /health` | Readiness — DB + Ollama reachable |

```bash
curl http://localhost:8000/health
# 200: {"status": "healthy", "database": "ok", "ollama": "ok"}
# 503: {"status": "unhealthy", "database": "ok", "ollama": "connection refused"}
```

Use `/health` for load balancers and Kubernetes probes.

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `docker compose up -d --build` | Start everything (build if needed) |
| `docker compose down` | Stop and remove containers |
| `docker compose down -v` | Stop and remove containers + volumes (deletes DB data) |
| `docker compose ps` | List running containers |
| `docker compose logs -f api` | Follow API logs |
| `docker compose logs -f db` | Follow database logs |
| `docker compose exec api python -m tiny_rag.rag "query"` | Run RAG CLI inside container |
| `docker compose exec api python -m tiny_rag.eval` | Run eval inside container |

---

## Troubleshooting

### "Cannot connect to Ollama"

- Ensure Ollama is running on your host: `ollama list`
- On Linux, `host.docker.internal` may not work. Add to docker-compose under `api`:
  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```
  (Already present in this project.)

### "could not translate host name 'db' to address"

Run ingest from the host instead (DB is on localhost:5433):

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/rag_db"
python -m tiny_rag.ingest
```

### "relation documents does not exist"

Run ingest:
```bash
docker compose exec api python -m tiny_rag.ingest
# Or from host: DATABASE_URL=postgresql://postgres:postgres@localhost:5433/rag_db python -m tiny_rag.ingest
```

### "sec-edgar-filings is empty"

Run the download script on your host first:
```bash
python scripts/download_financial_docs.py
```

### Rebuild after code changes

```bash
docker compose up -d --build
```

### Reset database

```bash
docker compose down -v
docker compose up -d
docker compose exec api python -m tiny_rag.ingest
```

---

## Summary Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Your Host Machine                                          │
│                                                              │
│  ollama (llama3.2)     sec-edgar-filings/                   │
│       ↑                        ↑                             │
│       │                        │ volume mount                 │
│       │ OLLAMA_HOST            │                              │
│       │                        │                              │
│  ┌────┴───────────────────────┴────┐                        │
│  │  Docker                         │                        │
│  │  ┌──────────┐    ┌────────────┐ │                        │
│  │  │   db     │    │    api     │ │                        │
│  │  │ pgvector │◄───│  FastAPI   │ │                        │
│  │  │ :5433    │    │  :8000     │ │                        │
│  │  └──────────┘    └────────────┘ │                        │
│  └─────────────────────────────────┘                        │
│                                                              │
│  localhost:8000  →  API                                      │
│  localhost:5433  →  Database                                 │
└─────────────────────────────────────────────────────────────┘
```

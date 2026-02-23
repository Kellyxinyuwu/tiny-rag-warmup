# Tiny RAG — Financial Documents

**Status:** In progress — Ingestion done, extending to embeddings + pgvector + retrieval + RAG.

A RAG (Retrieval Augmented Generation) project for financial documents (10-K filings). Uses **pgvector**, **Ollama**, and **SEC EDGAR** data. Designed to be AWS-ready later (Bedrock, pgvector on RDS).

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Tech Stack & Comparisons](#tech-stack--comparisons)
3. [How We Get the Data](#how-we-get-the-data)
4. [Converting Raw Formats to Text](#converting-raw-formats-to-text)
5. [Project Structure](#project-structure)
6. [Setup](#setup)
7. [Run](#run)
8. [What's Next](#whats-next)
9. [Git Notes](#git-notes)

See **DATA_GUIDE.md** for more detail on SEC EDGAR, pipeline paths, and stack choices.

---

## What This Project Does

1. **Download** 10-K filings from SEC EDGAR (Apple, Alphabet)
2. **Extract** text from the full submission (or convert PDF/HTML/XML via `process_documents.py`)
3. **Chunk** text with overlap and token-aware sizing
4. **Embed** chunks and **store** in pgvector
5. **Retrieve** and **answer** with RAG (retrieval → prompt → LLM → citations)

---

## Tech Stack & Comparisons

### Vector DB: pgvector (chosen)

| | pgvector | Chroma |
|--|----------|--------|
| **Setup** | PostgreSQL + extension (Docker: one command) | `pip install chromadb` |
| **Production readiness** | High — SQL, ACID, scales | Good for prototyping |
| **Enterprise fit** | Common in AWS/RDS setups | Simpler, less ops |
| **Why we chose it** | More prod-ready; aligns with Jefferies/AWS | — |

```bash
# pgvector with Docker
docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
```

### LLM: Ollama (chosen for now)

| | Ollama | OpenAI | Bedrock |
|--|--------|--------|---------|
| **Cost** | Free, local | Paid API | Paid (AWS) |
| **Setup** | Install + pull model | API key | AWS account + access |
| **Use case** | Local dev, learning | General production | AWS-native, enterprise |
| **Why we chose it** | No API key; fast iteration | — | Target for Jefferies later |

### Embeddings

| | SentenceTransformers | Ollama (nomic-embed-text) | OpenAI | Bedrock Titan |
|--|---------------------|---------------------------|--------|---------------|
| **Cost** | Free | Free | Paid | Paid |
| **Setup** | `pip install` | `ollama pull` | API key | AWS |
| **Use case** | Local, good quality | Local | Production | AWS production |

---

## How We Get the Data

### Source: SEC EDGAR

- **Website:** [sec.gov/edgar](https://www.sec.gov/edgar)
- **Filing types:** 10-K (annual), 10-Q (quarterly), 8-K (current events)
- **Tickers:** AAPL (Apple), GOOGL (Alphabet/Google), etc.

### Path A: Direct txt (recommended)

`download_financial_docs.py` downloads 10-Ks and produces txt directly:

```bash
python download_financial_docs.py
```

**Output:** `sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt`

No conversion step. Use these files for RAG.

### Path B: Raw → Process (mimics real pipeline)

When documents arrive as PDF, XML, or HTML:

1. Put raw files in `data/`
2. Run `process_documents.py`
3. Output: `sec-edgar-filings/processed/*.txt`

```bash
python process_documents.py
```

### Path C: Manual download

1. Go to [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar)
2. Search by ticker (e.g. AAPL, GOOGL)
3. Filings → filter by **10-K**
4. Open filing → **Documents** → download the main `.htm` (not "Inline XBRL Viewer")
5. Save to `data/` → run `process_documents.py`

### Pitfall: Inline XBRL Viewer

The **"Inline XBRL Viewer"** link gives a small XML/HTML page that only loads the real document in an iframe. It has almost no content (~130 lines of viewer code). Do **not** use it as your source. Use **Documents** and the main `.htm` file, or Path A.

### Exploration summary

| Step | What we tried | Outcome |
|------|---------------|---------|
| Download source | SEC EDGAR | Free, no API key; 10-K best for RAG |
| Get txt | `download_financial_docs.py` | Direct `full-submission.txt` in `sec-edgar-filings/` |
| Manual download | "Inline XBRL Viewer" XML | Wrong file — viewer page, not content |
| Manual download | Documents → main `.htm` | Correct — use this if not using script |
| Raw → txt | `process_documents.py` | Converts PDF/HTML/XML in `data/` → `sec-edgar-filings/processed/` |
| Vector DB | Chroma vs pgvector | Chose pgvector for prod readiness |
| LLM | Ollama vs OpenAI vs Bedrock | Ollama for local dev; Bedrock for AWS later |

---

## Converting Raw Formats to Text

In practice, documents come as PDF, HTML, XML, or Excel. We convert them before chunking.

| Format | Tool | Difficulty |
|--------|------|------------|
| **HTML** | BeautifulSoup | Easy |
| **PDF** | pypdf, PyMuPDF, pdfplumber | Medium (tables, layout) |
| **XML** | BeautifulSoup, xml.etree | Easy |
| **Excel** | pandas, openpyxl | Easy–Medium |
| **Scanned PDF** | Tesseract OCR | Hard |

`process_documents.py` handles XML, HTML, and PDF. For complex PDFs, consider `Unstructured.io` or cloud APIs (e.g. AWS Textract).

---

## Project Structure

```
tiny-rag-warmup/
├── data/                    # Raw files (PDF, XML, HTML) for processing
├── sec-edgar-filings/       # Downloaded 10-Ks
│   ├── AAPL/10-K/.../full-submission.txt
│   ├── GOOGL/10-K/.../full-submission.txt
│   └── processed/          # Output from process_documents.py
├── download_financial_docs.py   # SEC EDGAR download
├── process_documents.py        # Raw → txt conversion
├── ingest.py                   # Chunk, embed, store (to be extended)
├── DATA_GUIDE.md               # Detailed data guide
├── requirements.txt
└── README.md
```

---

## Setup

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### pgvector (Docker)

```bash
docker run -d --name pgvector -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
# Create DB: CREATE DATABASE rag_db; \c rag_db; CREATE EXTENSION vector;
```

### Ollama

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

---

## Run

```bash
# 1. Download 10-Ks (edit COMPANY_NAME, COMPANY_EMAIL in script first)
python download_financial_docs.py

# 2. Process raw files (if you have PDF/XML/HTML in data/)
python process_documents.py

# 3. Ingest (extend ingest.py to use txt + pgvector)
python ingest.py
```

---

## What's Next

- [x] Extend `ingest.py`: load txt, chunk with overlap, embed, store in pgvector
- [x] Implement `retrieve_context(query, k=5)` in `retrieve.py`
- [ ] Implement `answer_with_rag` (retrieval → prompt → Ollama → citations)
- [ ] Add FastAPI `/ask` endpoint
- [ ] Evaluation script + Q&A pairs

See **INGEST_GUIDE.md** for ingestion and retrieval setup.

---

## Git Notes

| Command | Purpose |
|---------|---------|
| `git add .` | Stage changes |
| `git commit -m "message"` | Commit |
| `git push` | Push to remote |

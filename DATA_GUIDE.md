# Getting Financial Documents for Your RAG Project

This guide shows how to get usable financial documents from **SEC EDGAR** for your RAG pipeline. You'll use **Ollama** and **Chroma** now, and switch to AWS later.

---

## Part 1: SEC EDGAR — Where to Get Documents

**SEC EDGAR** hosts all public company filings in the US. It's free and requires no API key.

- **Website:** [sec.gov/edgar](https://www.sec.gov/edgar)
- **Search:** [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar)

### Common filing types

| Filing | Description |
|--------|-------------|
| **10-K** | Annual report — full-year financials, risk factors, MD&A |
| **10-Q** | Quarterly report — quarterly financials |
| **8-K** | Current report — material events (earnings, acquisitions) |

For RAG, **10-K** is usually the best starting point.

---

## Part 2: Two Pipeline Paths

### Path A: Direct (recommended for SEC EDGAR)

`download_financial_docs.py` gives you **txt directly** — no extra processing:

```bash
python download_financial_docs.py
```

Output: `sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt` — ready for RAG.

### Path B: Raw → Process (mimics real-world pipeline)

In reality, documents often arrive as **PDF, XML, or HTML**. Use `process_documents.py` to convert them:

```bash
# 1. Put raw files in data/ (XML, PDF, HTML from manual download or other sources)
# 2. Run the processor
python process_documents.py
```

Output: `sec-edgar-filings/processed/*.txt` — converted from raw formats.

**Flow:** `data/` (raw XML/PDF/HTML) → `process_documents.py` → `sec-edgar-filings/processed/*.txt`

**Note:** Avoid "Inline XBRL Viewer" XML — it's a viewer page, not the filing content. Download the main document (Documents link) or use Path A.

### Option C: Manual download

1. Go to [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar)
2. Search by **Company name** or **Ticker** (e.g., AAPL, GOOGL, MSFT)
3. Click the company → **Filings** → filter by **10-K**
4. Open a filing → **Documents** → download the main `.htm` (not "Inline XBRL Viewer")
5. Save to `data/` → run `process_documents.py` to convert to txt

---

## Part 3: Your Stack (Ollama + pgvector)

| Component | Choice | Notes |
|-----------|--------|------|
| **LLM** | Ollama | Local, no API key. Run `ollama run llama3.2` |
| **Embeddings** | SentenceTransformers or Ollama | `all-MiniLM-L6-v2` or `nomic-embed-text` via Ollama |
| **Vector DB** | pgvector | Production-ready, PostgreSQL. See README for Chroma comparison |

### Install

```bash
pip install -r requirements.txt
# pgvector: use Docker (see README)
```

### Ollama setup

```bash
# Install Ollama from ollama.com, then:
ollama pull llama3.2        # For chat/completion
ollama pull nomic-embed-text  # For embeddings
```

---

## Part 4: Quick Start Checklist

- [ ] Install Ollama and pull `llama3.2` and `nomic-embed-text`
- [ ] Install `sec-edgar-downloader`, `pgvector`, `psycopg2-binary`
- [ ] Run pgvector via Docker (see README)
- [ ] Run `download_financial_docs.py` to get 1–2 10-Ks
- [ ] Extend `ingest.py` to use embeddings + pgvector
- [ ] Build retrieval and RAG pipeline

---

## Part 5: Switching to AWS Later

When you deploy to AWS:

- **LLM:** Replace Ollama with `boto3` Bedrock client
- **Embeddings:** Replace with Bedrock Titan Embeddings
- **Vector DB:** Point to pgvector on RDS (same API, different connection)

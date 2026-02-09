# Tiny RAG Warm-up

**Status: Complete** — This week's ingestion/chunking phase is done. Ready for embeddings next week.

## What this project did

This project builds the **ingestion and splitting** muscle for RAG (Retrieval Augmented Generation):

1. **Extract text** from a PDF — reads all pages and joins them into one string
2. **Chunk the text** — splits it into fixed-size pieces (default 1000 chars) for embedding later

These chunks are the feed for embeddings when you add the full RAG pipeline (vector DB, retrieval, LLM).

### Functions

- **`extract_text_from_pdf(path)`** — Reads a PDF and returns all page text as one string
- **`simple_chunk(text, max_chars=1000)`** — Splits text into fixed-size chunks (no overlap)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Get a sample PDF

Save a long PDF as `sample_10k.pdf` in this folder. Options:

- **Direct PDF:** [Alphabet 2024 10-K](https://abc.xyz/assets/77/51/9841ad5c4fbe85b4440c47a4df8d/goog-10-k-2024.pdf) — right-click → Save as
- **SEC EDGAR:** [sec.gov/search-filings](https://www.sec.gov/search-filings) — search a company, find a 10-K, look for PDF attachments
- Any long finance document from investor relations sites

## Run

```bash
python ingest.py
```

Expected output: total chunk count and a preview of the first chunk.

## What's next

- **Next week:** Embed chunks, store in a vector DB, and build retrieval + LLM answering

---

## Git Study Notes

### `cd` (Change Directory)

| Command | Purpose |
|---------|---------|
| `cd path` | Move into the given folder |
| `cd ..` | Go up one level (parent folder) |
| `cd` or `cd ~` | Go to your home directory |

### Git commands used for this project

| Command | Purpose |
|---------|---------|
| `git init` | Turn the current folder into a Git repo (creates a `.git` folder). Do this once per project. |
| `git add .` | Stage all files for the next commit. The `.` means "everything in this directory." |
| `git commit -m "message"` | Save a snapshot of staged files with a descriptive message. |
| `git remote add origin <url>` | Link this repo to your GitHub repo. `origin` is the conventional name for the main remote. |
| `git branch -M main` | Rename the current branch to `main` (in case it was `master`). |
| `git push -u origin main` | Upload your commits to GitHub. `-u` sets `origin` as the default remote for future pushes. |

### Typical daily workflow

1. `git add .` — Stage your changes
2. `git commit -m "Describe what you did"` — Save locally
3. `git push` — Send to GitHub

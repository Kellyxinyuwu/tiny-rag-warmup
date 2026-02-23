# Branch Setup Steps

## Goal

- **main** = original version (PDF extraction + simple chunking only)
- **original** (branch 1) = same as main, preserves baseline
- **feature/extended** (branch 2) = extended RAG pipeline (download, process, ingest, retrieve, pgvector)

Work on `feature/extended`, merge to `main` when ready.

---

## Steps

### 1. Create branch 1 (original) from current main

```bash
cd "/Users/kellywu/Desktop/AI learning/tiny-rag-warmup"
git checkout main
git branch original
```

### 2. Create branch 2 (feature/extended) and switch to it

```bash
git checkout -b feature/extended
```

### 3. Add and commit all extended changes

```bash
# Add new and modified files (exclude .DS_Store)
git add DATA_GUIDE.md INGEST_GUIDE.md download_financial_docs.py process_documents.py retrieve.py
git add ingest.py README.md requirements.txt

# Optional: ignore large downloaded data (recommended)
# echo "sec-edgar-filings/" >> .gitignore
# echo "data/" >> .gitignore

git add .gitignore 2>/dev/null || true
git status  # verify
git commit -m "feat: extended RAG pipeline - SEC download, process, pgvector, retrieve"
```

### 4. Verify branches

```bash
git branch -a
# main, original, feature/extended

git log --oneline -3
# Should show your new commit on feature/extended
```

### 5. Switch back to main (optional check)

```bash
git checkout main
git log --oneline -3
# main should still be at original (no extended commit)
ls
# Should NOT have retrieve.py, DATA_GUIDE.md, etc. (if uncommitted on main)
```

**Note:** If you had uncommitted changes on main, `main` still has the old files in the working tree until you checkout. After step 3, the extended files exist only on `feature/extended`.

### 6. Work on feature branch from now on

```bash
git checkout feature/extended
# All future work happens here
```

### 7. Later: merge to main when ready

```bash
git checkout main
git merge feature/extended
git push origin main
```

---

## Summary

| Branch | Purpose |
|--------|---------|
| **main** | Original baseline (PDF + simple chunk) |
| **original** | Backup of original (same as main) |
| **feature/extended** | Extended pipeline; active development |

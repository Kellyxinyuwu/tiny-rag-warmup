"""
Tiny RAG ingestion: load 10-K txt files, chunk with overlap, embed, store in pgvector.

GUIDE:
------
1. find_filing_txt_files()  → Discovers full-submission.txt in sec-edgar-filings/{ticker}/10-K/
2. load_txt(path)           → Reads raw text from file
3. chunk_with_overlap()     → Splits text into 400-token chunks with 100-token overlap (tiktoken)
4. embed_chunks()           → Embeds each chunk with SentenceTransformers all-MiniLM-L6-v2
5. store_in_pgvector()      → Inserts chunks + embeddings into documents table

Run: python -m tiny_rag.ingest
Requires: DATABASE_URL in .env, pgvector running, sec-edgar-filings/ populated
"""
import os
from pathlib import Path

from dotenv import load_dotenv

import tiktoken

load_dotenv()

from .logging_config import get_logger
from .retry_config import retry_db

logger = get_logger(__name__)

# Paths relative to project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SEC_FILINGS_DIR = PROJECT_ROOT / "sec-edgar-filings"

# Chunking: token-based sliding window (see README "Chunking Method")
# 400 tokens ≈ 300 words; 100 overlap prevents cutting sentences
CHUNK_SIZE_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 100

# pgvector connection (override with env: DATABASE_URL)
# Default: use current user (macOS/Homebrew) or postgres (Docker)
_default_user = os.environ.get("USER", "postgres")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{_default_user}@localhost:5432/rag_db",
)


def load_txt(path: Path) -> str:
    """Load text from a file."""
    return path.read_text(encoding="utf-8", errors="ignore")


def find_filing_txt_files() -> list[tuple[Path, str]]:
    """
    Find all full-submission.txt files in sec-edgar-filings.
    Returns list of (path, ticker) tuples.
    """
    if not SEC_FILINGS_DIR.exists():
        return []

    results = []
    for ticker_dir in SEC_FILINGS_DIR.iterdir():
        if not ticker_dir.is_dir():
            continue
        ten_k_dir = ticker_dir / "10-K"
        if not ten_k_dir.exists():
            continue
        for accession_dir in ten_k_dir.iterdir():
            if not accession_dir.is_dir():
                continue
            txt_file = accession_dir / "full-submission.txt"
            if txt_file.exists():
                results.append((txt_file, ticker_dir.name))
    return results


def chunk_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into chunks by tokens, with overlap.

    Uses tiktoken (cl100k_base) — same encoding as GPT-4.
    Sliding window: stride = chunk_size - overlap. Each chunk shares `overlap`
    tokens with the previous one to avoid cutting sentences.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    chunks = []
    start = 0
    stride = chunk_size - overlap

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        if chunk_text.strip():
            chunks.append(chunk_text)
        start += stride
        if start >= len(tokens):
            break

    return chunks


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """Embed chunks using SentenceTransformers."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(chunks, show_progress_bar=True)
    return embeddings.tolist()


def get_embedding_dim() -> int:
    """Return embedding dimension for all-MiniLM-L6-v2."""
    return 384


def init_pgvector(conn):
    """Create extension and table if not exist."""
    from pgvector.psycopg2 import register_vector

    register_vector(conn)
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS documents (
            id bigserial PRIMARY KEY,
            content text NOT NULL,
            embedding vector({get_embedding_dim()}),
            ticker text,
            source text
        )
        """
    )
    cur.close()
    conn.commit()


@retry_db
def store_in_pgvector(
    chunks: list[str],
    embeddings: list[list[float]],
    ticker: str,
    source: str,
) -> None:
    """Store chunks and embeddings in pgvector."""
    import numpy as np
    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)
    init_pgvector(conn)

    cur = conn.cursor()
    for content, embedding in zip(chunks, embeddings):
        cur.execute(
            """
            INSERT INTO documents (content, embedding, ticker, source)
            VALUES (%s, %s, %s, %s)
            """,
            (content, np.array(embedding), ticker, source),
        )
    conn.commit()
    cur.close()
    conn.close()


def ingest_all():
    """Load filings, chunk, embed, and store in pgvector."""
    files = find_filing_txt_files()
    if not files:
        logger.warning("no_filings_found", hint="Run python scripts/download_financial_docs.py")
        return

    logger.info("ingest_start", filings_count=len(files))

    for path, ticker in files:
        logger.info("processing_ticker", ticker=ticker)
        text = load_txt(path)
        logger.info("loaded", ticker=ticker, chars=len(text))

        chunks = chunk_with_overlap(
            text,
            chunk_size=CHUNK_SIZE_TOKENS,
            overlap=CHUNK_OVERLAP_TOKENS,
        )
        logger.info("chunked", ticker=ticker, chunks=len(chunks))

        embeddings = embed_chunks(chunks)
        logger.info("embedded", ticker=ticker, count=len(embeddings))

        store_in_pgvector(
            chunks=chunks,
            embeddings=embeddings,
            ticker=ticker,
            source=str(path),
        )
        logger.info("stored", ticker=ticker)

    logger.info("ingest_complete")


if __name__ == "__main__":
    ingest_all()

"""
Tiny RAG ingestion: load 10-K txt files, chunk with overlap, embed, store in pgvector.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

import tiktoken

load_dotenv()

# Paths
SEC_FILINGS_DIR = Path("sec-edgar-filings")

# Chunking
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
    Uses tiktoken (cl100k_base) for token counting.
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
        print("No full-submission.txt files found in sec-edgar-filings/")
        print("Run: python download_financial_docs.py")
        return

    print(f"Found {len(files)} filing(s)")

    for path, ticker in files:
        print(f"\nProcessing {ticker}...")
        text = load_txt(path)
        print(f"  Loaded {len(text):,} chars")

        chunks = chunk_with_overlap(
            text,
            chunk_size=CHUNK_SIZE_TOKENS,
            overlap=CHUNK_OVERLAP_TOKENS,
        )
        print(f"  Chunked into {len(chunks)} chunks")

        embeddings = embed_chunks(chunks)
        print(f"  Embedded {len(embeddings)} chunks")

        store_in_pgvector(
            chunks=chunks,
            embeddings=embeddings,
            ticker=ticker,
            source=str(path),
        )
        print(f"  Stored in pgvector")

    print("\nDone. Ready for retrieval.")


if __name__ == "__main__":
    ingest_all()

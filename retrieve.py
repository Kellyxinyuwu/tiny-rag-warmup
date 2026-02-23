"""
Retrieve relevant chunks from pgvector for a query.
"""
import os
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/rag_db",
)


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model.encode([query])[0].tolist()


def retrieve_context(query: str, k: int = 5, ticker: str | None = None) -> list[dict]:
    """
    Retrieve top-k most relevant chunks for a query.
    Returns list of dicts with keys: content, ticker, source.
    """
    import numpy as np
    import psycopg2
    from pgvector.psycopg2 import register_vector

    embedding = embed_query(query)
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)

    cur = conn.cursor()
    if ticker:
        cur.execute(
            """
            SELECT content, ticker, source
            FROM documents
            WHERE ticker = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (ticker, np.array(embedding), k),
        )
    else:
        cur.execute(
            """
            SELECT content, ticker, source
            FROM documents
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (np.array(embedding), k),
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"content": row[0], "ticker": row[1], "source": row[2]}
        for row in rows
    ]


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "What are Apple's main risk factors?"
    results = retrieve_context(query, k=3)
    print(f"Query: {query}\n")
    for i, r in enumerate(results, 1):
        print(f"--- Result {i} ({r['ticker']}) ---")
        print(r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"])
        print()

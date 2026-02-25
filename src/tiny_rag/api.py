"""
FastAPI server with /ask endpoint for RAG queries.

GUIDE:
------
- GET /         → Health check
- GET /ask?q=... → RAG query. Params: q (required), k (default 6), ticker (optional)
- GET /docs     → Swagger UI

Ticker is inferred from query if omitted (e.g. "Alphabet" → GOOGL).
Uses rag.answer_with_rag() under the hood.

Run: uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001
"""
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query
from pydantic import BaseModel

from .rag import answer_with_rag, infer_ticker_from_query

app = FastAPI(
    title="Tiny RAG API",
    description="Ask questions about 10-K financial documents.",
    version="0.1.0",
)


class AskResponse(BaseModel):
    answer: str
    sources_count: int
    ticker_filter: str | None = None


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "docs": "/docs"}


@app.get("/ask", response_model=AskResponse)
def ask(
    q: str = Query(..., description="Your question about the financial documents"),
    k: int = Query(6, ge=1, le=20, description="Number of chunks to retrieve"),
    ticker: str | None = Query(None, description="Filter by ticker (e.g. GOOGL, AAPL)"),
):
    """
    Ask a question. Retrieves relevant context from pgvector, then answers via Ollama.
    If ticker is omitted, it may be inferred from the query (e.g. 'Alphabet' → GOOGL).
    """
    ticker_used = ticker or infer_ticker_from_query(q)
    result = answer_with_rag(q, k=k, ticker=ticker_used)
    return AskResponse(
        answer=result["answer"],
        sources_count=len(result["sources"]),
        ticker_filter=ticker_used,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

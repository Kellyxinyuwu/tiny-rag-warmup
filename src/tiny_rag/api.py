"""
FastAPI server with /ask endpoint for RAG queries.

GUIDE:
------
- GET /         → Simple liveness
- GET /health   → Readiness (DB + Ollama checks)
- GET /ask?q=... → RAG query. Requires X-API-Key header if API_KEY is set.
- GET /docs     → Swagger UI

Ticker is inferred from query if omitted (e.g. "Alphabet" → GOOGL).
Uses rag.answer_with_rag() under the hood.

Run: uvicorn tiny_rag.api:app --host 0.0.0.0 --port 8001
"""
import os
import time
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .health import check_database, check_ollama
from .logging_config import get_logger
from .rag import answer_with_rag, infer_ticker_from_query

logger = get_logger(__name__)

# If API_KEY is set, require it. If empty, auth is disabled (for local dev).
API_KEY = os.getenv("API_KEY", "").strip()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    """Verify X-API-Key header. Skip if API_KEY is not configured."""
    if not API_KEY:
        return  # Auth disabled
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(
    title="Tiny RAG API",
    description="Ask questions about 10-K financial documents. Requires X-API-Key header if API_KEY is set.",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Add request_id and log requests/responses."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()

        logger.info("request_start", method=request.method, path=request.url.path)
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info("request_end", status_code=response.status_code, elapsed_ms=round(elapsed_ms, 1))
        structlog.contextvars.unbind_contextvars("request_id")

        return response


app.add_middleware(RequestLoggingMiddleware)


class AskResponse(BaseModel):
    answer: str
    sources_count: int
    ticker_filter: str | None = None


@app.get("/")
def root():
    """Liveness check."""
    return {"status": "ok", "docs": "/docs"}


@app.get("/live")
def live():
    """Minimal liveness (no DB/Ollama checks). Use for basic connectivity."""
    return {"status": "ok"}


@app.get("/health")
def health():
    """
    Readiness check: DB + Ollama.
    Returns 200 if all checks pass, 503 if any fail.
    """
    try:
        db_ok, db_msg = check_database()
        ollama_ok, ollama_msg = check_ollama()
        healthy = db_ok and ollama_ok

        response = {
            "status": "healthy" if healthy else "unhealthy",
            "database": "ok" if db_ok else db_msg,
            "ollama": "ok" if ollama_ok else ollama_msg,
        }

        if not healthy:
            return JSONResponse(status_code=503, content=response)
        return response
    except Exception as e:
        logger.exception("health_check_error")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)},
        )


@app.get("/ask", response_model=AskResponse, dependencies=[Depends(verify_api_key)])
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
    logger.info("ask_request", query=q[:100], k=k, ticker=ticker_used)
    result = answer_with_rag(q, k=k, ticker=ticker_used)
    logger.info("ask_response", sources=len(result["sources"]))
    return AskResponse(
        answer=result["answer"],
        sources_count=len(result["sources"]),
        ticker_filter=ticker_used,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

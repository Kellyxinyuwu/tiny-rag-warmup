"""
Retry decorators for transient failures (DB, Ollama, network).

Config: 3 attempts, exponential backoff 1s–10s.
"""
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def _db_retry():
    """Retry for PostgreSQL connection/query failures."""
    import psycopg2

    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        reraise=True,
    )


def _ollama_retry():
    """Retry for Ollama/LLM connection failures (incl. httpx from ollama client)."""
    retryable = (ConnectionError, TimeoutError, OSError)
    try:
        import httpx

        retryable = retryable + (httpx.ConnectError, httpx.TimeoutException)
    except ImportError:
        pass

    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(retryable),
        reraise=True,
    )


retry_db = _db_retry()
retry_ollama = _ollama_retry()

"""
Structured logging setup for tiny_rag.

Configure once at startup, then use: from tiny_rag.logging_config import get_logger

Env: LOG_FORMAT=json for JSON output (production), default is pretty console.
     LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
"""
import os

import structlog


def _configure_structlog() -> None:
    """Configure structlog. Call once at import."""
    log_format = os.getenv("LOG_FORMAT", "console").lower()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_structlog()


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger for the given module name."""
    return structlog.get_logger(name)

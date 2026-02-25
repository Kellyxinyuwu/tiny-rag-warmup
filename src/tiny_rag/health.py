"""
Health check utilities for DB and Ollama.
"""
import os
from urllib.request import urlopen
from urllib.error import URLError

from dotenv import load_dotenv

load_dotenv()

_default_user = os.environ.get("USER", "postgres")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{_default_user}@localhost:5432/rag_db",
)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def check_database() -> tuple[bool, str]:
    """Check PostgreSQL connectivity. Returns (ok, message)."""
    try:
        import psycopg2

        conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def check_ollama() -> tuple[bool, str]:
    """Check Ollama connectivity. Returns (ok, message)."""
    try:
        url = f"{OLLAMA_HOST.rstrip('/')}/api/tags"
        with urlopen(url, timeout=3) as _:
            return True, "ok"
    except URLError as e:
        return False, str(e.reason) if hasattr(e, "reason") else str(e)
    except Exception as e:
        return False, str(e)

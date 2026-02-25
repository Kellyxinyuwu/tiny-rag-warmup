# API Authentication Guide

This project uses **API key authentication** via the `X-API-Key` header.

---

## How It Works

1. You set `API_KEY` in `.env` (e.g. `API_KEY=my-secret-key-123`).
2. Clients send that key in the `X-API-Key` header with each request.
3. The API compares the header value to `API_KEY`. If they match → allow. If not → 401 Unauthorized.

---

## Setup

### 1. Add API_KEY to .env

```bash
# In .env
API_KEY=your-secret-key-here
```

**Generate a secure key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Local development (no auth)

If `API_KEY` is empty or not set, auth is **disabled** — all requests are allowed. Useful for local testing.

---

## Making Requests

### With curl

```bash
curl -H "X-API-Key: your-secret-key-here" \
  "http://localhost:8000/ask?q=What%20are%20Alphabet%27s%20risks%3F"
```

### With Python requests

```python
import requests

response = requests.get(
    "http://localhost:8000/ask",
    params={"q": "What are Alphabet's main risks?"},
    headers={"X-API-Key": "your-secret-key-here"},
)
print(response.json())
```

### With Swagger UI (/docs)

1. Click **Authorize**
2. Enter your API key in the `X-API-Key` field
3. Click **Authorize**, then **Close**
4. All requests from the UI will include the header

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success — key valid |
| 401 | Unauthorized — missing or invalid key |
| 422 | Validation error — e.g. missing `q` param |

---

## Implementation Details

- **Header name:** `X-API-Key`
- **Dependency:** `verify_api_key()` in `api.py`
- **Protected routes:** `/ask` (and any route that uses the dependency)
- **Unprotected:** `/` (health check) — so load balancers can ping without a key

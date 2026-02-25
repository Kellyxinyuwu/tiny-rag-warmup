# CI/CD Guide

## GitHub Actions workflow

**File:** `.github/workflows/ci.yml`

**Triggers:** Push and PR to `main`, `feature/organized`

## Jobs

| Job | Purpose |
|-----|---------|
| **lint** | `ruff check src/ tests/` |
| **test** | `pytest tests/ -v` |
| **build** | Build Docker image (runs after lint + test pass) |

## Local checks (before push)

```bash
# Lint
ruff check src/ tests/

# Test
pytest tests/ -v
```

## Adding branches

Edit `.github/workflows/ci.yml`:

```yaml
on:
  push:
    branches: [main, feature/organized, your-branch]
  pull_request:
    branches: [main, feature/organized, your-branch]
```

## Ruff config

`ruff.toml` configures lint rules. Key settings:
- `target-version = "py310"`
- `line-length = 100`
- Select: E (errors), F (pyflakes), I (import sort), N (naming), W (warnings)
- Tests: assert allowed (S101 ignored)

# CI/CD Guide

## GitHub Actions workflow

**File:** `.github/workflows/ci.yml`

**Triggers:** Push and PR to `main`, `feature/final-organize`

## Jobs

| Job | Purpose |
|-----|---------|
| **lint** | `ruff check src/ tests/` |
| **test** | `pytest tests/ -v` |
| **build** | Build Docker image (runs after lint + test pass) |

## Local checks (before push)

```bash
# Lint
python3 -m ruff check src/ tests/

# Test
python3 -m pytest tests/ -v
```

## Branch configuration

CI runs only on the branches you list in the workflow. You choose which branches to include.

```yaml
on:
  push:
    branches: [main, feature/final-organize]
  pull_request:
    branches: [main, feature/final-organize]
```

**What this means:**

- **`push`** — CI runs when you push commits to any branch in the list.
- **`pull_request`** — CI runs when you open or update a PR whose **base** (target) branch is in the list.

**Why these branches?**

- `main` — Default branch; CI runs on every merge.
- `feature/final-organize` — Your active feature branch; CI runs before you merge to main.

**Adding or changing branches:** Edit the `branches:` list. Add any branch you want CI to run on (e.g. `feature/new-feature`). CI is not a default GitHub feature—only branches you list will trigger it.

## Ruff config

`ruff.toml` configures lint rules. Key settings:
- `target-version = "py310"`
- `line-length = 100`
- Select: E (errors), F (pyflakes), I (import sort), N (naming), W (warnings)
- Tests: assert allowed (S101 ignored)

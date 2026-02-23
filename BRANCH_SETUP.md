# Branch Setup — Done ✓

## Current State

| Branch | Purpose |
|--------|---------|
| **main** | Original baseline (PDF + simple chunk) |
| **original** | Backup of original (same as main) |
| **feature/extended** | Extended pipeline; **active development** ← you are here |

---

## What Was Done

1. Created `original` branch from main (preserves baseline)
2. Created `feature/extended` branch
3. Committed all extended changes on `feature/extended`
4. `main` and `original` stay at commit `3695b9d` (original version)
5. `feature/extended` has commit `ef5d8b7` (extended pipeline)

---

## Workflow From Now On

```bash
# Always work on feature/extended
git checkout feature/extended

# When ready to merge to main
git checkout main
git merge feature/extended
git push origin main
```

---

## Verify

```bash
git branch -a
git log --oneline -3
```

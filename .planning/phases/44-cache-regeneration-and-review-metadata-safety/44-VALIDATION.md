# Phase 44 Validation

## Focused

```bash
uv run pytest \
  tests/analysis/test_cache_advice.py \
  tests/analysis/test_launch_readiness.py \
  tests/analysis/test_remediation.py \
  tests/test_cache_status_cli.py \
  tests/test_review_metadata.py \
  tests/analysis/test_response_cache.py \
  -q
```

## Full

```bash
uv run pytest -q
```

## Static

```bash
git diff --check
node /Users/m.v.shchegolev/.codex/get-shit-done/bin/gsd-tools.cjs verify phase-completeness 44
```

## Manual Smoke

```bash
uv run saymo cache-status -p standup
```

Expected: read-only output with statuses, explicit F5 cost warning only for
missing/stale/partial caches, and targeted commands for prepared audio versus
response cache.

---
phase: 15-meeting-ask-and-search
status: passed
verified: 2026-05-20
---

# Phase 15 Verification

## Result

status: passed

## Requirement Coverage

- ASK-01: `saymo meeting-search` searches local meeting sessions by profile,
  session id/prefix, date range, speaker label, trigger category, and keyword.
- ASK-02: `saymo meeting-ask` answers from local transcript evidence and prints
  citations to session segments.
- ASK-03: `saymo meeting-summary --sanitized` exports reviewable markdown while
  omitting raw audio names, source sample paths, secrets, and config values.

## Verification Commands

- `.venv/bin/python -m pytest -q tests/analysis/test_meeting_memory.py tests/test_meeting_memory_cli.py`
  - 11 passed
- `git diff --check`
  - no whitespace errors

## Residual Notes

- Phase 15 uses deterministic local retrieval. External source grounding and
  optional local LLM drafting are Phase 16 scope.

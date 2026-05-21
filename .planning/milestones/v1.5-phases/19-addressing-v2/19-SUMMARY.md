# Phase 19 Summary: Addressing v2

## Completed

- Added addressing evidence and local context to deterministic decisions.
- Added direct-handoff, bare-call, plain-mention, and full-name mention
  handling.
- Added per-profile `meetings.<profile>.addressing.handoff_patterns` and
  `mention_only_patterns`.
- Wired addressing pattern tuning into trigger-check, trigger capture,
  trigger-sample replay/evaluation, answer drafting, and auto mode.
- Extended `trigger-check` explain output with matched phrase, context,
  evidence, and decision path.

## Verification

- `uv run pytest tests/analysis/test_addressing.py tests/analysis/test_trigger_capture.py tests/test_trigger_check.py tests/test_auto_qa_flow.py tests/test_config.py`

## Notes

- Non-question name mentions now skip unless they match a handoff pattern or
  are a bare trigger call.
- Direct questions such as "John, what do you think?" still produce answer
  candidates.
- Configured regexes use `{trigger}` as the escaped trigger placeholder.


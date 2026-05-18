# Summary 06-03: Shadow-Mode Classifier Diagnostics

## Completed

- Added `--classifier-shadow` and `--model-dir` to `trigger-eval`.
- Added `--classifier-shadow` and `--model-dir` to `trigger-check`.
- Printed classifier accepted/rejected confidence and disagreement counts
  without changing deterministic trigger/addressing decisions.
- Documented sample decision labels, classifier training, and shadow-mode usage.

## Files

- `saymo/commands/tests.py`
- `README.md`
- `docs/QUICK-START.md`
- `docs/PRD.md`
- `tests/test_trigger_check.py`

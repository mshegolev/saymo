# Summary 06-02: Lightweight Local Trigger Classifier

## Completed

- Added `saymo.analysis.trigger_classifier`, a dependency-free local classifier
  trained from transcript and sample-metadata features.
- Added training threshold checks for total labeled samples and per-class
  accepted/rejected counts.
- Added local JSON artifact save/load helpers and profile-safe artifact paths.
- Added `trigger-classifier train`, `inspect`, and `delete`.

## Files

- `saymo/analysis/trigger_classifier.py`
- `saymo/commands/tests.py`
- `tests/analysis/test_trigger_classifier.py`
- `tests/test_trigger_check.py`

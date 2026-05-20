# Summary 05-02: Speaker-Aware Trigger Evaluation

## Completed

- `trigger-eval` still prints aggregate stored/current category counts.
- It now also prints per-speaker records, misses, false positives, and current
  answer counts for `me`, `other`, and `unknown`.
- Existing unlabeled samples are included under `unknown`.

## Tests

- `test_trigger_eval_reports_counts_misses_and_false_positives`
- `test_trigger_eval_groups_counts_by_speaker`


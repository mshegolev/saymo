# Summary 02-03: Promote-And-Rerun Workflow

## Completed

- Added `--promote` to `saymo trigger-eval`.
- Promotion reuses the existing safe config update path from trigger setup.
- Evaluation reloads config after promotion so the same command shows the new
  result.

## Tests

- `test_trigger_eval_promotes_sample_variant_and_reruns`


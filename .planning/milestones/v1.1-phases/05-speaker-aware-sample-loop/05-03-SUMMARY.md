# Summary 05-03: Sample Label Review Commands And Docs

## Completed

- Added `saymo trigger-samples label <sample.json> --speaker me|other|unknown`.
- The command updates only local sample metadata and preserves existing fields.
- README and quick-start docs now show the speaker-label workflow.

## Tests

- `test_trigger_samples_label_updates_speaker_metadata`
- `test_trigger_samples_list_replay_and_sanitized_report`


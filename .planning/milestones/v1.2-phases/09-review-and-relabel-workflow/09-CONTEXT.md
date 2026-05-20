# Phase 9 Context: Review And Relabel Workflow

## Goal

Make saved trigger samples easy to filter, replay, correct, and report after a
call without manually editing JSON files.

## Baseline

- `trigger-samples list` currently filters only by profile/category.
- `trigger-samples label` corrects speaker labels.
- `trigger-samples decision` corrects accepted/rejected/unlabeled answer
  decisions.
- `trigger-samples replay` reclassifies one sample and can play adjacent WAV.
- `trigger-samples report` exports a sanitized markdown report without raw
  transcripts.
- Phase 8 added `session_id`, `session_name`, `session_sequence`, and
  `trigger-sessions list/summary`.

## Decisions

- Keep sample JSON and adjacent WAV in their existing category folder; category
  relabeling moves both files to the target category folder.
- Add list filters for session, speaker, answer decision, classifier
  disagreement, and date range while preserving old profile/category behavior.
- Implement a CLI review queue that is deterministic and scriptable: it can run
  interactively by default and non-interactively with `--limit`, `--no-play`,
  and skip/keep options.
- Keep reports sanitized by default; group by session then category and avoid
  transcript text or raw audio payloads.

## Acceptance Criteria

- REV-01: `trigger-samples list` supports profile, session, category, speaker,
  answer decision, classifier disagreement, and date-range filters.
- REV-02: `trigger-samples category SAMPLE.json --category <category>` updates
  metadata and keeps the WAV discoverable.
- REV-03: `trigger-samples review` can replay samples and write category,
  speaker, and answer-decision corrections in one command flow.
- REV-04: `trigger-samples report` groups sanitized output by session and
  category.

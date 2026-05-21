# Phase 18 Context: Post-call Review Queue

## Goal

Let the user review the highest-value samples from one completed session first
and apply labels needed for safer live behavior.

## Requirements

- REV-05: prioritized post-call queue surfaces likely handoffs, questions,
  name mentions, unlabeled speaker windows, and classifier-critical samples.
- REV-06: category, speaker, and answer-decision labels are applied through
  commands, not manual JSON edits.
- REV-07: review progress reports unknown speakers, unlabeled decisions,
  accepted/rejected counts, and classifier-readiness blockers.

## Existing System

- `saymo/commands/tests.py` owns `trigger-samples list/replay/review/report`
  and low-level metadata writes.
- `saymo/analysis/trigger_review.py` owns reusable filtering, report, and
  relabel helpers.
- `saymo/analysis/trigger_readiness.py` already reports classifier readiness
  over reviewed samples.
- Session ledgers are available through v1.4; sample JSON remains the source of
  truth for review labels.

## Design Decisions

- Add pure queue/progress helpers in `trigger_review.py` so CLI output and
  future regression replay can reuse the same logic.
- Add non-interactive `trigger-samples queue` for session-scoped prioritized
  review previews.
- Add `trigger-samples progress` for review coverage and readiness blockers.
- Keep existing `trigger-samples review/category/label/decision` commands as
  the label application path for REV-06, and do not duplicate metadata writers.


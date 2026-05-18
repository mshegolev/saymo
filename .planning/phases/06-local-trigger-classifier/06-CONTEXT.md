# Phase 6 Context: Local Trigger Classifier

## Goal

Train a local sample-based classifier from accepted/rejected trigger decisions
and compare it against deterministic gating before it affects calls.

## Baseline

- Phase 5 sample metadata supports `speaker` labels: `me`, `other`, and
  `unknown`.
- `trigger-samples list|label|replay|report` can review local samples.
- `trigger-eval` compares saved samples against current deterministic
  trigger/addressing behavior and reports speaker-aware misses and false
  positives.
- No accepted/rejected answer-decision label or classifier artifact exists yet.

## Decisions

- Store answer-decision labels in the existing sample JSON sidecar as
  `answer_decision`.
- Keep supported labels explicit: `accepted`, `rejected`, and `unlabeled`.
- Use a dependency-free local classifier so the phase does not add cloud or ML
  runtime requirements.
- Run the learned classifier only in shadow mode during this phase; live-call
  decisions stay controlled by deterministic trigger/addressing logic.

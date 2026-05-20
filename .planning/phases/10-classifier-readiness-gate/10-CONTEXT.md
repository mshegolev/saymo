# Phase 10 Context: Classifier Readiness Gate

## Goal

Let the local trigger classifier assist live-call decisions only when local
evidence is strong enough and deterministic trigger/addressing checks remain
the hard safety boundary.

## Baseline

- Phase 6 added a dependency-free local Naive Bayes classifier trained from
  accepted/rejected sample metadata.
- `trigger-eval --classifier-shadow` and `trigger-check --classifier-shadow`
  show learned confidence without changing live decisions.
- Phase 8/9 provide session grouping and corrected labels.
- `saymo auto` currently uses deterministic trigger/addressing only.

## Decisions

- Add readiness reporting before live assist: label balance, category coverage,
  mention-vs-handoff coverage, and minimum thresholds.
- Add deterministic holdout evaluation from local metadata; no cloud services.
- Store live-assist opt-in as a local per-profile artifact under the classifier
  model directory so `config.yaml` secrets and user settings are not rewritten
  implicitly.
- In live auto-mode, learned classifier can only downgrade an already
  deterministic answer candidate to skip or confirm the deterministic answer;
  it cannot bypass trigger/addressing checks.

## Acceptance Criteria

- CLS-01: `trigger-classifier readiness` reports threshold pass/fail and gaps.
- CLS-02: `trigger-classifier evaluate` reports local holdout answer/skip
  precision/recall-style metrics.
- CLS-03: `trigger-classifier live-assist enable` is refused until readiness
  passes, and `saymo auto` respects the local guard.
- CLS-04: `trigger-check` can explain live-assist accept/reject diagnostics
  using local features and confidence.


# Phase 51: Dry-Run Evidence And Rehearsal Feedback - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase closes v1.14 by turning `saymo dry-run` output into reusable,
sanitized evidence. The operator should be able to save a dry-run artifact,
feed it into rehearsal, session scorecard, and safety-soak flows, and compare
the latest result with a previous result before joining a real call.

</domain>

<decisions>
## Implementation Decisions

### Dry-Run Evidence Artifact
- Reuse the existing launch-readiness artifact schema and
  `LaunchReadinessReport`/`LaunchReadinessCheck` data model; do not create a
  second dry-run evidence format.
- `saymo dry-run --output <path>` should remain the main way to save a
  sanitized artifact, with `mode: dry-run`, timestamps, profile, provider,
  check status, detail/stale reasons, actions, rerun commands, and counts.
- Evidence must exclude raw meeting text, prompt text, generated response text,
  transcript windows, audio bytes, secrets, voice samples, training data, and
  protected local assets.
- Keep JSON stdout concise and artifact-metadata-free except for `mode`; full
  artifact metadata belongs in the explicit `--output` file.

### Rehearsal, Scorecard, And Safety-Soak Reuse
- Prefer wiring saved dry-run artifacts through the existing launch evidence
  loader rather than adding one-off parser code to each command.
- Existing `session-scorecard --launch-json` and `safety-soak` launch metrics
  should accept dry-run mode artifacts as launch-readiness evidence.
- `rehearsal` should be able to record or reference the dry-run artifact path
  so the operator can correlate rehearsal output with the launch-readiness
  state used before the call.
- Keep all consumed evidence sanitized in scorecard/soak JSON and Markdown.

### Latest-vs-Previous Comparison
- Add a small read-only comparison path for two saved launch-readiness/dry-run
  artifacts, focused on readiness improvements/regressions.
- Compare stable fields: ready state, block/warn counts, failed labels,
  blocker categories, response-cache counts, provider readiness, daemon
  readiness, and rerun command changes.
- The comparison should be operator-readable and machine-readable where
  practical, without raw checks or private content.
- Do not rerun checks, mutate artifacts, delete old evidence, or infer private
  content from paths.

### Safety Boundary
- Evidence commands must be read-only over saved JSON artifacts unless an
  explicit `--output` writes a new sanitized report.
- No TTS synthesis, playback, recording, provider mutation, launchd mutation,
  cache rebuild, voice retraining, model download, or protected asset access.
- Tests should use temp artifacts with private sentinels to prove redaction.
- Missing/invalid evidence should produce clear warnings rather than crashing
  or attempting repair.

### Claude's Discretion
- Choose the smallest CLI/API surface that satisfies EVID-03; a
  `saymo dry-run compare --current ... --previous ...`-style subcommand or a
  separate `saymo dry-run-compare` command is acceptable if it matches local
  Click patterns.
- Add tests before production changes, then keep implementation narrow to
  evidence loading, rendering, and safe command wiring.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `write_launch_readiness_artifact(report, output, mode="dry-run")` already
  writes flat launch-readiness JSON artifacts.
- `saymo.analysis.launch_evidence.load_launch_evidence` and
  `summarize_launch_evidence` already normalize saved launch-readiness
  artifacts into sanitized `LaunchEvidence`.
- `session_scorecard` already folds optional launch JSON into
  `LaunchScorecardMetrics`.
- `safety_soak` already aggregates launch/readiness metrics from scorecards.
- Rehearsal artifacts are already sanitized and written under per-profile
  directories.

### Established Patterns
- CLI tests use `CliRunner`, temp JSON artifacts, and private sentinel strings.
- Evidence serialization keeps raw transcript and live-control private details
  out of JSON and Markdown.
- Launch evidence summaries expose stable aggregates, not raw prompt or answer
  text.
- Safety-soak turns scorecards into pass/fail gates with totals and violations.

### Integration Points
- `saymo/commands/dry_run.py` owns dry-run artifact writing and is the natural
  CLI entry for dry-run comparison.
- `saymo/analysis/launch_evidence.py` is the right place for normalized compare
  logic over two saved launch-readiness artifacts.
- `saymo/analysis/session_scorecard.py` and command tests should verify dry-run
  mode artifacts are accepted as launch evidence.
- `tests/test_dry_run_cli.py`, `tests/analysis/test_launch_evidence.py`,
  `tests/test_rehearsal_cli.py`, `tests/test_session_scorecard_cli.py`, and
  `tests/test_safety_soak_cli.py` are likely test targets.

</code_context>

<specifics>
## Specific Ideas

- The user needs a pre-call answer to "did readiness improve since the last
  dry-run?" without opening raw JSON.
- The comparison should call out categories like source-data, provider,
  audio-device, call-control, response-cache, and voice-cache.
- Phase 51 should preserve the existing dry-run guarantee: output and evidence
  prove state, but do not repair it.

</specifics>

<deferred>
## Deferred Ideas

- Live Answer Policy, answer confidence gates, and manual approval modes belong
  to v1.15.
- Calendar-triggered unattended launch and automatic provider repair remain out
  of scope.
- Rich historical dashboards over many dry-run artifacts can come later; this
  phase only needs latest-vs-previous comparison.

</deferred>

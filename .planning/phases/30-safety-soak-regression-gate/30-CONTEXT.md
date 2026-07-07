# Phase 30: Safety Soak Regression Gate - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning
**Source:** Roadmap + Phase 28 scorecards + Phase 29 remediation hints

<domain>
## Phase Boundary

Phase 30 adds a repeatable local safety soak gate for one profile. It should
run over saved rehearsal artifacts and real-session scorecards, enforce the
handbrake/approval safety invariants, compare reliability drift against a
prior baseline, and emit one pre-call/pre-merge pass/fail summary.

This phase does not build a native UI, automatically edit configuration, or
install new ML dependencies.
</domain>

<decisions>
## Implementation Decisions

### Soak Inputs
- Reuse Phase 28 `SessionScorecard` as the normalized input contract.
- Support one or more `--rehearsal PATH` inputs by building scorecards from
  rehearsal artifacts.
- Support one or more `--scorecard-json PATH` inputs so real captured-session
  scorecards can be included without rerunning expensive replay in tests.
- Keep direct `--session` replay integration optional; the gate can consume
  scorecard JSON produced by `saymo session-scorecard`.

### Safety Invariants
- Fail if a scorecard indicates Saymo would speak while auto-answer is off,
  manual takeover is active, or hard-disable is active.
- Fail if scorecard evidence reports automatic playback while an approval or
  handbrake boundary should have blocked it.
- Treat blocked automatic playback as evidence to review, not as a failure by
  itself unless paired with forbidden speaking.

### Drift Comparison
- Aggregate false handoffs, missed handoffs, question noise, unknown speakers,
  and latency from all scorecards.
- Compare with a prior soak JSON baseline when provided.
- Fail drift only when current metrics worsen relative to baseline; equal or
  improved metrics pass.

### Output and Storage
- Add a single `saymo safety-soak` command with Markdown-like terminal output,
  optional Markdown output, optional JSON output, and optional baseline JSON.
- Output should include status, checked artifacts, safety violations, drift,
  and remediation references.
- JSON/Markdown exports remain sanitized by construction because they consume
  sanitized scorecards.

### Claude's Discretion
- Exact module names may follow Phase 28/29 analysis module patterns.
- It is acceptable to keep the first implementation CLI-focused and
  deterministic.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.session_scorecard` provides scorecard dataclasses, JSON
  export, rehearsal loading, and regression metric mapping.
- `saymo.analysis.remediation` provides compact remediation output and rerun
  commands.
- `saymo.commands.tests` is the existing home for local diagnostic commands.

### Established Patterns
- Analysis modules use dataclasses plus JSON/Markdown helpers.
- CLI commands take profile-scoped inputs, print report text, and optionally
  write Markdown/JSON files.
- Tests can construct local artifacts directly without macOS/device access.

### Integration Points
- Add `saymo.analysis.safety_soak`.
- Add `saymo safety-soak` in `saymo/commands/tests.py`.
- Add focused analysis and CLI tests.
</code_context>

<specifics>
## Specific Ideas

- JSON fields: `profile`, `status`, `items`, `totals`, `violations`,
  `drift`, `warnings`.
- CLI flags: `--profile/-p`, repeated `--rehearsal`, repeated
  `--scorecard-json`, `--baseline-json`, `--audit-root`, `--output`,
  `--json-output`.
- Markdown heading: `# Saymo Safety Soak`.
- Remediation line: point users to `saymo session-scorecard` or the specific
  artifact rerun when a violation exists.
</specifics>

<deferred>
## Deferred Ideas

- Native menu bar or launchd scheduled soak remains future work.
- Automatic session discovery across all local artifacts can be added after
  explicit input mode is stable.
- Deep answer-cockpit unapproved draft replay remains future work unless an
  existing scorecard exposes that evidence.
</deferred>

---

*Phase: 30-safety-soak-regression-gate*
*Context gathered: 2026-07-06*


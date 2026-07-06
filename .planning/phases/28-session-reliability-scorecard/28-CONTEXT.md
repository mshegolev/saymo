# Phase 28: Session Reliability Scorecard - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning
**Source:** Roadmap + Phase 27 artifact contract + existing replay/control audit modules

<domain>
## Phase Boundary

Phase 28 adds a local, sanitized reliability scorecard for one saved rehearsal
artifact or one real trigger-capture session. It should summarize whether the
session was safe enough to trust in a call by combining trigger/addressing,
speaker/classifier readiness, playback gate, handbrake, latency, cancellation,
and blocked automatic speaking evidence.

This phase produces report data and export commands only. It does not add the
remediation taxonomy from Phase 29 or the repeatable multi-session soak gate
from Phase 30.
</domain>

<decisions>
## Implementation Decisions

### Scorecard Inputs
- Support rehearsal artifacts from Phase 27 as the first-class input because
  they already include preflight, hotkey, live-control state, playback gate,
  and sanitized dry-run decision evidence.
- Support saved trigger-capture sessions through existing regression replay
  metrics so real sessions can report false handoffs, missed handoffs, question
  noise, speaker coverage, review coverage, and classifier readiness.
- Treat live-control audit JSONL as optional evidence; missing audit logs should
  not prevent scorecard generation but should produce an explicit warning.
- Keep loaders tolerant of malformed local files by skipping bad audit rows and
  surfacing a warning instead of leaking raw local content.

### Metrics Contract
- Use pass/warn/fail sections so the user can scan readiness before a call.
- Trigger/addressing metrics should include triggered decisions, addressed-to-me
  decisions, mention-only skips, question noise, false handoffs, missed
  handoffs, speaker coverage, review coverage, and classifier readiness impact
  when the source provides them.
- Playback and handbrake metrics should include approved speak attempts,
  blocked automatic playback, stop/takeover/hard-disable events, cancellation
  evidence, latency fields when present, and max-duration interruption evidence
  when present.
- Do not invent missing evidence; unknown or unavailable values should be
  explicit in JSON and concise in Markdown.

### Sanitization
- Markdown and JSON exports are sanitized by default.
- Rehearsal transcript snippets are omitted from scorecard exports unless a
  later local-debug flag explicitly opts in; Phase 28 default output must not
  include raw transcript text, raw audio paths, secrets, or local meeting text.
- Real session outputs should reuse existing regression replay sample names and
  aggregate counts rather than transcript text.
- Local file paths may be reduced to basenames or relative artifact labels when
  needed for user orientation.

### CLI and Storage
- Add a profile-scoped CLI command that follows existing `saymo` report
  command style and writes optional Markdown/JSON outputs.
- Suggested command shape: `saymo session-scorecard -p personal --rehearsal
  PATH` and `saymo session-scorecard -p personal --session SESSION`.
- Default printed output should be a concise Markdown-like report; `--output`
  writes Markdown and `--json-output` writes sanitized JSON.
- Keep generated files in user-specified locations or local `~/.saymo` paths;
  never commit generated scorecards.

### Claude's Discretion
- Exact module names may follow local `saymo.analysis.*` patterns.
- It is acceptable to introduce a dedicated scorecard module if it reduces
  coupling between CLI, rehearsal artifacts, replay metrics, and audit loading.
- If Phase 28 needs an intermediate data model, prefer dataclasses with
  explicit JSON conversion, matching existing `rehearsal` and
  `regression_replay` modules.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.rehearsal` provides `RehearsalArtifact`, JSON
  serialization, loading, status checks, profile-local storage, and sanitized
  rehearsal data.
- `saymo.analysis.regression_replay` provides `RegressionMetrics`, sanitized
  JSON conversion, and Markdown rendering for real trigger sessions.
- `saymo.analysis.live_control` provides state and audit paths plus normalized
  action names for stop, takeover, hard-disable, approved speak, and blocked
  playback evidence.
- `saymo.commands.tests` already hosts diagnostic/report commands such as
  `rehearsal`, `provider-latency`, `trigger-sessions replay`, and output
  flags.

### Established Patterns
- Analysis modules define dataclasses and pure serialization/rendering helpers;
  CLI commands assemble local inputs and print/write reports.
- Tests cover analysis behavior under `tests/analysis/` and CLI behavior in
  top-level `tests/test_*_cli.py` or `tests/test_trigger_check.py`.
- Report helpers intentionally avoid raw transcript/audio content and prefer
  aggregate counts, sample basenames, and sanitized JSON/Markdown.

### Integration Points
- CLI command should be registered on the existing Click `main` command in
  `saymo/commands/tests.py`, where related diagnostics already live.
- Rehearsal scorecards can load a specific JSON artifact path or discover the
  latest profile artifact later if useful; Phase 28 only needs explicit path
  support to satisfy the saved artifact requirement.
- Real-session scorecards can call the same underlying replay/evaluation path
  used by `trigger-sessions replay` or accept prebuilt regression metrics if
  that keeps tests focused.
</code_context>

<specifics>
## Specific Ideas

- JSON top-level fields: `profile`, `source_type`, `source_id`, `status`,
  `trigger_metrics`, `playback_metrics`, `safety_metrics`, `warnings`.
- Markdown sections: `Summary`, `Trigger and Addressing`, `Playback and
  Handbrake`, `Warnings`.
- For rehearsal artifacts, map `decision.would_speak`, `decision.auto_action`,
  `decision.addressing`, `decision.question`, `checks`, and
  `live_control_state` into scorecard metrics.
- For live-control audit logs, count `approved_speak`, `stop`, `takeover`,
  `hard_disable`, `automatic_playback_blocked`, and cancellation-like results
  by normalized action/result.
</specifics>

<deferred>
## Deferred Ideas

- Human-readable fix recommendations belong to Phase 29.
- Multi-session baseline drift and soak failure policy belong to Phase 30.
- Rich browser/native scorecard UI remains future work.
- Local-debug transcript inclusion can be considered later, but default Phase
  28 exports stay sanitized.
</deferred>

---

*Phase: 28-session-reliability-scorecard*
*Context gathered: 2026-07-06*

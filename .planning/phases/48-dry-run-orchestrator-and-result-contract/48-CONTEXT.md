# Phase 48: Dry-Run Orchestrator And Result Contract - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase creates the operator-facing dry-run shell for v1.14. It should give
one profile/provider command that reports `ready` or `not ready` using the
existing launch-readiness contract, without starting realtime mode and without
mutating audio, cache, voice, model, or provider state.

</domain>

<decisions>
## Implementation Decisions

### Command Contract
- Add a dry-run command or mode that is distinct from `saymo auto` and does
  not start realtime capture, playback, or provider meeting actions.
- Keep the default invocation profile/provider based, matching existing
  `call-ready` and `auto-preflight` conventions: `-p/--profile` plus optional
  `--provider`.
- Prefer reusing `LaunchReadinessReport` and `LaunchReadinessCheck` over
  inventing a second result model.
- Preserve existing `saymo call-ready` behavior for backward compatibility.

### Output Contract
- The first human-readable line must be a concise top-level result:
  `dry-run: ready` or `dry-run: not ready`.
- Human output should group blockers, warnings, exact actions, and rerun
  commands in the existing remediation style.
- JSON output must be sanitized and machine-readable, with profile, provider,
  ready, check counts, and check details.
- Exit code should mirror readiness: `0` when ready, non-zero when blocking
  readiness fails.

### Non-Destructive Safety
- Dry-run must not synthesize audio, play audio, delete cache artifacts,
  retrain, download voice models, or mutate protected `.saymo` assets.
- Dry-run must not pass `prepare=True` to launch-readiness source checks in
  this phase; source creation/repair belongs to Phase 49.
- Dry-run diagnostics may suggest exact commands, but those commands remain
  operator-triggered.
- Tests should monkeypatch dangerous or OS-facing calls and assert the dry-run
  path is read-only.

### Artifact Boundary
- If the user asks for an output file, write a sanitized JSON artifact using
  the same privacy boundary as launch-readiness evidence.
- Artifact mode should identify itself as dry-run evidence without embedding
  raw meeting text, prompt text, response text, audio bytes, secrets, voice
  samples, or training data.
- Avoid storing command output that can include private daily note bodies or
  generated answer text.
- Later phases can extend this artifact for source/cache/provider/evidence
  details; Phase 48 establishes the shell and schema hook.

### Claude's Discretion
- Choose the command name and module organization conservatively based on the
  existing CLI structure. Prefer a small module over expanding the very large
  `saymo/commands/tests.py`.
- Add helper functions only where they reduce duplication with
  `saymo.commands.call_ready`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.commands.call_ready.call_ready` already wires
  `collect_launch_readiness`, `render_launch_readiness`, optional JSON output,
  optional artifact output, and readiness-based exit codes.
- `saymo.analysis.launch_readiness.LaunchReadinessReport` and
  `LaunchReadinessCheck` already provide sanitized structured readiness data.
- `render_grouped_launch_remediation` already groups failed/warning checks by
  severity with actions and rerun commands.
- `write_launch_readiness_artifact` already writes sorted sanitized JSON with
  evidence metadata.

### Established Patterns
- Click commands live under `saymo/commands/` and register with
  `@main.command(...)`; modules are imported from `saymo/commands/__init__.py`.
- CLI tests use `CliRunner`, temporary YAML config, and monkeypatching of
  readiness collectors.
- Launch-readiness checks are read-only unless `prepare=True` is explicitly
  passed for daily note creation.
- Tests assert private sentinel strings are absent from stdout/artifacts.

### Integration Points
- New dry-run CLI should call `collect_launch_readiness(..., prepare=False)`.
- Rendering can either wrap existing launch-readiness rendering or share helper
  logic while replacing the top-level label with `dry-run`.
- Artifact writing can call the existing writer and then adjust safe metadata,
  or add a small launch-readiness writer option if tests prove the old mode is
  too call-ready specific.
- Target tests belong near `tests/test_call_ready_cli.py` or a new
  `tests/test_dry_run_cli.py`.

</code_context>

<specifics>
## Specific Ideas

- The user wants “before a real call one command -> everything is ready”.
- Phase 48 should be deliberately narrow: command shell, result contract, and
  no-mutation proof. Obsidian creation, cache repair advice depth, provider
  health details, and latest-vs-previous comparison are later phases.

</specifics>

<deferred>
## Deferred Ideas

- Phase 49 handles Obsidian daily-note creation/selection, prepared audio
  source hash checks, response-cache staleness, and cloned voice metadata.
- Phase 50 handles provider tab, BlackHole, audio routing, call-control daemon,
  and LaunchAgent health expansion.
- Phase 51 handles dry-run evidence integration with rehearsal, scorecards,
  safety-soak, and latest-vs-previous comparison.

</deferred>

# Phase 11: Diarization Adapter And Config - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 11 establishes the optional diarization foundation only: config,
availability diagnostics, backend-neutral result contracts, and docs. It must
not run session diarization or alter speaker labels yet; those belong to Phases
12 and 13.

</domain>

<decisions>
## Implementation Decisions

### Backend Strategy
- Diarization stays disabled by default and never becomes a required install
  dependency.
- Start with a pyannote-style optional backend interface, loaded only when the
  user requests it.
- Missing backend packages, tokens, or model access should produce actionable
  diagnostics instead of import-time crashes.
- Backend code must expose stable Saymo-owned dataclasses so later phases do
  not depend on backend-specific objects.

### Configuration
- Add a top-level `diarization` config section for engine, enabled flag, model
  id, device, speaker-count bounds, and auth token env name.
- Use env interpolation and env-var names for secrets; CLI/report output should
  never print token values.
- Keep profile/session-specific behavior for later phases; Phase 11 only
  establishes global defaults and diagnostics.
- Invalid optional config should be normalized to safe defaults where possible.

### CLI Diagnostics
- Add a direct `saymo diarization-check` command because setup troubleshooting
  is not tied to one session.
- Output should be plain, grep-friendly lines similar to existing
  `trigger-check` diagnostics.
- The command should report disabled, missing dependency, missing token, and
  ready states without contacting cloud services.
- A user should be able to override engine/model/device from the CLI for a
  setup dry run.

### Claude's Discretion
None.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.config` already uses dataclasses, YAML loading, and env interpolation.
- `saymo.commands.tests` hosts diagnostic CLI commands and can add
  `diarization-check` consistently with `trigger-check`.
- `saymo.analysis.trigger_sessions` and `trigger_review` already provide the
  storage/review patterns that later phases will extend.

### Established Patterns
- Optional runtime behavior should be local-by-default and fail with
  `click.ClickException` or diagnostic output, not hard imports.
- Existing sample metadata uses simple JSON-compatible dataclasses and stable
  labels such as `me`, `other`, and `unknown`.
- Tests use `CliRunner` and focused unit tests for analysis helpers.

### Integration Points
- Add config dataclasses in `saymo/config.py`.
- Add backend-neutral helpers under `saymo/analysis/diarization.py`.
- Add CLI output in `saymo/commands/tests.py`.
- Add tests under `tests/analysis/` and existing CLI tests.

</code_context>

<specifics>
## Specific Ideas

Use pyannote as the first documented optional backend, but keep the code shaped
so WhisperX/NeMo-style adapters can be added later.

</specifics>

<deferred>
## Deferred Ideas

- Session diarization execution and sidecar writes move to Phase 12.
- Speaker suggestion review/promotion and quality reports move to Phase 13.
- Real-time diarization in `saymo auto` remains out of scope.

</deferred>

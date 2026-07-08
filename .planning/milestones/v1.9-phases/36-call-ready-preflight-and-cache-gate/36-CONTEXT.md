# Phase 36: Call-Ready Preflight and Cache Gate - Context

**Gathered:** 2026-07-08
**Status:** Ready for planning
**Source:** Smart Discuss auto-accepted for autonomous run

<domain>
## Phase Boundary

Phase 36 delivers the first operator-facing `call-ready` gate for the current
profile/provider. It covers daily-note readiness, prepared standup audio
freshness, response-cache coverage, cloned-voice metadata, and grouped
remediation. It should not yet perform deeper provider tab/audio route
verification, daemon/LaunchAgent work, realtime fail-closed behavior, or full
scorecard/safety-soak evidence feedback; those belong to phases 37-40.

</domain>

<decisions>
## Implementation Decisions

### Command Contract

- Add a `saymo call-ready -p <profile> --provider <provider>` command as the
  main operator entry point for Phase 36.
- Default command mode should be check-only except for reading config and local
  metadata. Mutating work such as creating the daily note or running prepare
  should require an explicit flag such as `--prepare`.
- The command should print one top-level result: `call-ready: ready` or
  `call-ready: not ready`.
- The command should support JSON output if it is cheap to add, but human
  readable output and exact rerun commands are the primary Phase 36 interface.

### Readiness Semantics

- Use structured checks with severities `block`, `warn`, and `info`; Phase 36
  is ready only when all blocking checks pass.
- Response-cache and prepared standup freshness are blocking for this
  `call-ready` gate, because the milestone exists to avoid a green launch that
  still has unsafe cache gaps.
- Provider/audio readiness may be represented as a placeholder or delegated
  lower-level `auto-preflight` check in Phase 36, but it must not be declared
  complete until Phase 37 adds deeper checks.
- Do not silently accept WAV existence as readiness; cache metadata must match
  current voice/profile/source expectations.

### Daily Note and Prepared Audio

- Reuse the existing Obsidian configuration and daily-note helper logic instead
  of keeping a second YAML parser as the long-term implementation path.
- Treat daily note file existence and useful standup content as separate
  checks. A just-created template with only placeholders should not satisfy
  standup source readiness.
- If `--prepare` is passed, daily-note creation is allowed because it is
  idempotent and preserves existing note content.
- If `--prepare` is passed, preparing standup audio and response-cache variants
  may call existing `prepare` / `prepare-responses` behavior, but the readiness
  report must still verify the resulting files and metadata.

### Cache and Voice Metadata

- Reuse `ResponseCache`, `build_library`, `build_voice_cache_metadata`, and
  existing voice selector/cache metadata checks.
- Report response-cache coverage as concrete counts, for example `47/48
  variants ready`, plus stale/missing examples where available.
- Prepared standup cache should report the concrete audio path and stale reason
  if missing or invalid.
- Output must remain privacy-safe: include hashes, counts, paths, and check
  names, but not raw daily-note text, private transcript text, or generated
  answer content.

### Claude's Discretion

- Choose internal module names that match current repo patterns. Preferred
  direction from research: move shared contracts into `saymo.analysis` and keep
  Click wrappers thin.
- Keep compatibility for `auto-preflight`; Phase 36 may reuse or delegate to
  existing checks, but should not remove existing commands.
- Add focused tests around the new readiness model and command output before
  production code changes.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `saymo/commands/tests.py` contains `PreflightCheck`,
  `_collect_auto_preflight`, `_print_auto_preflight`, and
  `_prepare_responses`; these already check prepared standup audio, response
  cache coverage, voice metadata, provider tab, audio devices, hotkeys, and
  fallback status.
- `saymo/commands/core.py` contains `prepare`, `_prepare`, and
  `_call_ready_cached_audio`; `_call_ready_cached_audio` already validates
  prepared WAV metadata via `build_voice_cache_metadata(..., purpose="prepare")`.
- `saymo/analysis/response_cache.py` contains `ResponseCache`, library
  building, metadata-aware cache validation, cache build status, and stale
  checks.
- `saymo/analysis/cache_metadata.py` contains privacy-safe voice cache metadata
  builders/checkers.
- `saymo/analysis/remediation.py` contains `RemediationHint`,
  `render_remediation_hints`, and `hints_from_preflight_checks`; reuse the
  rendering style rather than inventing unrelated output.
- `saymo/obsidian/daily_notes.py` reads standup notes and warns when daily
  notes are missing. `scripts/ensure_obsidian_daily_note.py` currently creates
  missing daily notes and has tests in `tests/scripts/test_ensure_obsidian_daily_note.py`.

### Established Patterns

- CLI commands are Click commands registered through the existing command
  modules and use `ctx.obj["config"]`.
- Tests use `pytest` with `click.testing.CliRunner`, monkeypatching, and tmp
  configs under `tests/`.
- User-facing diagnostics use concise `ok:`, `block:`, `warn:`, and
  `remediation:` output.
- Voice/cache metadata sidecars must avoid raw text and use fingerprints.
- Local private runtime artifacts live under `~/.saymo/`; repo-committed tests
  should use temporary directories.

### Integration Points

- Add shared readiness contracts in a new or existing `saymo.analysis` module.
- Add a Click command wrapper for `call-ready`; keep business logic outside the
  CLI wrapper so future phases can reuse it from `auto`, rehearsal, scorecard,
  and safety-soak.
- Reuse existing `ResponseCache(...).status()` / cache validation paths for
  coverage rather than scanning response WAVs ad hoc.
- Use existing remediation hints where possible, then extend only for daily
  note/source-specific blockers if needed.

</code_context>

<specifics>
## Specific Ideas

- The immediate user-facing pain point is `auto-preflight -p standup` reporting
  a missing prepared standup WAV and Glip provider tab; Phase 36 should make
  the cache/source side actionable and Phase 37 will deepen provider handling.
- `saymo call-ready -p standup --provider glip --prepare` should be the target
  workflow for a pre-call repair/check pass.
- The report should avoid dumping private note text; show the note path, cache
  path, response-cache counts, voice profile/engine metadata, and rerun command.

</specifics>

<deferred>
## Deferred Ideas

- Deep Chrome/Glip tab capability, BlackHole route, permission, and takeover
  checks are Phase 37.
- Call-control daemon, heartbeat, LaunchAgent lifecycle, and menu-adjacent
  status are Phase 38.
- Fail-closed realtime behavior and cache-miss policy enforcement are Phase 39.
- Full launch/realtime scorecard and safety-soak evidence feedback is Phase 40.
- Native menu bar app packaging, calendar launch, automatic provider repair,
  and live LLM+TTS fallback are outside v1.9 Phase 36.

</deferred>

---

*Phase: 36-call-ready-preflight-and-cache-gate*
*Context gathered: 2026-07-08 via smart discuss auto defaults*

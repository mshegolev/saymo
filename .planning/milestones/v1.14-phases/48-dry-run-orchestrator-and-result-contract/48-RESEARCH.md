# Phase 48: Dry-Run Orchestrator And Result Contract - Research

**Researched:** 2026-07-10
**Domain:** Python Click CLI over existing Saymo launch-readiness contracts
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Phase 49 handles Obsidian daily-note creation/selection, prepared audio
  source hash checks, response-cache staleness, and cloned voice metadata.
- Phase 50 handles provider tab, BlackHole, audio routing, call-control daemon,
  and LaunchAgent health expansion.
- Phase 51 handles dry-run evidence integration with rehearsal, scorecards,
  safety-soak, and latest-vs-previous comparison.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DRY-01 | User can run one profile/provider dry-run command that verifies whether Saymo is ready for the next real standup without starting realtime mode. | Add `saymo dry-run` as a thin Click command in `saymo/commands/dry_run.py`; call `collect_launch_readiness(..., prepare=False)` directly. |
| DRY-02 | User can see one concise `ready` or `not ready` result with grouped blockers, warnings, exact actions, and rerun commands. | Reuse `render_launch_readiness()` and `render_grouped_launch_remediation()` with a parameterized top-level label. Preserve severity grouping and readiness-based exit codes. |
| DRY-03 | User can run the dry-run without synthesizing audio, playing audio, deleting cache artifacts, retraining, downloading voice models, or mutating protected `.saymo` assets automatically. | Do not import auto/realtime/TTS execution paths. Add monkeypatched CLI tests proving no `prepare=True`, no playback, no synthesis, no provider actions, no cache rotation/deletion, and no protected asset writes. |
</phase_requirements>

## Summary

Phase 48 should be implemented as a small operator-facing shell over the existing launch-readiness contract, not as a new readiness system. The repo already has the right domain model: `LaunchReadinessReport`, `LaunchReadinessCheck`, `collect_launch_readiness()`, grouped remediation rendering, sanitized JSON serialization, and artifact writing. The dry-run command should only select profile/provider, collect the report with `prepare=False`, render `dry-run: ready|not ready`, optionally emit sanitized JSON/artifact output, and exit `0` or `1` from `report.ready`.

The only needed contract changes are narrow and backward-compatible: parameterize launch-readiness rendering so the first line can say `dry-run`, and parameterize artifact metadata so `mode` can be `dry-run` while preserving `evidence_kind: launch-readiness`. Keep `saymo call-ready` defaults unchanged. Do not broaden this phase into Phase 49 source creation, Phase 50 provider/audio expansion, or Phase 51 evidence comparison.

**Primary recommendation:** Implement `saymo dry-run` in a new `saymo/commands/dry_run.py`, reuse `collect_launch_readiness(..., prepare=False)`, and add TDD tests that prove the command is a read-only wrapper around the existing readiness report.

## Standard Stack

### Core

| Library / Contract | Version | Purpose | Why Standard |
|--------------------|---------|---------|--------------|
| Python | 3.12.1 runtime, project requires `>=3.11` | CLI/runtime language | Existing package, dataclass contracts, and pytest suite are Python-first. |
| Click | 8.3.2 in `uv.lock`; `>=8.1.0` in `pyproject.toml` | CLI command/option registration | All Saymo commands use `@main.command`, `@click.option`, `@click.pass_context`, and `click.exceptions.Exit`. |
| Rich Console | 15.0.0 in `uv.lock`; `>=13.0.0` in `pyproject.toml` | Human terminal output | Existing command modules print through `saymo.commands.console`; `call-ready` uses `console.print(..., markup=False, soft_wrap=True)`. |
| `LaunchReadinessReport` / `LaunchReadinessCheck` | repo-local | Structured readiness result | Already computes `ready`, counts, sanitized `to_dict()`, and check details. Do not create a second model. |
| `collect_launch_readiness()` | repo-local | Readiness collection | Existing one source of truth for daily note, prepared audio, response cache, voice metadata, provider/audio, and call-control rows. |

### Supporting

| Library / Contract | Version | Purpose | When to Use |
|--------------------|---------|---------|-------------|
| pytest | 9.0.3 in runtime and `uv.lock`; `>=9.0.3` in `pyproject.toml` | Test framework | Add focused RED tests before implementation. |
| `click.testing.CliRunner` | from Click 8.3.2 | CLI contract tests | Existing `tests/test_call_ready_cli.py` pattern for config fixtures, exit codes, stdout, JSON, and artifacts. |
| `json`, `pathlib.Path`, `dataclasses.replace` | stdlib | JSON payloads, artifact paths, frozen check copying if needed | Use stdlib; no new dependency. |
| `write_launch_readiness_artifact()` | repo-local | Sanitized artifact writing | Parameterize for `mode="dry-run"` rather than creating a new writer. |
| `render_grouped_launch_remediation()` | repo-local | Existing blocker/warning/action/rerun grouping | Keep remediation output consistent with call-ready and realtime launch gates. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `saymo dry-run` | `saymo auto --dry-run` | Rejected: risks entering or importing realtime setup and violates the distinct-from-auto requirement. |
| New `DryRunReport` model | Existing `LaunchReadinessReport` | Rejected: duplicates readiness semantics, sanitization, and test surface. |
| Shell out to `saymo call-ready` | Direct function call | Rejected: subprocess complicates config object reuse, monkeypatch testing, exit behavior, and JSON/artifact control. |
| Add to `saymo/commands/tests.py` | New `saymo/commands/dry_run.py` | Rejected: `tests.py` is already very large and diagnostic-heavy; phase context explicitly prefers a small module. |
| Rewrite all checker action text to say dry-run | Preserve checker-owned remediation text in Phase 48 | Rejected for this phase: those strings are owned by launch-readiness source/provider/cache modules. Phase 48 should only set top-level dry-run label and artifact/JSON mode unless tests expose a strict contract gap. |

**Installation:** No new packages.

```bash
uv sync
```

**Version verification:** Verified locally on 2026-07-10.

```bash
uv run python -c "import click, pytest, sys; print(sys.version.split()[0], click.__version__, pytest.__version__)"
```

Observed runtime: Python 3.12.1, Click 8.3.2, pytest 9.0.3. `uv.lock` publish timestamps: Click 8.3.2 uploaded 2026-04-03, pytest 9.0.3 uploaded 2026-04-07, Rich 15.0.0 uploaded 2026-04-12, PyYAML 6.0.3 uploaded 2025-09-25.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
├── commands/
│   ├── call_ready.py       # keep existing behavior unchanged
│   ├── dry_run.py          # new thin dry-run command
│   └── __init__.py         # import dry_run for command registration
└── analysis/
    └── launch_readiness.py # parameterize render/artifact helpers only

tests/
├── test_dry_run_cli.py     # new CLI/result/non-destructive tests
├── test_call_ready_cli.py  # existing regression coverage
└── analysis/
    └── test_launch_readiness.py # render/artifact default + dry-run mode tests
```

### Pattern 1: Thin Click Command Over Shared Collector

**What:** Add a new command module with the same option shape as `call-ready`: `-p/--profile`, optional `--provider`, `--json`, optional `--output`. Do not include `--prepare`.

**When to use:** This is the Phase 48 command shell.

**Example:**

```python
# Source: saymo/commands/call_ready.py pattern
@main.command("dry-run")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option("--provider", default=None, help="Override provider from profile")
@click.option("--json", "json_output", is_flag=True, help="Print JSON output")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.pass_context
def dry_run(ctx, profile, provider, json_output, output):
    config = ctx.obj["config"]
    meeting = config.get_meeting(profile)
    resolved_provider = provider or (meeting.provider if meeting else "glip")
    report = collect_launch_readiness(
        config,
        profile=profile,
        provider_name=resolved_provider,
        prepare=False,
    )
    ...
```

### Pattern 2: Parameterize Existing Rendering

**What:** Change `render_launch_readiness(report)` to accept a keyword-only label with default `label="call-ready"`. This avoids string post-processing and preserves existing call-ready/realtime behavior.

**When to use:** Dry-run human output must start with `dry-run: ready` or `dry-run: not ready`.

**Example:**

```python
# Source: saymo/analysis/launch_readiness.py, backward-compatible extension
def render_launch_readiness(
    report: LaunchReadinessReport,
    *,
    label: str = "call-ready",
) -> str:
    lines = [f"{label}: {'ready' if report.ready else 'not ready'}"]
    ...
```

### Pattern 3: Parameterize Artifact Mode, Keep Evidence Kind

**What:** Change `write_launch_readiness_artifact(report, output_path)` to accept `mode="call-ready"` with the same default schema. Dry-run should call it with `mode="dry-run"`.

**When to use:** The user asks for `--output`. JSON stdout should stay parseable and should not be polluted by the human `artifact:` line.

**Example:**

```python
# Source: saymo/analysis/launch_readiness.py, backward-compatible extension
def write_launch_readiness_artifact(
    report: LaunchReadinessReport,
    output_path: Path,
    *,
    mode: str = "call-ready",
) -> Path:
    payload = report.to_dict()
    payload.update(
        {
            "schema_version": "1.0",
            "evidence_kind": "launch-readiness",
            "mode": mode,
            "artifact_path": _sanitize_text(str(output_path)),
            "created_at": _utc_now(),
        }
    )
    ...
```

### Pattern 4: Command-Local JSON Payload

**What:** Use `report.to_dict()` as the base JSON stdout payload. Add `mode: "dry-run"` at the command layer if the CLI contract wants explicit mode in stdout. Do not add artifact-only keys such as `artifact_path` or `created_at` to JSON stdout.

**When to use:** `saymo dry-run --json` and `saymo dry-run --json --output path`.

**Example:**

```python
payload = report.to_dict()
payload["mode"] = "dry-run"
click.echo(json.dumps(payload, ensure_ascii=False))
```

### Anti-Patterns to Avoid

- **Calling `saymo.commands.tests._collect_auto_preflight()`:** it is a separate legacy preflight contract. Use `collect_launch_readiness()` so dry-run, call-ready, and realtime gate share one readiness source.
- **Adding `--prepare` to dry-run:** source creation is Phase 49. Phase 48 must prove no automatic mutation.
- **Importing auto/realtime execution helpers:** dry-run must not touch `_run_auto_start()`, `_auto()`, `AudioCapture`, `LocalWhisper`, playback, or provider control actions.
- **String-rendering then replacing `call-ready` with `dry-run`:** parameterize the renderer/writer instead.
- **Wrapping artifacts in a new schema envelope:** existing launch evidence loaders expect flat launch-readiness artifacts. Use `mode="dry-run"` in the existing schema.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Readiness data model | New dry-run dataclasses | `LaunchReadinessReport` and `LaunchReadinessCheck` | Already provide ready semantics, counts, check details, and sanitized serialization. |
| Human remediation grouping | New blocker/warning renderer | `render_grouped_launch_remediation()` via `render_launch_readiness()` | Existing grouping already matches call-ready and realtime launch-block output. |
| Artifact sanitizer | New JSON sanitizer | `LaunchReadinessReport.to_dict()` and `write_launch_readiness_artifact()` | Existing sanitizer redacts known private sentinels, sensitive metadata names, tokens, and audio/text markers. |
| Provider/audio probes | New OS or Chrome checks | Existing `collect_provider_audio_checks()` under `collect_launch_readiness()` | Existing checks are read-only and already covered by provider/audio safety tests. |
| TTS/audio no-op mode | Fake synthesis/playback pipeline | No synthesis/playback imports at all | A dry-run should inspect readiness metadata, not exercise generation or output paths. |
| Cache cleanup/repair | Deletion or regeneration helpers | Action strings only | Protected caches and voice assets require explicit operator commands outside Phase 48. |

**Key insight:** Phase 48 is not about making readiness smarter. It is about giving the operator one safe, named dry-run entry point over the readiness contract Saymo already trusts.

## Common Pitfalls

### Pitfall 1: Accidentally Preparing Sources

**What goes wrong:** Dry-run calls `collect_launch_readiness(..., prepare=True)` or exposes `--prepare`, causing missing daily notes to be created.

**Why it happens:** `call-ready` supports `--prepare`; copy/paste can preserve the flag accidentally.

**How to avoid:** The dry-run command must hardcode `prepare=False` and should not declare a `--prepare` option.

**Warning signs:** A dry-run test creates an Obsidian note, modifies a temp vault, or accepts `saymo dry-run --prepare`.

### Pitfall 2: Reaching Realtime or Audio Paths

**What goes wrong:** Dry-run imports or calls `_run_auto_start()`, `_auto()`, `_play_cached_audio()`, `AudioCapture`, `LocalWhisper`, TTS selector/engine functions, or playback helpers.

**Why it happens:** Existing operator flows include `auto`, `realtime`, `rehearsal`, and `test-tts`; they are tempting shortcuts but outside this phase.

**How to avoid:** The command module should import only Click, JSON/Path, `collect_launch_readiness`, render/artifact helpers, `console`, and `main`.

**Warning signs:** Tests need to monkeypatch TTS synthesis, audio playback, provider mute actions, or realtime capture to keep dry-run safe.

### Pitfall 3: Breaking `saymo call-ready`

**What goes wrong:** Renderer/artifact helper changes alter existing first-line output, JSON stdout shape, artifact `mode: call-ready`, or exit behavior.

**Why it happens:** Shared helpers currently hardcode `call-ready`; changing defaults instead of adding keyword-only defaults will break existing tests.

**How to avoid:** Add defaults: `render_launch_readiness(report, label="call-ready")` and `write_launch_readiness_artifact(..., mode="call-ready")`.

**Warning signs:** Any existing `tests/test_call_ready_cli.py` or `tests/analysis/test_launch_readiness.py` assertion must be weakened to pass.

### Pitfall 4: Polluting JSON Stdout With Human Artifact Output

**What goes wrong:** `--json --output` prints JSON plus `artifact: path`, making stdout unparseable.

**Why it happens:** Human output and artifact notification paths are mixed.

**How to avoid:** Follow `call-ready`: emit `artifact:` only in human mode; JSON stdout should contain one JSON object only.

**Warning signs:** `json.loads(result.output)` fails in CLI tests when `--json --output` is used.

### Pitfall 5: Treating Artifact Writing as Permission to Store Private Content

**What goes wrong:** Artifact includes raw daily note body, prompt text, generated answer text, audio bytes, secrets, voice sample paths/content, or training data.

**Why it happens:** Later evidence phases may want richer artifacts; Phase 48 only establishes the shell/schema hook.

**How to avoid:** Base artifacts on `report.to_dict()` only. Do not capture stdout, note bodies, prompt text, response text, audio bytes, or command logs.

**Warning signs:** Artifact tests contain `PRIVATE_DAILY_NOTE`, `PRIVATE_TRANSCRIPT`, `PRIVATE_GENERATED_ANSWER`, `SECRET_TOKEN`, `raw_transcript`, `generated_answer`, `answer_text`, `daily_note_body`, or `audio_bytes`.

## Code Examples

Verified patterns from existing repo sources:

### Current Call-Ready Command Flow

```python
# Source: saymo/commands/call_ready.py
report = collect_launch_readiness(
    config,
    profile=profile,
    provider_name=resolved_provider,
    prepare=prepare,
)
artifact_path = write_launch_readiness_artifact(report, output) if output else None

if json_output:
    click.echo(json.dumps(report.to_dict(), ensure_ascii=False))
else:
    console.print(render_launch_readiness(report), markup=False, soft_wrap=True)
    if artifact_path:
        click.echo(f"artifact: {artifact_path}")

raise click.exceptions.Exit(0 if report.ready else 1)
```

### Launch-Readiness Ready Semantics

```python
# Source: saymo/analysis/launch_readiness.py
@property
def ready(self) -> bool:
    return all(check.ok or check.severity != "block" for check in self.checks)
```

### Read-Only Collector Call

```python
# Source: saymo/analysis/realtime_gate.py
report = collect_launch_readiness(
    config,
    profile=profile,
    provider_name=provider,
    prepare=False,
)
```

### Dry-Run Non-Destructive Test Shape

```python
# New test pattern: tests/test_dry_run_cli.py
def fake_collect(config, *, profile, provider_name, prepare):
    assert prepare is False
    return LaunchReadinessReport(profile=profile, provider=provider_name, checks=(ok_check,))

monkeypatch.setattr(dry_run_module, "collect_launch_readiness", fake_collect)
result = CliRunner().invoke(
    main,
    ["--config", str(config_path), "dry-run", "-p", "standup", "--provider", "glip"],
)
assert result.exit_code == 0
assert result.output.splitlines()[0] == "dry-run: ready"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `auto-preflight` with separate `PreflightCheck` rows | Shared `LaunchReadinessReport` used by `call-ready` and realtime launch gate | v1.9 / Phase 39 | Dry-run should use launch-readiness, not legacy preflight. |
| Starting realtime performed partial local checks inside `_auto()` | `evaluate_realtime_launch_gate()` calls `collect_launch_readiness(..., prepare=False)` before capture/STT/provider setup | v1.9 / Phase 39 | Phase 48 can safely reuse the same read-only launch-gate contract. |
| Call-ready artifact only identified `mode: call-ready` | Phase 48 should keep flat `launch-readiness` schema and set `mode: dry-run` for dry-run artifacts | Phase 48 | Future evidence tools can distinguish dry-run without a new schema envelope. |
| Cache/voice repair might appear automatic | Current milestone decisions keep cache repair, retraining, downloads, and cleanup explicit | v1.12-v1.14 | Dry-run must report commands, never repair automatically. |

**Deprecated/outdated:**
- `saymo auto-preflight` as the primary launch readiness source for this phase. It remains useful as a legacy diagnostic, but Phase 48 planning should build on `collect_launch_readiness()`.
- Dry-run via `saymo auto --dry-run`. This conflicts with the requirement to keep dry-run distinct from realtime mode.

## Open Questions

1. **Should nested rerun/action text say `dry-run` instead of `call-ready`?**
   - What we know: The top-level dry-run result and artifact mode must say dry-run. Existing checks generate many `saymo call-ready` rerun/action strings from source/cache/provider modules.
   - What's unclear: Whether Phase 48 acceptance will require every embedded rerun command to point at `saymo dry-run`.
   - Recommendation: For Phase 48, do not spread text changes across checker modules. Preserve checker-owned remediation text, and only parameterize top-level rendering plus artifact/JSON mode. If implementation tests require self-rerun commands, retarget only exact `check.rerun == "saymo call-ready -p <profile> --provider <provider>"` values in the dry-run command module; do not edit source/provider/cache modules.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none; dependencies and dev group are in `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DRY-01 | `saymo dry-run -p standup --provider glip` calls launch-readiness once with profile/provider and does not start realtime | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_calls_launch_readiness_without_prepare -q` | ❌ Wave 0 |
| DRY-01 | Command is registered through `saymo/commands/__init__.py` and supports `-p/--profile`, `--provider`, `--json`, `--output` | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_cli_options_and_registration -q` | ❌ Wave 0 |
| DRY-02 | Human output first line is exactly `dry-run: ready` or `dry-run: not ready`; exit code mirrors readiness | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_prints_top_level_result_and_exit_code -q` | ❌ Wave 0 |
| DRY-02 | Human output preserves grouped remediation sections and sanitized action/rerun lines | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_groups_remediation_with_rerun_commands -q` | ❌ Wave 0 |
| DRY-02 | JSON stdout is one sanitized object with `mode`, `profile`, `provider`, `ready`, counts, and checks | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_json_is_sanitized_machine_contract -q` | ❌ Wave 0 |
| DRY-02 | `--output` writes a sanitized flat artifact with `mode: dry-run` and does not pollute JSON stdout | CLI/unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_output_artifact_uses_dry_run_mode -q` | ❌ Wave 0 |
| DRY-03 | Dry-run always passes `prepare=False` and exposes no `--prepare` flag | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_has_no_prepare_path -q` | ❌ Wave 0 |
| DRY-03 | Dry-run does not call synthesis, playback, cache rotation/deletion, provider mutation, realtime capture, STT, retraining, or model downloads | CLI unit with monkeypatch guards | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_path_is_non_destructive -q` | ❌ Wave 0 |
| DRY-02/03 | Shared render/artifact helpers preserve call-ready defaults while allowing dry-run label/mode | unit | `uv run pytest tests/analysis/test_launch_readiness.py::test_render_and_artifact_support_dry_run_mode_without_breaking_call_ready -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py -q`
- **Per wave merge:** `uv run pytest tests/test_call_ready_cli.py tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_gate.py -q`
- **Phase gate:** `uv run pytest` before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_dry_run_cli.py` - covers DRY-01, DRY-02, DRY-03 command/result/non-destructive behavior.
- [ ] `tests/analysis/test_launch_readiness.py` additions - covers parameterized render label and artifact mode while preserving call-ready defaults.
- [ ] Optional static guard in `tests/test_realtime_static_guards.py` or `tests/test_dry_run_cli.py` - asserts `saymo/commands/dry_run.py` does not reference `_auto`, `_run_auto_start`, `_play_cached_audio`, `_rotate_audio_cache`, `_prepare`, `AudioCapture`, `LocalWhisper`, or TTS factory/selector imports.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/48-dry-run-orchestrator-and-result-contract/48-CONTEXT.md` - locked decisions, scope, non-destructive boundary, artifact boundary.
- `.planning/REQUIREMENTS.md` - DRY-01, DRY-02, DRY-03 and out-of-scope requirements.
- `.planning/ROADMAP.md` - Phase 48 goal and success criteria.
- `.planning/STATE.md` and `.planning/PROJECT.md` - milestone decisions around read-only cache repair, protected voice assets, and v1.14 dry-run focus.
- `CLAUDE.md` and `AGENTS.md` - project architecture, local-by-default, no personal data, testing conventions.
- `saymo/commands/call_ready.py` - existing Click command, JSON/artifact/exit-code pattern.
- `saymo/analysis/launch_readiness.py` - report/check contracts, rendering, artifact writer, sanitizer, collector.
- `saymo/analysis/realtime_gate.py` - read-only launch gate already using `prepare=False`.
- `saymo/analysis/provider_audio_readiness.py` - read-only provider/audio checks and guardrails.
- `saymo/analysis/launch_evidence.py` - flat launch-readiness artifact loader and privacy sanitizer.
- `tests/test_call_ready_cli.py` and `tests/analysis/test_launch_readiness.py` - existing test patterns and privacy/non-destructive assertions.
- `.claude/agents/audio-safety-reviewer.md` - provider/audio guardrails if those modules are touched.
- `.claude/skills/test-tts/SKILL.md` - read only for project awareness; not invoked because Phase 48 must not synthesize or play audio.

### Secondary (MEDIUM confidence)

- `pyproject.toml` and `uv.lock` - dependency constraints, resolved versions, upload timestamps.
- Local runtime check: Python 3.12.1, Click 8.3.2, pytest 9.0.3.

### Tertiary (LOW confidence)

- None. No web search was needed because Phase 48 is repo-contract research, not an ecosystem selection problem.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing package metadata, lockfile, and runtime imports verified.
- Architecture: HIGH - command registration, launch-readiness contracts, renderer, writer, and tests are all present locally.
- Pitfalls: HIGH - current tests already cover call-ready privacy, non-destructive provider/audio checks, and JSON/artifact behavior.
- Open question on embedded rerun text: MEDIUM - the contract clearly requires dry-run top-level output and artifact mode, but does not explicitly require every checker-owned action string to be retargeted.

**Research date:** 2026-07-10
**Valid until:** 2026-08-09, or earlier if Phase 49 changes launch-readiness check ownership.

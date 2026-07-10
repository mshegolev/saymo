# Phase 51: Dry-Run Evidence And Rehearsal Feedback - Research

**Researched:** 2026-07-10
**Domain:** Python Click CLI, sanitized JSON evidence, launch-readiness comparison, rehearsal/scorecard/safety-soak gates
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Live Answer Policy, answer confidence gates, and manual approval modes belong
  to v1.15.
- Calendar-triggered unattended launch and automatic provider repair remain out
  of scope.
- Rich historical dashboards over many dry-run artifacts can come later; this
  phase only needs latest-vs-previous comparison.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVID-01 | User can save a sanitized dry-run artifact with profile, provider, check statuses, stale reasons, actions, rerun commands, and timestamps without raw meeting text, prompt text, response text, audio bytes, secrets, voice samples, or training data. | Existing `saymo dry-run --output` already calls `write_launch_readiness_artifact(..., mode="dry-run")`; Phase 51 should add explicit dry-run artifact completeness/privacy tests and avoid new serialization. |
| EVID-02 | User can feed dry-run evidence into rehearsal, session scorecard, and safety-soak so the next real call has a repeatable launch-readiness signal. | Scorecard and safety-soak already accept `--launch-json`; add dry-run-mode coverage and let rehearsal record/read a launch evidence path via the shared loader. |
| EVID-03 | User can compare the latest dry-run result with the previous result to see whether readiness improved or regressed before joining a call. | Add normalized compare dataclasses/functions in `launch_evidence.py` and a read-only flat Click command in `dry_run.py`. Compare only stable aggregate fields, not raw checks. |
</phase_requirements>

## Summary

Phase 51 should be a narrow evidence/reporting phase, not a new dry-run execution phase. The repo already has the right primitives: `LaunchReadinessReport` and `LaunchReadinessCheck` sanitize output, `write_launch_readiness_artifact()` writes flat JSON with `schema_version`, `evidence_kind`, `mode`, `artifact_path`, and `created_at`, and `load_launch_evidence()` normalizes saved artifacts into aggregates used by session scorecards and safety soak.

The main missing pieces are focused tests and a small comparison surface. `session-scorecard --launch-json` and `safety-soak --launch-json` already load launch-readiness evidence, and they do not currently reject `mode: dry-run`. Rehearsal can be connected by recording a dry-run evidence path and optionally loading a summarized launch check into the rehearsal artifact. Latest-vs-previous comparison belongs in `saymo.analysis.launch_evidence` and should be exposed as a flat `saymo dry-run-compare --current <path> --previous <path>` command to avoid converting the existing `saymo dry-run` command into a Click group.

**Primary recommendation:** Reuse the launch-readiness artifact and loader; add `LaunchEvidenceComparison` in `launch_evidence.py`, a flat read-only `dry-run-compare` CLI, and minimal rehearsal/scorecard/soak wiring tests with private sentinels.

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| Python stdlib `dataclasses`, `json`, `pathlib` | Python >=3.11 | Frozen evidence models, JSON encode/decode, path handling | Existing repo pattern for artifacts; no new dependency required. |
| `click` | 8.3.2 (uv.lock, uploaded 2026-04-03) | CLI options and command registration | Existing CLI framework; Click documents `CliRunner` for invoking commands in tests. |
| `pytest` | 9.0.3 (uv.lock, uploaded 2026-04-07) | Unit and CLI tests | Existing test framework; pytest `tmp_path` gives per-test temp artifacts. |
| `rich` | 15.0.0 (uv.lock, uploaded 2026-04-12) | Console rendering via existing `console.print` | Existing human output path; compare output can stay plain text through the same console. |
| `saymo.analysis.launch_readiness` | repo-local | Source artifact schema and serializer | Locked user decision requires this model; current dry-run writes with `mode="dry-run"`. |
| `saymo.analysis.launch_evidence` | repo-local | Read-only artifact loading, summarization, and comparison | Existing loader is the correct integration point; add comparison here. |

### Supporting

| Library / Module | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| `saymo.analysis.rehearsal` | repo-local | Sanitized rehearsal artifacts | Add a launch evidence path/status field and keep transcript blanking behavior. |
| `saymo.analysis.session_scorecard` | repo-local | Fold launch evidence into scorecards | Extend tests to prove dry-run artifacts are accepted and remain sanitized. |
| `saymo.analysis.safety_soak` | repo-local | Gate sanitized scorecards | Extend tests to prove dry-run launch metrics contribute to soak totals/violations. |
| `saymo.analysis.remediation` | repo-local | Rerun/action hint rendering | Reuse existing sanitized rerun command rendering; do not add ad hoc command strings in compare. |
| `pyyaml` | 6.0.3 (uv.lock, uploaded 2025-09-25) | Config loading in CLI tests | Use existing config fixtures only; no new YAML behavior needed. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing launch-readiness artifact | New dry-run evidence schema | Rejected by locked decision; would duplicate sanitization and break scorecard/soak reuse. |
| Flat `saymo dry-run-compare` command | Convert `saymo dry-run` into a command group with `compare` subcommand | Flat command is less invasive because `saymo dry-run` is already a normal command and many repo commands are flat `@main.command(...)` entries. |
| Shared `load_launch_evidence()` | One-off parser in rehearsal, scorecard, and soak | Rejected by locked decision; one-off parsers create privacy drift and inconsistent invalid-file handling. |
| Compare raw `checks` payloads | Compare normalized aggregates | Raw checks can contain implementation churn and path hints; normalized fields are stable and already sanitized. |

**Installation:** No new dependencies.

```bash
uv sync
```

**Version verification:** Versions were verified from `uv.lock` and the active environment:

```bash
uv run python -c "import importlib.metadata as m; print(m.version('click'), m.version('pytest'), m.version('rich'), m.version('pyyaml'))"
```

Observed: `click==8.3.2`, `pytest==9.0.3`, `rich==15.0.0`, `pyyaml==6.0.3`.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
  commands/
    dry_run.py              # keep dry-run artifact writing; add flat dry-run-compare command
    tests.py                # add rehearsal --launch-json wiring only if matching existing diagnostic CLI pattern
  analysis/
    launch_readiness.py     # source of artifact schema; avoid adding compare here
    launch_evidence.py      # add normalized comparison dataclasses/functions/rendering
    rehearsal.py            # add optional launch evidence reference fields with safe defaults
    session_scorecard.py    # reuse launch_json path; optionally fall back to rehearsal artifact path
    safety_soak.py          # no parser changes; consume scorecards only
tests/
  analysis/
    test_launch_evidence.py # add focused compare/redaction tests (new file)
  test_dry_run_cli.py       # dry-run artifact and compare CLI tests
  test_rehearsal_cli.py     # launch evidence path recorded/loaded
  test_session_scorecard_cli.py
  test_safety_soak_cli.py
```

### Pattern 1: Existing Artifact Schema Is The Source Of Truth

**What:** Keep all dry-run evidence on the existing `LaunchReadinessReport` -> `write_launch_readiness_artifact()` path.

**When to use:** Every time a dry-run result is saved or loaded for downstream gates.

**Evidence:** `saymo dry-run --output` already calls `write_launch_readiness_artifact(report, output, mode="dry-run")` and JSON stdout only adds `mode` without artifact metadata.

**Example:**

```python
# Source: saymo/commands/dry_run.py
report = collect_launch_readiness(..., mode="dry-run")
write_launch_readiness_artifact(report, output, mode="dry-run")
```

### Pattern 2: Normalize Before Comparing Or Gating

**What:** Load saved artifacts through `load_launch_evidence()` and compare `LaunchEvidence` fields.

**When to use:** Scorecard, safety soak, rehearsal launch-evidence checks, and dry-run comparison.

**Example:**

```python
# Source: saymo.analysis.launch_evidence
current = load_launch_evidence(current_path)
previous = load_launch_evidence(previous_path)
comparison = compare_launch_evidence(current, previous)
```

### Pattern 3: Flat Read-Only Compare CLI

**What:** Add `@main.command("dry-run-compare")` in `saymo/commands/dry_run.py` with required `--current` and `--previous`. Default output should be human-readable; `--json` can print sanitized machine JSON to stdout.

**When to use:** EVID-03 latest-vs-previous comparison before a real call.

**Why:** It matches existing flat Click command style and avoids breaking `saymo dry-run` by turning it into a group.

**Example:**

```bash
saymo dry-run-compare --current ~/.saymo/evidence/latest.json --previous ~/.saymo/evidence/previous.json
saymo dry-run-compare --current latest.json --previous previous.json --json
```

### Pattern 4: Rehearsal References Evidence, Scorecard/Soak Gate It

**What:** Let `saymo rehearsal --launch-json <dry-run.json>` record a sanitized launch evidence path/status in the rehearsal artifact. Then `build_scorecard_from_rehearsal()` can use explicit `launch_json` or the path recorded in the rehearsal artifact.

**When to use:** EVID-02 correlation between a rehearsal result and the launch-readiness state used before the call.

**Recommended behavior:**
- If launch evidence loads and `ready=True`: add/pass a non-private `launch readiness` rehearsal check.
- If launch evidence loads and `ready=False`: add/fail a blocking `launch readiness` rehearsal check with counts and failed labels only.
- If launch evidence is missing/invalid: add a warning and continue; do not crash or repair.
- Do not embed full launch evidence in rehearsal JSON; store path plus status/count summary only.

### Anti-Patterns to Avoid

- **New dry-run artifact schema:** Violates locked decisions and duplicates redaction.
- **Raw `checks` diff in CLI output:** Check details can change and can carry path hints; compare summarized fields.
- **Implicit latest-file discovery:** Inferring newest artifacts from directories risks private path assumptions and surprising IO; require explicit `--current` and `--previous`.
- **Rerunning dry-run during compare:** EVID-03 is a read-only saved-artifact comparison.
- **Crashing downstream gates on missing evidence:** Context requires clear warnings, not attempted repair.
- **Embedding raw launch JSON in rehearsal artifacts:** Store only the path/status summary; scorecards can reload via `load_launch_evidence()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Evidence serialization | New JSON writer for dry-run | `write_launch_readiness_artifact()` | Already adds schema/version/mode/timestamp and sanitizes via `to_dict()`. |
| Evidence parsing | Per-command JSON traversal | `load_launch_evidence()` / `summarize_launch_evidence()` | Already handles legacy reports, skips bad check rows, dedupes paths/reruns, and redacts sensitive names/values. |
| Privacy redaction | New regex set in each command | Existing `_sanitize_*` helpers in launch readiness/evidence plus tests | Multiple redactors drift; existing tests already pin private sentinel removal. |
| Scorecard launch metrics | New scorecard fields from raw artifact | `_launch_metrics_from_evidence()` | Already maps cache, provider, daemon, log paths, failed labels, and rerun commands. |
| Safety soak launch gate | New soak parser over dry-run JSON | Existing scorecard -> safety soak path | Soak already gates launch readiness through scorecard metrics and violations. |
| CLI testing harness | Manual subprocess CLI tests | `click.testing.CliRunner` with pytest `tmp_path` | Existing tests use this; official Click docs recommend `CliRunner` for command invocation tests. |

**Key insight:** The hard part is not JSON I/O; it is preserving the privacy boundary across artifact, rehearsal, scorecard, soak, and comparison. The safest implementation is to route every saved launch artifact through the one existing normalization layer.

## Common Pitfalls

### Pitfall 1: Treating `mode: dry-run` As A New Evidence Type

**What goes wrong:** Code branches on mode and adds a parallel parser or schema.
**Why it happens:** Dry-run feels distinct from call-ready, but Phase 48 intentionally reused the launch-readiness contract.
**How to avoid:** Keep `evidence_kind: launch-readiness`; mode is metadata only.
**Warning signs:** New dataclass names like `DryRunEvidenceArtifact` containing duplicate `profile/provider/checks` fields.

### Pitfall 2: Leaking Private Content Through Comparison

**What goes wrong:** A compare output includes raw check details, note paths, voice sample paths, prompt text, response text, or secret-like values.
**Why it happens:** Directly diffing `checks` or metadata is tempting.
**How to avoid:** Compare only `ready`, counts, failed labels, blocker categories, cache counts, provider/daemon booleans, and rerun command sets after `load_launch_evidence()`.
**Warning signs:** Compare tests assert against raw `detail` strings or metadata keys ending in private asset paths.

### Pitfall 3: Rehearsal Stores Too Much Evidence

**What goes wrong:** Rehearsal JSON embeds a full launch artifact, making it harder to prove transcript/prompt/response/audio exclusion.
**Why it happens:** It seems convenient to carry one big evidence blob.
**How to avoid:** Store a sanitized path and a compact status/count summary; let scorecard reload the artifact if needed.
**Warning signs:** Rehearsal artifact contains `checks`, `metadata`, or launch log paths copied from launch JSON.

### Pitfall 4: Invalid Evidence Becomes A Crash Or Auto-Repair

**What goes wrong:** Missing/invalid JSON raises a traceback or triggers a dry-run rerun.
**Why it happens:** `load_launch_evidence()` raises on invalid JSON, and commands may not catch it.
**How to avoid:** CLI compare catches `OSError`, `json.JSONDecodeError`, and `ValueError`, then raises a clear `ClickException` for compare. Rehearsal/scorecard/soak should warn and continue where existing behavior does.
**Warning signs:** Compare imports `collect_launch_readiness()` or any provider/audio/TTS module.

### Pitfall 5: Mode-Specific Tests Miss Call-Ready Compatibility

**What goes wrong:** Dry-run acceptance breaks existing call-ready or legacy artifact loading.
**Why it happens:** Tests focus only on new dry-run mode.
**How to avoid:** Include both `mode: dry-run` and `mode: call-ready` fixture artifacts for loader/compare tests.
**Warning signs:** `load_launch_evidence()` starts rejecting legacy artifacts without `mode`.

### Pitfall 6: Hidden Writes Outside Explicit Output

**What goes wrong:** Comparison or evidence loading writes normalized files, deletes old artifacts, or mutates `.saymo`.
**Why it happens:** "Latest-vs-previous" can invite history management.
**How to avoid:** Require explicit input paths; no directory scan, no cleanup, no auto-save.
**Warning signs:** `unlink`, `rmtree`, cache rebuild, provider mutation, launchd lifecycle, or TTS imports in `dry_run.py` or `launch_evidence.py`.

## Code Examples

Verified patterns from local source and official docs.

### Artifact Writer Contract

```python
# Source: saymo/analysis/launch_readiness.py
payload = report.to_dict()
payload.update({
    "schema_version": "1.0",
    "evidence_kind": "launch-readiness",
    "mode": _sanitize_text(mode),
    "created_at": _utc_now(),
})
```

### Launch Evidence Summary Fields

```python
# Source: saymo/analysis/launch_evidence.py
LaunchEvidence(
    mode=_sanitize_text(data.get("mode") or "call-ready"),
    ready=_ready_from_data(data, checks),
    failed_labels=_failed_labels(checks),
    blocker_categories=_blocker_categories(checks),
    cache_counts=_cache_counts(checks),
)
```

### Recommended Compare Model

```python
# New in saymo/analysis/launch_evidence.py
@dataclass(frozen=True)
class LaunchEvidenceComparison:
    current_path: str
    previous_path: str
    status: str  # improved | regressed | unchanged | mixed
    ready_change: str
    block_delta: int
    warn_delta: int
    resolved_failures: tuple[str, ...] = ()
    new_failures: tuple[str, ...] = ()
    blocker_category_deltas: dict[str, int] = field(default_factory=dict)
    cache_deltas: dict[str, int] = field(default_factory=dict)
    provider_change: str = "unchanged"
    daemon_change: str = "unchanged"
    rerun_commands_added: tuple[str, ...] = ()
    rerun_commands_removed: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
```

### Recommended Compare CLI

```python
# New in saymo/commands/dry_run.py
@main.command("dry-run-compare")
@click.option("--current", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--previous", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "json_output", is_flag=True)
def dry_run_compare(current, previous, json_output):
    comparison = compare_launch_evidence_paths(current=current, previous=previous)
    if json_output:
        click.echo(json.dumps(launch_evidence_comparison_to_json(comparison), ensure_ascii=False))
    else:
        console.print(render_launch_evidence_comparison(comparison), markup=False, soft_wrap=True)
```

### CLI Test Pattern

```python
# Source: Click official testing docs and existing tests
result = CliRunner().invoke(
    main,
    ["dry-run-compare", "--current", str(current), "--previous", str(previous)],
)
assert result.exit_code == 0
assert "improved" in result.output
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dry-run was only a human terminal check | Dry-run can write `mode: dry-run` launch-readiness artifacts | Phase 48, 2026-07-10 | Phase 51 should test and reuse the artifact, not rebuild it. |
| Source/cache/voice readiness lived in separate diagnostics | Dry-run rows include source, prepared audio, response cache, and cloned-voice metadata/actions | Phase 49, 2026-07-10 | Artifact completeness tests must include stale/source/cache/voice fields. |
| Provider/audio/control state required separate manual checks | Dry-run rows include provider/audio/call-control health and rerun actions | Phase 50, 2026-07-10 | Comparison can include provider readiness and daemon readiness. |
| Scorecard/soak lacked launch metrics | Scorecard loads `--launch-json`; soak gates launch not-ready/cache/provider/daemon violations through scorecards | Existing Phase 40-era code | EVID-02 is mostly wiring/tests, not new soak architecture. |
| No saved-artifact delta view | Add read-only latest-vs-previous compare over `LaunchEvidence` | Phase 51 target | Operator sees improvements/regressions before joining a call. |

**Deprecated/outdated:**
- Creating a separate dry-run evidence schema: explicitly out of bounds.
- Re-running checks to compare artifacts: violates read-only comparison requirement.
- Manual JSON inspection by the operator: insufficient for EVID-03.

## Open Questions

1. **Should compare write a comparison artifact?**
   - What we know: The requirement needs operator-readable and machine-readable comparison, not persistent comparison history.
   - What's unclear: Whether a saved comparison file is useful immediately.
   - Recommendation: Start with human stdout plus `--json` machine stdout. Add `--json-output` later only if planning wants a saved comparison report.

2. **Should rehearsal fail when linked dry-run evidence is not ready?**
   - What we know: Rehearsal should correlate with launch-readiness; scorecard/soak are the stronger gates.
   - What's unclear: Whether a not-ready launch artifact should make the rehearsal artifact status `fail`.
   - Recommendation: Add a blocking `launch readiness` rehearsal check for loaded `ready=False`, because that gives the operator one repeatable pre-call signal while preserving read-only behavior.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` for dependency declaration; no `[tool.pytest.ini_options]` detected |
| Quick run command | `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q` |
| Existing focused evidence command | `uv run pytest tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/test_realtime_static_guards.py -q` |
| Full suite command | `uv run pytest -q` |

Focused baseline run during research: `65 passed in 1.52s`.

### Phase Requirements To Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| EVID-01 | `saymo dry-run --output` writes a complete sanitized dry-run artifact with mode, timestamps, counts, check statuses, stale details, actions, reruns, and no private sentinels. | CLI/unit | `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_evidence.py -q` | Partial: `tests/test_dry_run_cli.py` Yes; `tests/analysis/test_launch_evidence.py` No, Wave 0 |
| EVID-02 | Rehearsal can reference dry-run evidence; scorecard and safety-soak accept `mode: dry-run` launch artifacts and keep JSON/Markdown sanitized. | CLI/integration unit | `uv run pytest tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py -q` | Yes, extend existing files |
| EVID-03 | Compare current vs previous launch/dry-run artifacts for readiness, count deltas, failures, categories, cache, provider, daemon, and rerun changes. | unit + CLI | `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py -q` | `tests/analysis/test_launch_evidence.py` No, Wave 0; `tests/test_dry_run_cli.py` Yes |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/analysis/test_launch_evidence.py tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q`
- **Per wave merge:** `uv run pytest tests/test_dry_run_cli.py tests/test_rehearsal_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py tests/analysis/test_launch_evidence.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/test_realtime_static_guards.py -q`
- **Phase gate:** `uv run pytest -q`, plus static guard that `saymo/commands/dry_run.py` and `saymo/analysis/launch_evidence.py` do not reference TTS/audio/provider/launchd/cache mutation APIs.

### Wave 0 Gaps

- [ ] `tests/analysis/test_launch_evidence.py` - dedicated launch evidence compare, dry-run-mode load, invalid/missing handling, and redaction tests for EVID-01/EVID-03.
- [ ] Extend `tests/test_rehearsal_cli.py` - `--launch-json` path is recorded/loaded without transcript/private leakage for EVID-02.
- [ ] Extend `tests/test_session_scorecard_cli.py` - `mode: dry-run` launch artifact accepted and rerun commands preserved for EVID-02.
- [ ] Extend `tests/test_safety_soak_cli.py` - dry-run launch evidence drives launch-not-ready/provider/daemon/cache violations through scorecard JSON for EVID-02.
- [ ] Extend `tests/test_dry_run_cli.py` - `dry-run-compare` human/JSON output and non-destructive static guard for EVID-03.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/51-dry-run-evidence-and-rehearsal-feedback/51-CONTEXT.md` - locked decisions, discretion, deferred scope.
- `.planning/REQUIREMENTS.md` - EVID-01, EVID-02, EVID-03 and out-of-scope boundaries.
- `saymo/commands/dry_run.py` - current dry-run CLI, JSON stdout, artifact writer call.
- `saymo/analysis/launch_readiness.py` - `LaunchReadinessReport`, `LaunchReadinessCheck`, artifact schema, sanitizers.
- `saymo/analysis/launch_evidence.py` - existing normalized loader/summarizer and redaction.
- `saymo/analysis/rehearsal.py` - sanitized rehearsal artifacts.
- `saymo/analysis/session_scorecard.py` - launch evidence loading into scorecard metrics.
- `saymo/analysis/safety_soak.py` - scorecard aggregation, launch/cache/provider/daemon violations.
- `saymo/commands/tests.py` - rehearsal/session-scorecard/safety-soak CLI wiring.
- `tests/test_dry_run_cli.py`, `tests/test_rehearsal_cli.py`, `tests/test_session_scorecard_cli.py`, `tests/test_safety_soak_cli.py`, `tests/analysis/test_launch_readiness.py`, `tests/analysis/test_session_scorecard.py`, `tests/analysis/test_safety_soak.py`, `tests/test_realtime_static_guards.py` - current behavioral and privacy tests.
- `pyproject.toml`, `uv.lock` - dependency declarations and locked versions.

### Official Docs (HIGH confidence)

- https://click.palletsprojects.com/en/stable/testing/ - `CliRunner` testing pattern; note current docs are 8.4.x while repo lock is Click 8.3.2, so do not use 8.4-only `capture` features.
- https://docs.pytest.org/en/stable/how-to/tmp_path.html - pytest `tmp_path` fixture for per-test temp artifacts.
- https://docs.python.org/3/library/dataclasses.html - frozen dataclass behavior.
- https://docs.python.org/3/library/json.html - JSON encoding behavior, `ensure_ascii`, `sort_keys`, `indent`.

### Secondary (MEDIUM confidence)

- Prior memory check found older Saymo v1.13/cache-cleanup notes only; no Phase 51-specific implementation facts. Used only to confirm no relevant prior phase-51 context was missed.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from `pyproject.toml`, `uv.lock`, active environment, and official docs.
- Architecture: HIGH - based on current code paths and locked Phase 51 decisions.
- Pitfalls: HIGH - derived from existing privacy/static guards and prior Phase 48-50 verification reports.
- Comparison output details: MEDIUM - exact CLI flag set is discretionary; recommendation is intentionally minimal.

**Research date:** 2026-07-10
**Valid until:** 2026-08-09 for architecture; re-check package docs/versions if dependency lock changes.

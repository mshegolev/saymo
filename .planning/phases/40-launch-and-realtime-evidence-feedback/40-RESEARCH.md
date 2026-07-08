# Phase 40: Launch and Realtime Evidence Feedback - Research

**Researched:** 2026-07-08
**Domain:** Local sanitized evidence artifacts, scorecards, safety-soak gates, and remediation output
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Approved Design Direction

Phase 40 should consume the contracts created in Phases 36-39 rather than
adding new realtime behavior:

- `LaunchReadinessReport.to_dict()` remains the source of truth for launch
  checks, blocker counts, cache/voice/provider/daemon metadata, and rerun
  commands.
- `RealtimeDecisionEvent` JSONL remains the source of truth for realtime
  spoke/skipped/blocked decision evidence.
- `SessionScorecard` should summarize launch health, daemon/control state,
  cache hit/miss and fallback-block counts, provider drift, handbrake blocks,
  and unsafe playback from sanitized launch/realtime evidence.
- `SafetySoakReport` should fail when v1.9 launch or realtime evidence proves
  unsafe conditions such as stale cache, missing daemon readiness, provider
  blockers, unsafe fallback, or automatic playback that bypassed safety gates.
- Troubleshooting output should connect the user to sanitized artifact paths,
  failed labels, remediation categories, and exact rerun commands.

Phase 40 must not weaken the Phase 39 fail-closed runtime loop. Evidence is a
feedback layer over already-sanitized artifacts.

#### Guardrails

- Do not store or render raw transcripts, generated answers, daily-note body,
  audio bytes, or secrets in launch, realtime, scorecard, soak, or
  troubleshooting evidence.
- Do not add Chrome, provider, microphone, audio-route, playback, recording, or
  launchd mutations to evidence readers or renderers.
- Do not make scorecards or safety-soak depend on a live provider/browser.
- Do not make Phase 40 bypass or relax Phase 39 fail-closed behavior.
- Preserve existing CLI behavior when new evidence paths are not supplied.
- Keep artifacts local-by-default and deterministic under test.

### Claude's Discretion

#### Grey Areas Resolved By Assumption

##### Evidence Shape

- Launch evidence may be a richer schema or wrapper around
  `LaunchReadinessReport.to_dict()`, but it must not duplicate readiness logic.
- Realtime evidence may be read from `realtime-decisions.jsonl` and summarized
  by label/outcome/source, not by raw transcript or generated text.
- Artifact paths are useful and allowed when sanitized local filesystem paths
  help the operator troubleshoot.

##### Scorecard Scope

- Existing scorecard APIs should grow typed v1.9 launch/realtime metrics rather
  than introducing a parallel report family.
- Scorecards may accept optional launch and realtime evidence paths/roots.
- Rehearsal and existing regression scorecards should stay backward compatible
  when no v1.9 evidence is provided.

##### Safety-Soak Scope

- Safety soak should continue accepting scorecards and baselines.
- New v1.9 violations should be derived from sanitized scorecard metrics, not
  by rereading raw meeting content.
- A failed gate should explain which sanitized condition failed and which source
  artifact to inspect.

##### Troubleshooting Scope

- Troubleshooting can be a renderer/helper or CLI output extension, but it
  should remain local and deterministic.
- It should favor existing remediation hints from launch readiness and
  scorecards over new prose-only heuristics.

#### Suggested Module Boundaries

- `saymo.analysis.launch_readiness` or a focused `launch_evidence` helper:
  normalized launch artifact schema and loader over existing readiness reports.
- `saymo.analysis.realtime_events`:
  event loader and summary helpers over existing JSONL.
- `saymo.analysis.session_scorecard`:
  v1.9 launch/realtime metrics, JSON/Markdown fields, and optional evidence
  ingestion.
- `saymo.analysis.safety_soak`:
  v1.9 safety violations derived from scorecard metrics.
- `saymo.analysis.remediation`:
  troubleshooting hints from launch/realtime/scorecard evidence.
- `saymo.commands.core`:
  minimal CLI option wiring and output rendering.

### Deferred Ideas (OUT OF SCOPE)

- A native visual dashboard over launch/realtime evidence.
- Automatic provider repair or route mutation based on evidence.
- Cloud sync or sharing of artifacts.
- Raw transcript-based post-call analytics.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVID-01 | User can inspect a sanitized launch-readiness artifact that records checks, blocker categories, cache counts, voice/cache fingerprints, provider status, daemon status, mode, and rerun commands without raw meeting content. | Use `LaunchReadinessReport.to_dict()` as the check/count source; add only a backward-compatible artifact envelope/optional fields for schema version, mode, source path, and artifact paths. |
| EVID-02 | User can inspect sanitized realtime events for launch start/end, cache hits/misses, fallback blocks, provider failures, playback attempts, handbrake actions, and stop reasons. | Extend `saymo.analysis.realtime_events` with JSONL loading and summary dataclasses over allowlisted `RealtimeDecisionEvent` rows; summarize by outcome/label/source and skip malformed rows. |
| EVID-03 | User can see launch health, daemon/control availability, cache hit/miss counts, unsafe fallback blocks, and provider drift in rehearsal or session scorecards. | Add optional typed v1.9 launch/realtime metrics to `SessionScorecard` with defaults so existing rehearsal/regression scorecards remain compatible. |
| EVID-04 | User can run safety-soak against v1.9 launch and realtime evidence, and the gate fails on unsafe playback, stale cache, missing daemon readiness, provider blockers, or unapproved fallback conditions. | Derive new safety violations from scorecard v1.9 metrics, preserving `SafetySoakReport` as the aggregate gate and keeping baseline drift behavior intact. |
| EVID-05 | User can troubleshoot launch and realtime failures from sanitized evidence that includes log/artifact paths and next rerun commands. | Extend remediation hints and CLI rendering to surface launch failed labels, categories, artifact/log paths, and exact rerun commands without new runtime probes. |
</phase_requirements>

## Summary

Phase 40 should be an evidence-consumption layer, not a runtime behavior phase. The current code already has two authoritative evidence sources: launch-readiness reports from `LaunchReadinessReport.to_dict()` and realtime decision rows from `RealtimeDecisionEvent.to_dict()`. The safest plan is to add loaders, summaries, scorecard metrics, safety-soak rules, and troubleshooting renderers around those contracts while keeping `saymo auto` and provider/audio behavior unchanged.

The existing schemas are already privacy-oriented: launch checks sanitize labels/details/actions/reruns/metadata, and realtime events use a strict allowlist. Phase 40 should preserve that style by adding typed metrics with default values, JSONL malformed-row tolerance, static privacy guards, and static provider/audio mutation guards.

**Primary recommendation:** Use the existing local dataclass contracts, add optional evidence inputs to scorecard generation, derive safety-soak violations from scorecard metrics, and keep all new CLI options opt-in.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.11 | Dataclasses, pathlib, json/jsonl parsing, CLI modules | Project runtime is Python 3.11+ in `pyproject.toml`; no new runtime dependency is needed. |
| Click | 8.3.2 locked | Existing `saymo` CLI commands and new optional options | All command surfaces use Click decorators and `CliRunner` tests. |
| Rich | 15.0.0 locked | Human CLI rendering through shared console | Existing call-ready/scorecard/soak output uses `console.print`, including `soft_wrap=True` for rerun commands. |
| PyYAML | 6.0.3 locked | Config loading only | Existing config stack; Phase 40 should not introduce config parsing alternatives. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 locked | Unit, CLI, and static guard validation | Use for all Phase 40 focused tests and regression suites. |
| stdlib `json` | Python stdlib | JSON artifact and JSONL event parsing | Use instead of ad hoc parsing; current writers already use sorted/sanitized JSON. |
| stdlib `dataclasses` | Python stdlib | Typed metric/report additions | Matches `LaunchReadinessCheck`, `SessionScorecard`, and `SafetySoakReport` patterns. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing dataclasses plus stdlib JSON | Pydantic or Marshmallow | Not justified; project has no schema dependency and existing artifacts are small/local. |
| Extending `SessionScorecard` | New `EvidenceScorecard` report family | Would duplicate rendering, CLI output, remediation, and safety-soak ingestion. |
| Reusing `RemediationHint` | New troubleshooting DSL | Existing hint rendering already sanitizes details and rerun commands. |

**Installation:**

```bash
uv sync
```

**Version verification:** No npm packages are involved. Versions were verified locally from `pyproject.toml` and `uv.lock` on 2026-07-08. Locked package publish/upload timestamps in `uv.lock`: Click 8.3.2 uploaded 2026-04-03; pytest 9.0.3 uploaded 2026-04-07; PyYAML 6.0.3 uploaded 2025-09-25; Rich 15.0.0 uploaded 2026-04-12.

## Existing Artifact Schemas

### Launch-Readiness Artifact

Source of truth: `saymo.analysis.launch_readiness.LaunchReadinessReport.to_dict()`.

Current root fields:

| Field | Meaning | Reuse |
|-------|---------|-------|
| `profile`, `provider` | Selected meeting scope | Use as scorecard evidence scope. |
| `ready` | Overall gate result | Map to launch health. |
| `check_count`, `ready_count`, `block_count`, `warn_count` | Aggregate readiness counts | Use directly; do not recompute from private inputs. |
| `checks[]` | Ordered sanitized check rows | Main source for categories, labels, daemon/provider/cache/voice status, rerun commands. |

Current check fields:

| Field | Meaning | Reuse |
|-------|---------|-------|
| `key`, `label`, `severity`, `ok`, `detail` | Stable check identity and state | Use failed labels and violation classification. |
| `action`, `rerun` | Exact operator next step | Reuse in troubleshooting; do not synthesize alternative commands unless no command exists. |
| `metadata` | Sanitized per-check facts | Use for cache counts, source hashes, voice fingerprints, provider/audio rows, daemon/log paths. |

Known check keys to preserve:

```text
daily_note_present
daily_note_source_ready
prepared_standup_audio
response_cache_coverage
cloned_voice_metadata
provider_meeting_tab
capture_input_device
playback_output_device
provider_output_blackhole
capture_route_blackhole
recording_microphone_input
provider_capabilities
call_control_agent
call_control_daemon
call_control_hotkeys
```

Recommended Phase 40 schema change: keep the existing root shape and add only optional top-level fields such as `schema_version`, `mode`, `artifact_path`, `created_at`, and `evidence_kind`. Do not wrap the report under a new `report` key for `call-ready --output`, because existing tests and user workflows expect root-level `ready` and `checks`.

### Realtime Decision JSONL

Source of truth: `saymo.analysis.realtime_events.RealtimeDecisionEvent.to_dict()`.

Allowlisted event fields:

```text
created_at
profile
provider
outcome
label
source
automatic
intent_key
confidence
audio_path
detail
```

Path contract: `realtime_event_log_path(profile, base_dir=...)` writes `realtime-decisions.jsonl` below the existing live-control profile directory. `live_control_dir()` creates the directory.

Stable current labels/sources to summarize:

| Label | Source | Meaning |
|-------|--------|---------|
| `launch-readiness-blocked` | `launch_readiness` | Realtime startup blocked before live setup. |
| `response-cache-hit` | `response_cache` | Automatic prepared response selected and attempted. |
| `cache-miss-blocked` | `response_cache` | Automatic cache miss failed closed. |
| `cache-disabled-blocked` | `response_cache` | Cache unavailable/disabled. |
| `voice-metadata-blocked` | `response_cache` | Cached response sidecar stale. |
| `fallback-blocked` | `response_cache` or `playback` | Unsafe fallback path blocked. |
| `handbrake-blocked` | `live_control` | Auto-answer off, manual takeover, or hard-disable blocked playback. |
| `provider-blocked` | `provider` or `playback` | Provider readiness or provider playback failure blocked playback. |
| `manual-standup-requested` | `manual_standup` | Explicit operator-requested prepared playback. |
| `manual-standup-blocked` | `manual_standup` | Explicit standup path blocked. |
| `addressing-skip` | `deterministic` or `live_assist` | Deterministic or classifier-assisted skip. |

Open gap: explicit stop/cancel live-control actions are currently represented in `audit.jsonl`, not consistently as realtime decision rows. Phase 40 should summarize stop/cancel labels when present in `realtime-decisions.jsonl`, but safety/scorecard stop counts should continue to use live-control audit metrics unless a future runtime phase adds more event emission.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/analysis/
├── launch_readiness.py       # existing report/check source of truth; artifact writer may get optional metadata
├── launch_evidence.py        # recommended focused loader/normalizer over launch artifact JSON
├── realtime_events.py        # existing event schema; add JSONL loader and summary dataclasses here
├── session_scorecard.py      # extend with v1.9 launch/realtime metric dataclasses and optional ingestion
├── safety_soak.py            # add v1.9 violations derived from scorecard metrics
└── remediation.py            # extend hints/troubleshooting over scorecards and evidence summaries

saymo/commands/
├── call_ready.py             # preserve existing --json and --output behavior
├── tests.py                  # current home of session-scorecard and safety-soak CLI options
└── core.py                   # realtime event writing exists here; do not add reporting imports here
```

### Pattern 1: Backward-Compatible Launch Artifact Normalization

**What:** Load existing raw `LaunchReadinessReport.to_dict()` JSON and optional Phase 40 enriched root fields into a typed `LaunchEvidence` object.

**When to use:** Scorecard, safety-soak, and troubleshooting code needs launch health without re-running readiness checks.

**Example:**

```python
# Source: local pattern from saymo.analysis.launch_readiness.write_launch_readiness_artifact
@dataclass(frozen=True)
class LaunchEvidence:
    path: str
    mode: str
    ready: bool
    block_count: int
    warn_count: int
    checks: tuple[dict[str, Any], ...]

def load_launch_evidence(path: str | Path) -> LaunchEvidence:
    artifact_path = Path(path).expanduser()
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    return LaunchEvidence(
        path=str(artifact_path),
        mode=str(data.get("mode") or "call-ready"),
        ready=bool(data.get("ready")),
        block_count=int(data.get("block_count") or 0),
        warn_count=int(data.get("warn_count") or 0),
        checks=tuple(row for row in data.get("checks") or () if isinstance(row, dict)),
    )
```

### Pattern 2: Realtime JSONL Loader With Malformed-Row Tolerance

**What:** Add `load_realtime_decision_events()` and `summarize_realtime_decision_events()` to `realtime_events.py`.

**When to use:** Scorecards and troubleshooting should never fail because one event row was partially written.

**Example:**

```python
# Source: local JSONL style from session_scorecard._load_live_control_audit
@dataclass(frozen=True)
class RealtimeEventSummary:
    path: str
    total: int = 0
    malformed_rows: int = 0
    outcome_counts: dict[str, int] = field(default_factory=dict)
    label_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)

def iter_realtime_decision_rows(path: str | Path):
    for raw in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            yield None
            continue
        yield data if isinstance(data, dict) else None
```

### Pattern 3: Optional Scorecard Metrics With Defaults

**What:** Add new frozen metric dataclasses at the end of `SessionScorecard` so old construction remains valid.

**When to use:** Existing rehearsal/regression scorecards must work unchanged when no Phase 40 paths are supplied.

**Example:**

```python
@dataclass(frozen=True)
class LaunchEvidenceMetrics:
    status: str = "unavailable"
    ready: bool | None = None
    block_count: int = 0
    warn_count: int = 0
    failed_labels: tuple[str, ...] = ()
    artifact_path: str = ""

@dataclass(frozen=True)
class RealtimeEvidenceMetrics:
    status: str = "unavailable"
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_blocks: int = 0
    provider_blocks: int = 0
    handbrake_blocks: int = 0
    malformed_rows: int = 0
    artifact_path: str = ""
```

### Pattern 4: Safety-Soak Rules Read Scorecard Metrics Only

**What:** Add v1.9 violations in `_violations_for_scorecard()` based on scorecard launch/realtime metrics.

**When to use:** `safety-soak` should accept scorecard JSON and baselines exactly as it does now.

**Example:**

```python
def _v19_violations_for_scorecard(scorecard: SessionScorecard) -> tuple[SafetySoakViolation, ...]:
    launch = scorecard.launch_evidence_metrics
    realtime = scorecard.realtime_evidence_metrics
    violations = []
    if launch.status != "unavailable" and launch.ready is False:
        violations.append(SafetySoakViolation(scorecard.source_id, "launch_not_ready", launch.failed_summary))
    if realtime.provider_blocks:
        violations.append(SafetySoakViolation(scorecard.source_id, "provider_blocked", f"provider_blocks={realtime.provider_blocks}"))
    return tuple(violations)
```

### Anti-Patterns to Avoid

- **Re-running readiness inside scorecards:** Load the artifact. Re-running `collect_launch_readiness()` can mutate with `prepare=True` if miswired and can drift from the evidence being explained.
- **Wrapping `call-ready --output` in a new incompatible root:** Keep `ready` and `checks` at the root. Optional extra root fields are safer.
- **Importing scorecard/safety-soak into `core.py` or realtime policy:** Phase 39 static guards intentionally keep Phase 40 reporting out of runtime modules.
- **Counting raw text or response content:** Summaries must use labels, outcomes, sources, stable keys, counts, hashes, and paths only.
- **Direct provider/audio diagnostics in evidence readers:** No Chrome activation, mute toggles, mic switching, playback, recording, route writes, or process kills.

## Proposed Module Boundaries for EVID-01..EVID-05

| Requirement | Primary Module | CLI Surface | Notes |
|-------------|----------------|-------------|-------|
| EVID-01 | `launch_readiness.py` plus focused `launch_evidence.py` | `call-ready --output` unchanged; optional richer fields | Keep `LaunchReadinessReport.to_dict()` root fields authoritative. Add loader and normalized metrics. |
| EVID-02 | `realtime_events.py` | `session-scorecard --realtime PATH` and troubleshooting output | Add loader/summary over JSONL; skip malformed rows and report a warning count. |
| EVID-03 | `session_scorecard.py` | `session-scorecard --launch-readiness PATH --realtime PATH` | Add optional typed metrics and Markdown/JSON sections. Preserve no-evidence behavior. |
| EVID-04 | `safety_soak.py` | Existing `safety-soak --scorecard-json PATH` | Add v1.9 violations derived from scorecard metrics; do not read raw evidence directly in soak. |
| EVID-05 | `remediation.py` and `commands/tests.py` | Existing scorecard/soak output plus optional troubleshooting section | Reuse `RemediationHint`; include artifact/log paths and rerun commands. |

## Backward Compatibility Constraints

- `saymo call-ready --json` must continue printing only valid JSON to stdout.
- `saymo call-ready --output PATH --json` must not print `artifact:` into stdout.
- Existing launch artifact consumers must still find root-level `ready`, `block_count`, `warn_count`, and `checks`.
- `LaunchReadinessCheck` and `LaunchReadinessReport` constructor call sites should continue working; any new dataclass fields need defaults and should be appended.
- `scorecard_from_json()` must load old scorecards without launch/realtime fields and default new metrics to `status="unavailable"`.
- `scorecard_to_json()` should keep omitting `source_path`; add artifact paths through explicit sanitized evidence metrics instead.
- `render_scorecard_markdown()` should not change existing section meanings. Add a new v1.9 evidence section after current playback/handbrake summary.
- `safety_soak_from_json()` must load older soak baselines; new totals/violations must not require baseline schema changes.
- Existing `session-scorecard` should still require exactly one of `--rehearsal` or `--session`; v1.9 evidence paths should be optional enrichments, not a replacement source, unless the planner explicitly decides to add an evidence-only mode.
- New path options must be local file paths and deterministic under pytest fixtures.

## Privacy and Mutation Guard Scope

### Privacy Guard

Apply static and serialization tests to these modules:

```text
saymo/analysis/launch_readiness.py
saymo/analysis/launch_evidence.py
saymo/analysis/realtime_events.py
saymo/analysis/session_scorecard.py
saymo/analysis/safety_soak.py
saymo/analysis/remediation.py
```

Forbidden serialized or source-visible private payload names for new evidence code:

```text
raw_transcript
generated_answer
answer_text
audio_bytes
PRIVATE_
daily_note body fields
transcript_window
```

Allowed evidence values:

- Stable labels such as `cache-miss-blocked`, `provider-blocked`, `handbrake-blocked`.
- Counts, booleans, schema versions, timestamps, and local sanitized paths.
- Source hashes/fingerprints such as `source_sha256`, `reference_fingerprint`, and voice metadata hashes.
- Rerun commands that are already sanitized by launch/readiness/remediation helpers.

### Provider/Audio Mutation Guard

Evidence loaders, scorecard ingestion, safety-soak, and remediation renderers must not call or import mutating APIs. Keep a static guard for:

```text
activate_meeting(
toggle_mute(
switch_mic(
get_previous_app(
activate_app(
leave_meeting(
play_audio_bytes
play_bytes_to_devices
sd.rec
sounddevice.rec
_write_audio_settings_to_user_config
set_input_volume
bump_input_volume
killall
pkill
bootstrap_argv(
bootout_argv(
kickstart_argv(
append_control_command(
run_handbrake_reachability_probe(
```

Launch readiness collection already performs read-only provider/audio and daemon status checks. Phase 40 evidence readers should read artifacts, not call those collectors.

## Recommended Plan Split

### 40-01: Define and write sanitized launch-readiness artifact schema

Scope:

- Add `launch_evidence.py` loader/normalizer or equivalent focused helper.
- Keep `LaunchReadinessReport.to_dict()` as source; add optional top-level artifact fields only if needed.
- Preserve `call-ready --output` and `--json` behavior.
- Add tests for mode, artifact path, blocker categories, cache counts, voice/cache fingerprints, provider status, daemon status, rerun commands, and legacy raw report loading.

Primary requirement: EVID-01.

### 40-02: Feed realtime and launch-health evidence into rehearsal/session scorecards

Scope:

- Add realtime JSONL loader and summary helpers to `realtime_events.py`.
- Add `LaunchEvidenceMetrics` and `RealtimeEvidenceMetrics` to `SessionScorecard`.
- Add optional CLI paths: recommended `--launch-readiness PATH`, `--realtime PATH`, and possibly `--evidence-root ROOT`.
- Render JSON and Markdown evidence sections.
- Preserve existing no-evidence scorecards.

Primary requirements: EVID-02, EVID-03.

### 40-03: Extend safety-soak with v1.9 readiness, daemon, cache, and fallback gates

Scope:

- Add v1.9 violations from scorecard metrics: stale cache, launch not ready, missing/stale daemon, provider blockers, handbrake blocks, fallback blocks, unsafe automatic playback.
- Add totals for v1.9 evidence counts where useful.
- Keep baseline drift comparison intact.
- Keep `safety-soak` reading scorecards and baselines; do not make it depend on live provider/browser state.

Primary requirement: EVID-04.

### 40-04: Add troubleshooting output, rerun commands, docs, and evidence tests

Scope:

- Extend `hints_from_scorecard()` and `hints_from_safety_soak()` for v1.9 metrics.
- Add a deterministic troubleshooting renderer that lists artifact paths, failed labels, categories, log paths, and rerun commands.
- Add CLI output assertions for scorecard/soak troubleshooting.
- Add static privacy and provider/audio mutation guards across all Phase 40 modules.
- Update docs only if the plan includes docs; do not change runtime behavior.

Primary requirement: EVID-05 plus phase-level regression proof.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Launch readiness decisions | A second readiness evaluator | `LaunchReadinessReport.to_dict()` and existing checks | Current checks already encode source, cache, voice, provider/audio, daemon, and rerun metadata. |
| Realtime evidence schema | Arbitrary event dicts | `RealtimeDecisionEvent.to_dict()` and JSONL loader | Existing schema is allowlisted and sanitized. |
| Scorecard/report family | New parallel evidence scorecard | Extend `SessionScorecard` with defaulted metrics | Existing JSON, Markdown, CLI, remediation, and safety-soak paths already consume `SessionScorecard`. |
| Safety gate aggregation | A direct raw evidence gate | `SafetySoakReport` over evidence-rich scorecards | Keeps baseline drift and source summaries intact. |
| Troubleshooting prose | Free-form string heuristics | `RemediationHint` plus existing launch check actions/reruns | Existing renderer sanitizes details and rerun commands. |
| JSONL parsing | Regex/string splitting | `json.loads` per line with malformed-row count | Prevents partial writes from crashing scorecards and avoids parsing bugs. |
| Provider/audio validation | Fresh Chrome/audio probing in evidence modules | Sanitized artifact metadata and existing audit/event logs | Prevents Phase 40 from mutating live call state or drifting from recorded evidence. |

**Key insight:** The hard safety work already happened in Phases 36-39. Phase 40 should make that evidence visible and gateable. Custom realtime behavior or new live probes would reduce trust because they could disagree with the artifacts being explained.

## Common Pitfalls

### Pitfall 1: Breaking Artifact Shape

**What goes wrong:** `call-ready --output` changes from root-level report fields to a nested wrapper, breaking consumers that read `checks`.
**Why it happens:** Adding schema metadata feels like a new report format.
**How to avoid:** Keep root-level `ready`, counts, and `checks`; add optional metadata fields only.
**Warning signs:** Tests need broad rewrites around `payload["checks"]`.

### Pitfall 2: Evidence Readers Recompute Live State

**What goes wrong:** Scorecard generation calls `collect_launch_readiness()` or provider/audio helpers and reports current machine state instead of the saved artifact.
**Why it happens:** Existing collectors are easy to import.
**How to avoid:** Load `call-ready` artifact JSON; treat missing artifact as `unavailable`.
**Warning signs:** Evidence tests need mocks for Chrome, sounddevice, LaunchAgent, or provider factories.

### Pitfall 3: Malformed JSONL Aborts Scorecards

**What goes wrong:** One partial event row prevents all scorecard output.
**Why it happens:** JSONL append is best-effort during a live loop and may be interrupted.
**How to avoid:** Skip malformed rows, increment `malformed_rows`, and add a sanitized warning.
**Warning signs:** Loader tests expect `json.JSONDecodeError`.

### Pitfall 4: Treating All Blocks As Unsafe Playback

**What goes wrong:** Fail-closed blocks are confused with actual unsafe playback.
**Why it happens:** Both are negative conditions.
**How to avoid:** Keep separate metrics: `unsafe_automatic_playback` means playback occurred across a safety boundary; `fallback_blocks`, `provider_blocks`, and `handbrake_blocks` are failed gate conditions that should fail v1.9 soak for remediation but are not playback bypasses.
**Warning signs:** Existing `unsafe_automatic_playback` tests start failing when only blocked events are present.

### Pitfall 5: Leaking Useful But Private Details

**What goes wrong:** Event detail or launch metadata includes note content, transcript snippets, generated responses, or secrets.
**Why it happens:** Troubleshooting output tries to be too descriptive.
**How to avoid:** Use labels, hashes, counts, path basenames or sanitized paths, and rerun commands. Keep static forbidden-name tests.
**Warning signs:** New tests assert raw phrases or response text in evidence output.

### Pitfall 6: Importing Reporting Into Realtime Runtime

**What goes wrong:** `core.py` or realtime policy imports scorecard/safety-soak code.
**Why it happens:** It seems convenient to emit richer evidence at runtime.
**How to avoid:** Keep runtime emitting minimal `RealtimeDecisionEvent`; Phase 40 loaders enrich after the fact.
**Warning signs:** Phase 39 static guard against `scorecard|safety-soak|session-scorecard` fails.

## Code Examples

Verified patterns from local source:

### Launch Artifact Writer

```python
# Source: saymo.analysis.launch_readiness.write_launch_readiness_artifact
def write_launch_readiness_artifact(
    report: LaunchReadinessReport,
    output_path: Path,
) -> Path:
    output_path = Path(output_path)
    output_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
```

### Realtime Event Path

```python
# Source: saymo.analysis.realtime_events.realtime_event_log_path
def realtime_event_log_path(profile: str, *, base_dir: Path | str | None = None) -> Path:
    return live_control.live_control_dir(profile, base_dir=base_dir) / EVENT_LOG_NAME
```

### Scorecard Backward-Compatible JSON Loading

```python
# Source: saymo.analysis.session_scorecard.scorecard_from_json pattern
trigger = data.get("trigger_metrics") or {}
playback = data.get("playback_metrics") or {}
safety = data.get("safety_metrics") or {}
```

### Safety-Soak Violation Extension Point

```python
# Source: saymo.analysis.safety_soak._violations_for_scorecard
def _violations_for_scorecard(scorecard: SessionScorecard) -> tuple[SafetySoakViolation, ...]:
    violations: list[SafetySoakViolation] = []
    source_id = scorecard.source_id
    if scorecard.playback_metrics.unsafe_automatic_playback:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="unsafe_automatic_playback",
                detail="automatic playback occurred while a handbrake boundary was active",
            )
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Preflight/rehearsal reports only | Shared `LaunchReadinessReport` with sanitized check metadata | Phase 36, 2026-07-08 | Phase 40 can load launch evidence instead of running checks. |
| Provider/audio placeholder | Non-destructive provider tab, audio route, capability, and permission rows | Phase 37, 2026-07-08 | Launch artifacts already expose provider/audio readiness. |
| Terminal-owned hotkeys only | LaunchAgent/daemon status and explicit handbrake probe | Phase 38, 2026-07-08 | Launch artifacts include daemon/log path metadata; do not run probe implicitly. |
| Realtime could fall back to live response paths | Fail-closed cache-only automatic policy | Phase 39, 2026-07-08 | Scorecards should count cache hit/miss/fallback blocks from events. |
| No realtime decision artifact | Allowlisted `realtime-decisions.jsonl` | Phase 39, 2026-07-08 | Phase 40 can summarize decisions without raw meeting content. |

**Deprecated/outdated:**

- `provider_audio_basic_scope`: removed after Phase 37; do not plan around it.
- Direct automatic fallback/TTS for cache misses: Phase 39 guards assert it stays out of `core.py`.
- Cron scheduling on macOS: project/global guidance requires LaunchAgent/launchd, not cron.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 locked in `uv.lock` |
| Config file | none detected; commands run through `uv run pytest` |
| Quick run command | `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/analysis/test_remediation.py -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| EVID-01 | Launch artifact includes sanitized checks, blocker categories, cache/voice/provider/daemon metadata, paths, mode, rerun commands | unit + CLI | `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` | Existing plus Phase 40 additions |
| EVID-02 | Realtime JSONL loader skips malformed rows and summarizes outcomes/labels/sources | unit | `uv run pytest tests/analysis/test_realtime_events.py -q` | Existing plus Phase 40 additions |
| EVID-03 | Scorecard JSON/Markdown includes v1.9 launch/realtime metrics without breaking old inputs | unit + CLI | `uv run pytest tests/analysis/test_session_scorecard.py tests/test_session_scorecard_cli.py -q` | Existing plus Phase 40 additions |
| EVID-04 | Safety-soak fails on v1.9 unsafe conditions and safe evidence passes | unit + CLI | `uv run pytest tests/analysis/test_safety_soak.py tests/test_safety_soak_cli.py -q` | Existing plus Phase 40 additions |
| EVID-05 | Troubleshooting output includes artifact/log paths, labels, categories, and rerun commands without leaks | unit + CLI + static | `uv run pytest tests/analysis/test_remediation.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q` | Existing plus Phase 40 additions |

### Sampling Rate

- **Per task commit:** Run the focused files touched by that task plus the relevant CLI test.
- **Per wave merge:** Run the focused Phase 40 suite from `40-VALIDATION.md`.
- **Phase gate:** Full suite green before `/gsd:verify-work`.

### Required Validation Commands

Focused Phase 40 suite:

```bash
uv run pytest \
  tests/analysis/test_launch_readiness.py \
  tests/analysis/test_realtime_events.py \
  tests/analysis/test_session_scorecard.py \
  tests/analysis/test_safety_soak.py \
  tests/analysis/test_remediation.py \
  tests/test_call_ready_cli.py \
  tests/test_session_scorecard_cli.py \
  tests/test_safety_soak_cli.py \
  -q
```

v1.9 regression suite:

```bash
uv run pytest \
  tests/analysis/test_realtime_gate.py \
  tests/analysis/test_realtime_policy.py \
  tests/analysis/test_realtime_events.py \
  tests/test_auto_qa_flow.py \
  tests/test_call_ready_cli.py \
  tests/test_live_control_cli.py \
  tests/test_realtime_static_guards.py \
  tests/test_call_control_cli.py \
  -q
```

Safety regression suite:

```bash
uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q
```

Full suite:

```bash
uv run pytest
```

Static privacy guard:

```bash
! rg "raw_transcript|generated_answer|answer_text|audio_bytes|PRIVATE_" \
  saymo/analysis/launch_readiness.py \
  saymo/analysis/launch_evidence.py \
  saymo/analysis/realtime_events.py \
  saymo/analysis/session_scorecard.py \
  saymo/analysis/safety_soak.py \
  saymo/analysis/remediation.py
```

Static provider/audio mutation guard:

```bash
! rg "activate_meeting\\(|toggle_mute\\(|switch_mic\\(|get_previous_app\\(|activate_app\\(|leave_meeting\\(|play_audio_bytes|play_bytes_to_devices|sd\\.rec|sounddevice\\.rec|_write_audio_settings_to_user_config|set_input_volume|bump_input_volume|killall|pkill|bootstrap_argv\\(|bootout_argv\\(|kickstart_argv\\(|append_control_command\\(|run_handbrake_reachability_probe\\(" \
  saymo/analysis/launch_readiness.py \
  saymo/analysis/launch_evidence.py \
  saymo/analysis/realtime_events.py \
  saymo/analysis/session_scorecard.py \
  saymo/analysis/safety_soak.py \
  saymo/analysis/remediation.py
```

### Wave 0 Gaps

- [ ] `tests/analysis/test_realtime_events.py` - add loader/summary malformed-row and label/source count coverage for EVID-02.
- [ ] `tests/analysis/test_session_scorecard.py` - add launch/realtime metric JSON/Markdown/backward-compat coverage for EVID-03.
- [ ] `tests/analysis/test_safety_soak.py` - add v1.9 launch/cache/daemon/provider/fallback violation coverage for EVID-04.
- [ ] `tests/analysis/test_remediation.py` - add troubleshooting hints for evidence metrics and artifact/log paths for EVID-05.
- [ ] `tests/test_session_scorecard_cli.py` - add optional `--launch-readiness` and `--realtime` CLI coverage.
- [ ] `tests/test_safety_soak_cli.py` - add evidence-rich scorecard JSON gate coverage.

## Open Questions

1. **Should `safety-soak` accept raw launch/realtime evidence paths directly?**
   - What we know: CONTEXT says new v1.9 violations should be derived from sanitized scorecard metrics, and existing safety-soak accepts scorecards/baselines.
   - What's unclear: A direct evidence input could be convenient but would duplicate scorecard ingestion.
   - Recommendation: Do not add direct raw evidence inputs in Phase 40. Use `session-scorecard --launch-readiness --realtime --json-output` followed by `safety-soak --scorecard-json`.

2. **How should stop reasons appear in realtime evidence?**
   - What we know: `realtime-decisions.jsonl` currently records launch blocks, skips, cache/fallback/metadata blocks, provider/handbrake blocks, manual standup decisions, and playback block results. Explicit stop/cancel actions are already counted from live-control audit in scorecards.
   - What's unclear: EVID-02 names stop reasons under realtime events, but Phase 40 must not add new runtime behavior.
   - Recommendation: Summarize stop/cancel labels if present in realtime JSONL; keep stop/cancellation counts from live-control audit for scorecards. Do not add new event emission in Phase 40 unless the planner explicitly treats it as reporting-only and verifies it does not alter fail-closed behavior.

3. **Where should launch evidence helpers live?**
   - What we know: `launch_readiness.py` is already 422 lines and owns live collection/rendering/writing.
   - What's unclear: Adding loaders there keeps everything together but increases module size.
   - Recommendation: Add `saymo.analysis.launch_evidence` for loader/normalizer/metrics, while keeping the writer and report source in `launch_readiness.py`.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/40-launch-and-realtime-evidence-feedback/40-CONTEXT.md` - Phase 40 scope, constraints, module boundary suggestions.
- `.planning/phases/40-launch-and-realtime-evidence-feedback/40-VALIDATION.md` - Required validation commands and done criteria.
- `.planning/ROADMAP.md` - Phase 40 four-plan split and milestone goals.
- `.planning/REQUIREMENTS.md` - EVID-01 through EVID-05 requirement text.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-05-SUMMARY.md` - Current realtime event contract and Phase 40 handoff.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-VERIFICATION.md` - Verified Phase 39 behavior and human residual risks.
- `saymo/analysis/launch_readiness.py` - Launch report/check schema, sanitizer, artifact writer, call-control rows.
- `saymo/analysis/realtime_events.py` - Realtime event schema, path, sanitizer, append helper.
- `saymo/analysis/session_scorecard.py` - Existing scorecard dataclasses, JSON/Markdown rendering, live-control audit ingestion.
- `saymo/analysis/safety_soak.py` - Existing soak aggregation and violation extension points.
- `saymo/analysis/remediation.py` - Existing remediation hint categories/rendering.
- `saymo/commands/call_ready.py`, `saymo/commands/tests.py`, `saymo/commands/core.py` - CLI wiring and runtime event emission boundaries.
- `tests/analysis/*` and CLI tests listed in Validation Architecture - Current executable contracts.

### Secondary (MEDIUM confidence)

- `uv.lock` - Local locked package versions and upload timestamps for Click, Rich, PyYAML, pytest.
- Phase 36-38 summaries - Historical rationale for launch readiness, provider/audio non-mutation, and daemon handbrake contracts.

### Tertiary (LOW confidence)

- None. No external web research was needed because Phase 40 is constrained to local project contracts and no new libraries are recommended.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - verified from `pyproject.toml` and `uv.lock`; no new dependency recommended.
- Architecture: HIGH - based on local source and completed Phase 36-39 summaries.
- Pitfalls: HIGH - based on current tests, validation docs, and Phase 39 static guards.
- Stop-reason handling: MEDIUM - explicit stop/cancel currently lives in audit evidence, not consistently in realtime decision JSONL.

**Research date:** 2026-07-08
**Valid until:** 2026-08-07, or until Phase 40 implementation changes artifact schemas.

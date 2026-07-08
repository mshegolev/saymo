# Phase 36: Call-Ready Preflight and Cache Gate - Research

**Researched:** 2026-07-08
**Domain:** Saymo launch readiness, Obsidian daily-note source checks, prepared audio cache, response-cache coverage, cloned-voice metadata, and remediation output
**Confidence:** HIGH for repo-local implementation patterns; MEDIUM for the exact provider/audio placeholder policy because Phase 37 owns the deeper provider/audio gate

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

- Deep Chrome/Glip tab capability, BlackHole route, permission, and takeover
  checks are Phase 37.
- Call-control daemon, heartbeat, LaunchAgent lifecycle, and menu-adjacent
  status are Phase 38.
- Fail-closed realtime behavior and cache-miss policy enforcement are Phase 39.
- Full launch/realtime scorecard and safety-soak evidence feedback is Phase 40.
- Native menu bar app packaging, calendar launch, automatic provider repair,
  and live LLM+TTS fallback are outside v1.9 Phase 36.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAUN-01 | User can run one call-ready command for a profile and provider that returns a concise `ready` or `not ready` result before a call. | Add a thin Click wrapper in a new command module and a structured report in `saymo.analysis.launch_readiness`; render one top-level result from blocking check status. |
| LAUN-02 | User can have the call-ready flow create or verify today's Obsidian daily note without overwriting existing note content. | Move/import daily-note creation logic into `saymo.obsidian.daily_notes`; keep script as a wrapper; call it only under `--prepare`. |
| LAUN-03 | User can see daily-note source readiness separately from file existence, including a blocker when the note contains only placeholders or no usable standup content. | Add separate `daily_note_present` and `daily_note_source_ready` checks; strip headings/template placeholders and avoid printing note text. |
| LAUN-04 | User can have the call-ready flow prepare or verify the current standup audio for the selected profile without silently accepting stale prepared WAVs. | Reuse `_call_ready_cached_audio`, but extend metadata to include source/profile freshness; block `audio_missing`, `voice_metadata_missing`, `voice_metadata_stale`, and source digest mismatch. |
| LAUN-05 | User can see response-cache coverage for the selected profile, voice, and response library as counts plus exact stale or missing variant blockers. | Add a public response-cache coverage helper using `ResponseCache`, `build_library`, and voice metadata; count every current variant and return missing/stale examples. |
| LAUN-06 | User can see approved cloned-voice metadata for prepared and response-cache audio, including selected engine, voice profile, approval state, reference fingerprint, and stale-cache reason. | Surface `VoiceCacheMetadata` and `resolve_voice_selector(..., purpose="live_call")` fields in sanitized check metadata; never print raw reference text. |
| LAUN-07 | User can get grouped `block`, `warn`, and `info` remediation with exact action and rerun commands for every call-ready check. | Extend `RemediationHint` mapping for launch-readiness checks and render grouped output using the existing renderer style. |
</phase_requirements>

## Summary

Phase 36 should create a shared launch-readiness model, not another CLI-only diagnostic. The current repo already has most primitives: `auto-preflight` checks, prepared-WAV metadata validation, response-cache building, voice selector approval gates, Obsidian note reading, daily-note bootstrapping, and remediation rendering. The plan should extract or wrap those primitives into `saymo.analysis.launch_readiness`, then add a thin `saymo call-ready` command.

The highest-risk finding is that existing checks are too permissive for this phase. `auto-preflight` currently marks response cache and hotkeys as nonblocking, counts a response cache as okay when any variant exists, and uses private cache helpers for coverage. Also, `build_voice_cache_metadata(..., text=...)` accepts text but the current fingerprint does not include the text/source payload, so prepared audio can be voice-fresh while source-stale. Phase 36 must close that gap before reporting `call-ready: ready`.

**Primary recommendation:** implement a typed, privacy-safe `LaunchReadinessReport` in `saymo.analysis.launch_readiness`; make daily-note source readiness, prepared standup metadata/source freshness, response-cache full coverage, and approved cloned voice metadata blocking; keep provider/audio as explicitly scoped Phase 37 placeholder/basic delegated checks.

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| Python | `>=3.11` from `pyproject.toml` | Dataclasses, paths, JSON, hashing, date handling | Existing repo baseline; no new runtime needed. |
| Click | `>=8.1.0`, locked `8.3.2` in `uv.lock` | `saymo call-ready` CLI options and exit behavior | Existing Saymo command framework. |
| Rich | `>=13.0.0`, locked `15.0.0` in `uv.lock` | Human-readable console output | Existing `console` output style. |
| PyYAML | `>=6.0`, locked `6.0.3` in `uv.lock` | Config loading through `saymo.config.load_config` | Reuse existing config loader; do not add another YAML parser. |
| pytest | dev `>=9.0.3`, locked `9.0.3` in `uv.lock` | Unit and CLI tests | Existing test framework. |
| `saymo.analysis.response_cache` | internal | Response library, deterministic variant paths, metadata-aware readiness | Already owns response cache semantics. |
| `saymo.analysis.cache_metadata` | internal | Voice/cache sidecars and stale reasons | Already owns privacy-safe voice fingerprints. |
| `saymo.tts.selector` | internal | Approved cloned-voice readiness | Existing call-ready voice gate from v1.8. |
| `saymo.obsidian.daily_notes` | internal | Daily-note discovery and reading | Correct package home for importable daily-note helpers. |
| `saymo.analysis.remediation` | internal | Action/rerun remediation rendering | Existing sanitized remediation style. |

### Supporting

| Library / Module | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| `click.testing.CliRunner` | Click locked `8.3.2` | CLI regression tests | Test `saymo call-ready` output and options without launching real audio/provider code. |
| `pathlib`, `hashlib`, `json`, `datetime` | stdlib | File paths, privacy-safe source digests, JSON output | Use for readiness dataclasses and artifacts. |
| `soundfile` | locked `0.13.1` | Test voice-profile fixtures already use it | Only if tests need WAV fixtures matching selector tests; not needed for status logic. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dataclasses | Pydantic | Adds dependency and validation style not used elsewhere; unnecessary for local report structs. |
| Existing config loader | Script-local YAML parser | The script parser already exists, but long-term call-ready must use `SaymoConfig` to avoid config drift. |
| `ResponseCache` helpers | Ad hoc `glob("*.wav")` scanning | Glob counts stale files and old text hashes as ready; use deterministic variant paths and metadata checks. |
| Existing remediation renderer | New prose/table formatter | Duplicates sanitization and categories; extend `RemediationHint` instead. |
| Deep provider/audio checks | New browser/audio stack in Phase 36 | Out of scope; Phase 37 owns deep provider and audio readiness. |

**Installation:**

```bash
uv sync
```

**Version verification:** Python package versions were verified from local `pyproject.toml`, `uv.lock`, and `uv --version` on 2026-07-08. This is a Python project; `npm view` is not applicable. No new packages are recommended.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
├── analysis/
│   ├── launch_readiness.py     # New: report/check dataclasses and collectors
│   ├── response_cache.py       # Add public coverage/status helper
│   ├── cache_metadata.py       # Extend metadata/source fingerprint if needed
│   └── remediation.py          # Extend launch-readiness hint mapping
├── commands/
│   ├── call_ready.py           # New: thin Click wrapper
│   ├── __init__.py             # Import call_ready so decorators register
│   ├── core.py                 # Reuse prepare primitives; avoid raw output in call-ready
│   └── tests.py                # Keep auto-preflight compatible
├── obsidian/
│   └── daily_notes.py          # Add importable ensure/content-readiness helpers
scripts/
└── ensure_obsidian_daily_note.py # Delegate to package helper
tests/
├── analysis/test_launch_readiness.py
├── test_call_ready_cli.py
├── analysis/test_response_cache.py
└── scripts/test_ensure_obsidian_daily_note.py
```

### Pattern 1: Shared Report Contracts

**What:** Use dataclasses for `LaunchReadinessCheck`, `LaunchReadinessReport`, `ResponseCacheCoverage`, and `PreparedAudioStatus`.

**When to use:** Any code that needs to decide or render launch readiness: `call-ready`, future realtime gate, future evidence, and tests.

**Example:**

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Severity = Literal["block", "warn", "info"]

@dataclass(frozen=True)
class LaunchReadinessCheck:
    key: str
    label: str
    severity: Severity
    ok: bool
    detail: str = ""
    action: str = ""
    rerun: str = ""
    metadata: dict[str, str | int | bool] = field(default_factory=dict)

@dataclass(frozen=True)
class LaunchReadinessReport:
    profile: str
    provider: str
    checks: tuple[LaunchReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        return all(check.ok or check.severity != "block" for check in self.checks)
```

### Pattern 2: Thin Click Wrapper

**What:** Put policy and checks in `saymo.analysis.launch_readiness`; the command only parses flags, calls the collector, renders, and sets exit code.

**When to use:** `saymo call-ready -p standup --provider glip [--prepare] [--json]`.

**Example:**

```python
@main.command("call-ready")
@click.option("--profile", "-p", default="standup")
@click.option("--provider", default=None)
@click.option("--prepare", "prepare_missing", is_flag=True)
@click.option("--json", "json_output", is_flag=True)
@click.pass_context
def call_ready(ctx, profile, provider, prepare_missing, json_output):
    report = collect_launch_readiness(
        ctx.obj["config"],
        profile=profile,
        provider_name=provider,
        prepare=prepare_missing,
    )
    render_launch_readiness(report, json_output=json_output)
    raise click.exceptions.Exit(0 if report.ready else 1)
```

Add `call_ready` to the import list at the bottom of `saymo/commands/__init__.py`.

### Pattern 3: Daily Note Presence Is Not Source Readiness

**What:** Add importable package helpers:

- `ensure_daily_note(obsidian_config, target_date=None) -> Path`
- `daily_note_path(obsidian_config, target_date=None) -> Path`
- `inspect_standup_source(path) -> DailyNoteReadiness`

**When to use:** Presence check always; creation only with `--prepare`.

**Example:**

```python
PLACEHOLDER_LINES = {"-", "- ", "", "TODO", "TBD"}

def has_useful_standup_content(markdown: str) -> bool:
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in PLACEHOLDER_LINES:
            continue
        return True
    return False
```

This is intentionally conservative. It should not print note text; it should report path, byte/line counts, section names, and source digest.

### Pattern 4: Response Cache Coverage Is a Public Helper

**What:** Add a public coverage helper instead of making call-ready depend on `ResponseCache._variant_path()` and `_variant_ready()`.

**When to use:** Call-ready, future realtime gate, and safety evidence.

**Example:**

```python
def response_cache_coverage(cache: ResponseCache) -> ResponseCacheCoverage:
    missing: list[str] = []
    stale: list[str] = []
    ready = 0
    total = 0
    expected = cache.voice_metadata
    for entry in cache.library.values():
        for idx, text in enumerate(entry.variants):
            total += 1
            path = cache.variant_path(entry.key, idx, text)
            check = check_voice_cache_metadata(path, expected) if expected else None
            if not path.exists():
                missing.append(f"{entry.key}[{idx}]")
            elif check and not check.valid:
                stale.append(f"{entry.key}[{idx}]:{check.blocked_reason}")
            else:
                ready += 1
    return ResponseCacheCoverage(ready=ready, total=total, missing=tuple(missing), stale=tuple(stale))
```

Expose `variant_path()` publicly or keep the helper inside `response_cache.py` so private naming stays encapsulated.

### Pattern 5: Privacy-Safe Source Freshness

**What:** Prepared audio readiness must include source freshness, not only voice freshness.

**Current gap:** `build_voice_cache_metadata(config, purpose="prepare", text=normalized)` is called when writing prepared audio, but the current metadata fingerprint is built from selector/config payload only; the `text` parameter is not included in the fingerprint.

**Recommended implementation:** Add a non-raw `source_sha256` or `content_sha256` field to `VoiceCacheMetadata` and include it in stale checks, or add a small prepared-audio metadata sidecar that includes:

- `purpose`
- `profile`
- `team_mode`
- `source_kind`
- `source_sha256`
- `selected_engine`
- `voice_profile`
- `reference_audio_sha256`
- `reference_text_sha256`

Do not store raw daily-note text or generated answer text.

### Anti-Patterns to Avoid

- **CLI-owned readiness policy:** Do not add another large block to `saymo/commands/tests.py`; put policy in `saymo.analysis`.
- **Calling noisy `prepare` output directly from call-ready:** `_prepare` currently prints generated standup text. A privacy-safe call-ready flow needs a quiet/lower-level prepare path or a captured/suppressed call plus a sanitized verification report.
- **N>0 response-cache pass:** Phase 36 requires full current-library coverage unless a later mode explicitly disables realtime Q&A.
- **Template-created note equals ready:** A just-created note with only `- ` placeholders is a source blocker.
- **Provider/audio overreach:** Do not claim PROV requirements in Phase 36. Include basic/deferred status only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config parsing | A second YAML parser in call-ready | `saymo.config.load_config` and `SaymoConfig` | Existing env interpolation and dataclass mapping must remain authoritative. |
| Daily-note creation | A separate call-ready file writer | Package helper extracted from `scripts/ensure_obsidian_daily_note.py` | Existing behavior preserves content and has tests. |
| Response cache inventory | `glob` and filename parsing | `ResponseCache`, `build_library`, deterministic variant paths, metadata checks | Filenames encode text hash; stale variants need metadata reasons. |
| Voice/profile validation | Custom profile JSON checks | `resolve_voice_selector` and `build_voice_cache_metadata` | v1.8 already defined approved cloned-voice gates. |
| Metadata sidecars | A new unrelated schema | Extend `VoiceCacheMetadata` or compose with it | Avoid two incompatible freshness mechanisms. |
| Remediation formatting | New print format | `RemediationHint` and `render_remediation_hints` | Existing renderer sanitizes labels and rerun commands. |
| Heavy repair workflow | Installing/training/downloading in `call-ready` | Exact remediation commands | Call-ready must stay fast and mostly read-only. |

**Key insight:** The hard part is not finding files; it is proving that each launch-critical file matches today's profile, source, selected approved voice, and response library without leaking private content. Existing helpers cover most of that, but Phase 36 must add source freshness and full coverage semantics.

## Common Pitfalls

### Pitfall 1: Reusing `auto-preflight` Semantics Unchanged

**What goes wrong:** `call-ready` reports ready even when response cache is partial because existing `auto-preflight` marks response cache `blocking=False` and `ok` when any variant exists.

**Why it happens:** `auto-preflight` was a broad diagnostic and rehearsal input, not the strict launch gate.

**How to avoid:** Create a separate Phase 36 readiness policy. Response cache and prepared standup are blocking. Existing provider/audio checks can be delegated but must be clearly labeled as basic/deferred.

**Warning signs:** Tests assert `call-ready: ready` with `0/N` or `1/N` response variants.

### Pitfall 2: Prepared WAV Is Voice-Fresh But Source-Stale

**What goes wrong:** The cache metadata matches the current voice selector, but the WAV was generated from yesterday's note or an old standup summary.

**Why it happens:** Current voice metadata does not include the prepared text/source digest even though the caller passes `text=`.

**How to avoid:** Add a privacy-safe source digest to prepared audio metadata and compare it during readiness.

**Warning signs:** Editing today's `## Standup Summary` does not make call-ready report stale prepared audio.

### Pitfall 3: `--prepare` Leaks Private Text

**What goes wrong:** `saymo call-ready --prepare` reuses `_prepare` and prints the generated standup summary or daily-note content.

**Why it happens:** Current `prepare` is user-facing and intentionally verbose.

**How to avoid:** Extract reusable prepare logic that returns paths/metadata without printing raw text, or add a quiet mode. The call-ready report should show hashes, paths, counts, and stale reasons only.

**Warning signs:** CLI tests contain raw fixture note text in `result.output`.

### Pitfall 4: Response Coverage Hides Stale Examples

**What goes wrong:** The output says `47/48 variants ready`, but the operator cannot see which variant is missing or stale.

**Why it happens:** Current cache checks only produce a count and path.

**How to avoid:** Return bounded examples such as `missing: status_done[1]`, `stale: blockers_none[0]:voice_metadata_stale`; keep raw variant text out.

**Warning signs:** Remediation says only "run prepare" without a concrete cache count or example.

### Pitfall 5: Phase 36 Accidentally Claims Provider Completion

**What goes wrong:** `call-ready` output implies Glip/BlackHole/mic takeover are fully verified, but Phase 37 has not implemented deeper checks.

**Why it happens:** Existing `auto-preflight` has provider tab and audio device rows, and it is tempting to treat them as complete.

**How to avoid:** Label Phase 36 provider/audio rows as `basic` or `deferred_to_phase_37`; do not map them to PROV requirements. If they block, the detail must say it is only a basic provider tab/device check.

**Warning signs:** Phase 36 tests assert mic switching, mute recovery, or BlackHole route ownership.

## Code Examples

Verified patterns from repo-local sources.

### Metadata-Aware Prepared WAV Check

```python
def _call_ready_cached_audio(config, audio_path) -> tuple[bool, str]:
    live_decision = resolve_voice_selector(config, purpose="live_call")
    if not live_decision.allowed:
        return False, live_decision.blocked_reason

    expected = build_voice_cache_metadata(config, purpose="prepare")
    metadata_check = check_voice_cache_metadata(audio_path, expected)
    if not metadata_check.valid:
        return False, metadata_check.blocked_reason
    return True, ""
```

Use this as the starting point, then add source/profile freshness required by Phase 36.

### Existing Response Cache Build Semantics

```python
cache = ResponseCache(
    library=build_library(config.responses.library),
    cache_dir=cache_dir,
    confidence_threshold=config.responses.confidence_threshold,
    voice_metadata=build_voice_cache_metadata(config, purpose="response_cache"),
)
written = await cache.build(synth, force=force)
```

This already regenerates stale voice metadata when building. Phase 36 needs a public coverage/status helper for checking without rebuilding.

### Existing Daily-Note Creation Behavior

```python
def ensure_daily_note(config: ObsidianConfig, *, target_date: date | None = None) -> Path:
    day = target_date or date.today()
    filename = day.strftime(config.date_format) + ".md"
    target_dir = config.vault_path.expanduser() / config.subfolder if config.subfolder else config.vault_path.expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / filename
    if note_path.exists():
        return note_path
    note_path.write_text(_daily_note_template(day), encoding="utf-8")
    return note_path
```

Move this into `saymo.obsidian.daily_notes` or delegate to a package helper, then keep the script wrapper.

## State of the Art

| Old Approach | Current Phase 36 Approach | When Changed | Impact |
|--------------|---------------------------|--------------|--------|
| `auto-preflight` CLI owns readiness checks | Shared `LaunchReadinessReport` in `saymo.analysis` | Phase 36 | Future phases can reuse the same gate. |
| Response cache warning with `N>0` pass | Full coverage `N/N` blocking gate with examples | Phase 36 | Prevents green launch with unsafe cache gaps. |
| Prepared WAV exists | Prepared WAV metadata plus source/profile digest | Phase 36 | Prevents stale standup audio. |
| Script-specific Obsidian YAML parser | Package helper using existing config model | Phase 36 | Avoids config drift. |
| Remediation generated from generic preflight names | Launch-specific grouped block/warn/info hints | Phase 36 | Every blocker has action and rerun command. |
| Deep provider/audio in launch gate | Basic/deferred provider/audio status only | Phase 36, expanded in Phase 37 | Keeps phase scope honest. |

**Deprecated/outdated:**

- Treating `response cache` as `blocking=False` for a call-ready launch.
- Accepting prepared standup audio without `.meta.json`.
- Considering a placeholder daily note as usable source data.
- Calling raw-text `prepare` output as part of a privacy-safe readiness report.

## Open Questions

1. **Should source freshness live inside `VoiceCacheMetadata` or a separate prepared-source metadata sidecar?**
   - What we know: voice metadata already owns selected engine, profile approval, and reference hashes.
   - What's unclear: adding source fields to the same schema may require migrating existing tests/fixtures; a separate sidecar avoids schema churn but creates two checks.
   - Recommendation: extend `VoiceCacheMetadata` with optional `source_sha256`, `source_kind`, and `profile` fields if the change stays contained; otherwise add a `PreparedAudioMetadata` dataclass next to it and compose both checks in launch readiness.

2. **Should basic provider tab failure block Phase 36 `call-ready`?**
   - What we know: Phase 36 command accepts `--provider`, but deep provider/audio readiness is Phase 37.
   - What's unclear: whether the user wants `call-ready: ready` to mean "cache/source ready" or "safe to join the call" before Phase 37.
   - Recommendation: render provider/audio as explicit `warn` or `info` rows with `deferred_to_phase_37` metadata unless reusing an existing blocking check is necessary for operator safety. Do not claim PROV requirements in Phase 36.

3. **How much of `prepare` should be extracted now?**
   - What we know: existing `_prepare` prints raw standup text and writes metadata; `call-ready --prepare` must remain privacy-safe.
   - What's unclear: whether a full quiet prepare refactor fits Phase 36.
   - Recommendation: extract the smallest quiet helper that returns prepared text digest, audio path, and metadata status; leave broader prepare UX unchanged.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 from `uv.lock` |
| Config file | none - pytest is declared in `pyproject.toml` dev dependency group only |
| Quick run command | `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/scripts/test_ensure_obsidian_daily_note.py tests/analysis/test_response_cache.py -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| LAUN-01 | `saymo call-ready -p personal --provider glip` prints exactly one top-level `call-ready: ready` or `call-ready: not ready` and exits 0/1 from blocking status. | CLI | `uv run pytest tests/test_call_ready_cli.py::test_call_ready_prints_top_level_result -q` | no - Wave 0 |
| LAUN-02 | Missing daily note is created only with `--prepare`; existing note content is preserved. | unit + CLI | `uv run pytest tests/scripts/test_ensure_obsidian_daily_note.py tests/test_call_ready_cli.py::test_call_ready_prepare_creates_note_without_overwrite -q` | partial - existing script tests |
| LAUN-03 | Daily note existence and usable standup source are separate checks; placeholder-only template blocks source readiness. | unit | `uv run pytest tests/analysis/test_launch_readiness.py::test_placeholder_daily_note_blocks_source_readiness -q` | no - Wave 0 |
| LAUN-04 | Prepared standup check blocks missing audio, missing metadata, stale voice metadata, and stale source digest; valid current metadata passes. | unit | `uv run pytest tests/analysis/test_launch_readiness.py::test_prepared_audio_requires_current_metadata_and_source_digest -q` | no - Wave 0 |
| LAUN-05 | Response-cache coverage reports `ready/total` plus bounded missing/stale examples, and partial coverage is blocking. | unit | `uv run pytest tests/analysis/test_response_cache.py::test_response_cache_coverage_reports_missing_and_stale_variants -q` | partial - extend existing file |
| LAUN-06 | Report exposes selected engine, voice profile, approval state, reference hashes/fingerprint, and stale reason without raw text. | unit + CLI | `uv run pytest tests/analysis/test_launch_readiness.py::test_voice_metadata_is_sanitized_and_actionable -q` | no - Wave 0 |
| LAUN-07 | Human output groups `block`, `warn`, and `info` remediation with action and rerun for each failed check. | CLI | `uv run pytest tests/test_call_ready_cli.py::test_call_ready_groups_remediation_with_rerun_commands -q` | no - Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q`
- **Per wave merge:** `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/scripts/test_ensure_obsidian_daily_note.py tests/test_trigger_check.py -q`
- **Phase gate:** `uv run pytest` green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/analysis/test_launch_readiness.py` - covers LAUN-03, LAUN-04, LAUN-06 and readiness report policy.
- [ ] `tests/test_call_ready_cli.py` - covers LAUN-01, LAUN-02 CLI integration, LAUN-07 rendering, `--prepare`, `--json` if implemented.
- [ ] `tests/analysis/test_response_cache.py` - add public coverage helper tests for LAUN-05.
- [ ] `tests/scripts/test_ensure_obsidian_daily_note.py` or new `tests/obsidian/test_daily_notes.py` - assert script delegates to package helper and preserves existing note content.
- [ ] `tests/analysis/test_cache_metadata.py` - add source digest/stale-source metadata tests if metadata schema is extended.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/36-call-ready-preflight-and-cache-gate/36-CONTEXT.md` - locked Phase 36 decisions and deferred scope.
- `.planning/REQUIREMENTS.md` - LAUN-01 through LAUN-07 requirement text.
- `.planning/ROADMAP.md` - Phase 36 goal, dependencies, success criteria, and planned plan split.
- `.planning/STATE.md` - v1.9 decisions and blockers.
- `.planning/research/SUMMARY.md` - milestone-level recommendation and critical pitfalls.
- `.planning/research/ARCHITECTURE.md` - recommended shared readiness architecture.
- `.planning/research/FEATURES.md` - call-ready user workflow and anti-features.
- `.planning/research/PITFALLS.md` - stale cache, empty note, privacy, and heavy-work pitfalls.
- `.planning/research/STACK.md` - dependency and stack recommendations.
- `CLAUDE.md` and `AGENTS.md` - project rules, local-first constraints, TTS naturalness rules, pytest workflow.
- `pyproject.toml` and `uv.lock` - Python/dependency versions and test framework.
- `saymo/commands/tests.py` - `PreflightCheck`, `_collect_auto_preflight`, `_prepare_responses`, `auto-preflight`.
- `saymo/commands/core.py` - `prepare`, `_prepare`, `_call_ready_cached_audio`, and current raw prepare output.
- `saymo/commands/__init__.py` - CLI registration and `_load_cached_summary`.
- `saymo/analysis/response_cache.py` - response-cache build, lookup, and private variant readiness behavior.
- `saymo/analysis/cache_metadata.py` - metadata sidecar schema and stale reasons.
- `saymo/analysis/remediation.py` - sanitized remediation renderer and existing hint mapping.
- `saymo/obsidian/daily_notes.py` and `scripts/ensure_obsidian_daily_note.py` - daily-note read/create behavior.
- `tests/test_trigger_check.py`, `tests/analysis/test_response_cache.py`, `tests/scripts/test_ensure_obsidian_daily_note.py`, `tests/analysis/test_cache_metadata.py`, `tests/tts/test_selector.py` - existing coverage patterns.

### Secondary (MEDIUM confidence)

- No external web search was needed; Phase 36 is repo-local and recommends no new third-party package.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - versions and patterns verified from `pyproject.toml`, `uv.lock`, and existing code.
- Architecture: HIGH - existing modules expose clear seams; main uncertainty is how much quiet-prepare extraction fits Phase 36.
- Pitfalls: HIGH - directly evidenced by current `auto-preflight`, cache metadata, response-cache, and prepare code.
- Provider/audio scope: MEDIUM - Phase 36 must accept `--provider`, but PROV requirements are explicitly deferred to Phase 37.

**Research date:** 2026-07-08
**Valid until:** 2026-08-07 for repo-local architecture; revisit sooner if Phase 37 provider/audio work lands first.

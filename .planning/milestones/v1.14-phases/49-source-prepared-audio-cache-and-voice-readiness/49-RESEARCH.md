# Phase 49: Source, Prepared Audio, Cache, And Voice Readiness - Research

**Researched:** 2026-07-10
**Domain:** Saymo dry-run launch readiness, source metadata, response cache, and cloned voice readiness
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Source Note Handling
- Keep plain `saymo dry-run` read-only; it verifies the selected daily note
  but does not create or overwrite source files.
- Add an explicit source-only repair flag for dry-run, preferred as
  `--prepare-source`, that creates a missing selected Obsidian daily note
  without overwriting existing note content.
- Preserve `saymo call-ready --prepare` behavior for backward compatibility.
- Dry-run source remediation should point back to dry-run with the explicit
  source flag, not to automatic cache rebuilds.

### Prepared Audio Diagnostics
- Reuse existing prepared-audio sidecar and voice-cache metadata checks rather
  than adding a second metadata format.
- Show whether the prepared WAV matches the selected source hash, voice
  profile, profile approval state, and F5 `prepared` source-type preset
  metadata.
- Missing or stale prepared audio should produce a targeted
  `saymo prepare -p <profile>` repair command.
- Do not synthesize, delete, rotate, or overwrite prepared audio from dry-run.

### Response Cache Diagnostics
- Reuse existing response-cache coverage and staleness checks with
  source-aware F5 `response_cache` metadata.
- Surface coverage counts, missing/stale examples, source type, resolved preset
  metadata, and expensive F5 warnings without raw prompt or response text.
- Missing or stale response-cache variants should produce
  `saymo prepare-responses -p <profile>` guidance and must not add `--force`
  by default.
- Dry-run should not rebuild response-cache variants.

### Voice Readiness Safety
- Verify the selected cloned voice profile, approval status, engine safety, and
  stale metadata through existing selector/cache metadata helpers.
- Diagnostics must not read, copy, delete, retrain, or mutate training datasets,
  voice samples, model checkpoints, or fallback model assets.
- Keep private paths and fingerprints sanitized to the level already used by
  launch readiness and cache-status outputs.
- If voice metadata is stale or unapproved, explain the explicit review or
  prepare commands instead of changing the profile automatically.

### Claude's Discretion
- Choose the smallest collector parameterization that lets `call-ready` keep
  its current labels while `dry-run` emits dry-run-specific action and rerun
  commands.
- Add tests at the CLI and launch-readiness layer before implementation, then
  adjust production code only enough to satisfy the Phase 49 success criteria.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Phase 50 handles provider tab, Chrome state, BlackHole routing, playback and
  capture devices, call-control daemon, and LaunchAgent health.
- Phase 51 handles sanitized dry-run evidence reuse in rehearsal, scorecards,
  safety-soak, and latest-vs-previous readiness comparisons.
- Automatic prepared/cache rebuilds, force regeneration, voice retraining, and
  provider auto-repair remain out of scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRC-01 | User can have the dry-run verify or create the selected Obsidian daily note for the active profile without overwriting existing note content. | `collect_daily_note_checks(..., prepare=True)` already calls `ensure_daily_note()`, which creates only missing notes and returns existing files untouched; route it through dry-run `--prepare-source` only. |
| SRC-02 | User can see whether prepared standup audio matches the selected daily-note/source hash, voice profile, and F5 source-type preset metadata. | `prepared_audio_status()` already compares the prepared WAV sidecar with `source_sha256`, live-call selector metadata, and `source_type="prepared"` metadata. Expose safe preset IDs in the launch check metadata. |
| SRC-03 | User can get targeted repair commands for missing or stale prepared audio, including `saymo prepare -p <profile>` and review guidance when needed. | Preserve `collect_prepared_audio_check()` as a read-only check, but parameterize rerun text for dry-run and keep action text targeted to `saymo prepare -p <profile>`. |
| CACHE-01 | User can see response-cache coverage and staleness for the active profile using source-aware F5 `response_cache` metadata. | `collect_response_cache_check()` builds `ResponseCache` with `build_voice_cache_metadata(..., source_type="response_cache")` and reports ready/total, missing/stale examples, preset metadata, and cache dir. |
| CACHE-02 | User can get targeted response-cache repair guidance such as `saymo prepare-responses -p <profile>` without automatic rebuilds or `--force` by default. | `response_cache_advice()` already says to rebuild only missing or stale variants and mentions `--force` only in the warning as avoid-unless-intentional. Assert dry-run keeps that behavior. |
| VOICE-01 | User can verify approved cloned-voice profile readiness and stale voice metadata before launch without touching voice training data or model checkpoints. | `collect_voice_metadata_check()` uses `resolve_voice_selector(config, purpose="live_call")` and safe manifest fields; do not add trainer, checkpoint, inventory, or asset mutation calls. |
</phase_requirements>

## Summary

Phase 49 should not build a new readiness system. The repo already has the correct primitives: `LaunchReadinessReport`, `LaunchReadinessCheck`, `collect_launch_readiness()`, source inspection, prepared WAV sidecars, source-aware F5 metadata, response-cache coverage, and voice selector manifests. The implementation should parameterize the existing launch-readiness collector with a small caller context so `call-ready` keeps current commands while `dry-run` emits dry-run-specific rerun/source-repair commands.

The only operator mutation allowed in this phase is explicitly creating a missing selected Obsidian daily note through `saymo dry-run --prepare-source`. Plain `saymo dry-run` remains read-only, and all audio/cache/voice repairs remain textual guidance. Existing checks already avoid raw note text, response text, prompt text, audio bytes, and training data; tests should lock that privacy contract at the CLI and launch-readiness boundaries.

**Primary recommendation:** Add `saymo dry-run --prepare-source`, introduce a minimal launch-readiness caller context for action/rerun labels, and reuse the existing `VoiceCacheMetadata` plus `ResponseCacheCoverage` checks unchanged for prepared audio, response cache, and cloned voice readiness.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.11 project requirement | Implementation language | Existing Saymo package is Python and uses dataclasses, pathlib, and pytest. |
| Click | 8.3.2 locked | `saymo dry-run` and `saymo call-ready` CLI options | Existing command modules use Click decorators and `CliRunner` tests. |
| pytest | 9.0.3 locked | RED/GREEN validation | Existing suite and GSD plans use focused `uv run pytest ...` commands. |
| PyYAML | 6.0.3 locked | Config loading in tests and app | Existing config loader uses YAML; no new parser needed. |
| Rich | 15.0.0 locked | Human command output | Existing command output uses `console.print`; keep output style consistent. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| repo-local `saymo.obsidian.daily_notes` | current source | Daily note path, idempotent creation, source hash | Use for SRC-01; do not duplicate note creation logic. |
| repo-local `saymo.analysis.cache_metadata` | current source | Prepared/response WAV sidecar metadata | Use for SRC-02, CACHE-01, VOICE-01. |
| repo-local `saymo.analysis.response_cache` | current source | Coverage counts and stale examples | Use for CACHE-01; do not inspect raw response text in diagnostics. |
| repo-local `saymo.tts.selector` and `saymo.tts.f5_presets` | current source | Voice selection and F5 source-type preset fingerprints | Use for prepared and response-cache source metadata. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `LaunchReadinessReport` | New dry-run result model | Rejected: duplicates sanitizer, grouped remediation, JSON shape, and Phase 48 contracts. |
| `VoiceCacheMetadata` sidecars | New prepared-audio metadata schema | Rejected: existing sidecar already stores source hash, voice selector fingerprint, source type, and F5 preset IDs. |
| `ResponseCacheCoverage` | Ad hoc filesystem scan | Rejected: existing helper hides response text and knows stale metadata reasons. |
| `resolve_voice_selector()` | Direct checkpoint/training-file probing | Rejected: violates Phase 49 safety boundary and duplicates selector/manifest policy. |

**Installation:** No new packages. Use the existing uv environment:
```bash
uv sync
```

**Version verification:** Verified locally on 2026-07-10:
```bash
uv run python - <<'PY'
from importlib.metadata import version
for name in ["click", "pytest", "pyyaml", "rich"]:
    print(name, version(name))
PY
uv run pytest --version
```

## Architecture Patterns

### Recommended Project Structure
```text
saymo/
├── commands/
│   └── dry_run.py              # add --prepare-source only; no audio/TTS/provider imports
├── analysis/
│   ├── launch_readiness.py     # add small caller context / rerun parameterization
│   ├── launch_sources.py       # reuse daily-note and prepared-audio collectors
│   ├── launch_cache.py         # reuse response-cache and voice metadata checks
│   ├── cache_advice.py         # keep targeted repair guidance and no default --force
│   └── cache_metadata.py       # one sidecar schema for prepared/response audio
└── tts/
    ├── selector.py             # voice selector and source-aware fingerprint payload
    └── f5_presets.py           # closed source-type vocabulary and preset resolution

tests/
├── test_dry_run_cli.py         # dry-run flag, no standalone --prepare, non-destructive guard
├── test_call_ready_cli.py      # compatibility for call-ready --prepare
└── analysis/
    ├── test_launch_readiness.py
    ├── test_cache_advice.py
    └── test_response_cache.py
```

### Pattern 1: Small Caller Context For Readiness
**What:** Extend `collect_launch_readiness()` and downstream collectors with a minimal context such as `mode="call-ready" | "dry-run"`, `rerun_command`, and `source_prepare_action`. Keep `prepare` as the boolean that means "daily note creation allowed".

**When to use:** Use this when a check's action/rerun text must differ between `call-ready` and `dry-run`, but the underlying readiness logic is identical.

**Example:**
```python
# Source: saymo/analysis/launch_readiness.py and Phase 49 recommendation
report = collect_launch_readiness(
    config,
    profile=profile,
    provider_name=resolved_provider,
    prepare=prepare_source,
    mode="dry-run",
)
```

### Pattern 2: Source-Only Creation Flag
**What:** `saymo dry-run --prepare-source` should set `prepare=True` only for `collect_daily_note_checks()`. It must not call `saymo.commands.core._prepare`, TTS synthesis, cache rebuilds, provider actions, or model utilities.

**When to use:** Use only when the selected daily note is missing and the operator explicitly asks dry-run to create that source file.

**Example:**
```python
# Source: saymo/commands/dry_run.py pattern, with Phase 49 flag
@click.option("--prepare-source", is_flag=True, help="Create the selected daily note if missing")
def dry_run(ctx, profile, provider, prepare_source, json_output, output):
    report = collect_launch_readiness(
        config,
        profile=profile,
        provider_name=resolved_provider,
        prepare=prepare_source,
        mode="dry-run",
    )
```

### Pattern 3: Metadata Comparison, Not Regeneration
**What:** Prepared and response-cache readiness should compare expected metadata to existing sidecars and return stale reasons such as `audio_missing`, `voice_metadata_missing`, `voice_metadata_stale`, or `source_metadata_stale`.

**When to use:** Use for SRC-02, CACHE-01, and VOICE-01. This keeps dry-run cheap, safe, and deterministic.

**Example:**
```python
# Source: saymo/analysis/cache_metadata.py
metadata_check = check_voice_cache_metadata(audio_path, expected)
if not metadata_check.valid:
    reason = metadata_check.blocked_reason
```

### Pattern 4: Sanitized Check Metadata
**What:** Surface hashes, counts, preset IDs, profile IDs, and stale reason enums. Do not surface raw note body, prompt text, response variants, generated answer text, audio bytes, secrets, or training paths.

**When to use:** Every `LaunchReadinessCheck.metadata` payload and JSON/artifact output.

**Example:**
```python
# Source: saymo/analysis/launch_cache.py
metadata={
    "ready": coverage.ready,
    "total": coverage.total,
    "missing_examples": list(coverage.missing),
    "stale_examples": list(coverage.stale),
    "source_type": "response_cache",
    "resolved_preset_id": advice.metadata["resolved_preset_id"],
}
```

### Anti-Patterns to Avoid
- **Standalone `--prepare` on dry-run:** use `--prepare-source`; keep `saymo dry-run --prepare` invalid.
- **Calling `_prepare()` from dry-run:** it rotates cache and synthesizes audio, which violates Phase 49.
- **New metadata sidecar format:** reuse `VoiceCacheMetadata`.
- **Default `--force` guidance:** never suggest `saymo prepare-responses --force` as the normal repair.
- **Raw response examples:** `missing_examples` and `stale_examples` must stay variant keys, not answer text.
- **Voice asset probing beyond selector manifests:** do not inspect or mutate training datasets, model checkpoints, or fallback assets.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dry-run result schema | New dry-run dataclasses | `LaunchReadinessReport` and `LaunchReadinessCheck` | Existing ready counts, severity grouping, sanitizer, and JSON contract are already tested. |
| Daily note path/create | Manual path and write code | `daily_note_path()`, `ensure_daily_note()`, `inspect_standup_source()` | Existing helper preserves existing content and computes privacy-safe source hash. |
| Prepared WAV freshness | Timestamp or filename checks | `build_voice_cache_metadata()` + `check_voice_cache_metadata()` | Sidecar detects source hash, engine, profile approval, selector, and F5 preset changes. |
| Response cache coverage | Directory glob with text parsing | `ResponseCache` + `response_cache_coverage()` | Existing helper reports counts and stale examples without leaking response text. |
| F5 source preset logic | Custom YAML/preset resolver | `resolve_f5_pause_preset_for_source()` | Closed vocabulary and fallback order are already implemented and tested. |
| Voice readiness | Checkpoint/training scans | `resolve_voice_selector(..., purpose="live_call")` | Selector enforces approved clone policy without touching protected assets. |
| Sanitization | Ad hoc redaction per command | `LaunchReadinessCheck.to_dict()` / `LaunchReadinessReport.to_dict()` | Existing sanitizer redacts known sensitive markers and tokens. |

**Key insight:** Phase 49 is a wiring and contract phase. The expensive and risky work already sits behind explicit commands (`saymo prepare`, `saymo prepare-responses`, voice approval/review tools); dry-run should only prove whether those artifacts are current.

## Common Pitfalls

### Pitfall 1: Overloading `prepare=True`
**What goes wrong:** `--prepare-source` accidentally becomes "repair everything" because `prepare=True` is treated broadly.
**Why it happens:** `call-ready --prepare` and future dry-run source creation share a boolean name.
**How to avoid:** Keep `prepare=True` scoped to `collect_daily_note_checks()` and document it as source creation only inside launch readiness.
**Warning signs:** Dry-run imports `_prepare`, `_prepare_responses`, TTS synthesis, audio cache rotation, provider modules, or deletion helpers.

### Pitfall 2: Existing Dry-Run Help Test Blocks `--prepare-source`
**What goes wrong:** `tests/test_dry_run_cli.py` currently asserts `"--prepare" not in result.output`, which will also match `--prepare-source`.
**Why it happens:** Phase 48 only needed to forbid standalone `--prepare`.
**How to avoid:** Update the test to assert `saymo dry-run --prepare` still fails while `--prepare-source` appears in help.
**Warning signs:** A correct `--prepare-source` implementation fails only because of substring matching.

### Pitfall 3: Rerun Commands Still Say `call-ready`
**What goes wrong:** Dry-run blockers tell the operator to rerun `saymo call-ready`, which conflicts with the Phase 49 UX.
**Why it happens:** `launch_sources.py` and `launch_cache.py` currently hardcode `_rerun_command()` as `saymo call-ready ...`.
**How to avoid:** Pass a caller rerun command into collectors or centralize it in a tiny launch-readiness context.
**Warning signs:** Dry-run output includes `rerun: saymo call-ready ...` for source/cache/voice checks.

### Pitfall 4: Source Hash Mismatch
**What goes wrong:** Prepared audio appears stale even after `saymo prepare`.
**Why it happens:** `_prepare()` initially hashes source notes, then after saving reads the daily note hash; readiness uses `inspect_standup_source(note_path).source_sha256`.
**How to avoid:** For Obsidian source readiness, compare against the selected daily note hash returned by `collect_daily_note_checks()`.
**Warning signs:** Prepared audio metadata has a non-empty `source_sha256`, but launch readiness reports `source_metadata_stale` after a fresh prepare.

### Pitfall 5: Missing `source_type`
**What goes wrong:** F5 timing preset changes do not invalidate the right prepared or response-cache artifacts.
**Why it happens:** `selector_fingerprint_payload()` only includes source preset metadata when `source_type` is passed.
**How to avoid:** Always pass `source_type="prepared"` for prepared audio and `source_type="response_cache"` for response variants.
**Warning signs:** Metadata sidecars show blank `source_type`, `source_preset_id`, or `source_override_preset_id`.

### Pitfall 6: Leaking Response Or Source Text
**What goes wrong:** Dry-run JSON or human output contains raw daily note lines, prompt text, generated responses, or cached response variants.
**Why it happens:** It is tempting to include "examples" for missing/stale diagnostics.
**How to avoid:** Use variant keys such as `blockers_none[1]:voice_metadata_stale`; expose hashes/counts/preset IDs only.
**Warning signs:** Tests need private sentinels such as `PRIVATE_DAILY_NOTE` or `PRIVATE RESPONSE TEXT` to be absent from output.

### Pitfall 7: Treating Voice Readiness As Inventory
**What goes wrong:** Dry-run scans or edits training data/checkpoints while trying to prove cloned voice readiness.
**Why it happens:** Voice inventory code exists elsewhere and is easy to conflate with launch readiness.
**How to avoid:** Use only `resolve_voice_selector()` and safe manifest metadata for Phase 49.
**Warning signs:** New imports from trainer, inventory, checkpoint cleanup, dataset, or model download modules.

## Code Examples

Verified patterns from repo sources:

### Idempotent Daily Note Creation
```python
# Source: saymo/obsidian/daily_notes.py
def ensure_daily_note(config: ObsidianConfig, target_date: date | None = None) -> Path:
    note_path = daily_note_path(config, day)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if note_path.exists():
        return note_path
    note_path.write_text(_daily_note_template(day), encoding="utf-8")
    return note_path
```

### Prepared Audio Metadata Check
```python
# Source: saymo/analysis/launch_sources.py
expected = build_voice_cache_metadata(
    config,
    purpose="prepare",
    source_kind=config.speech.source,
    source_profile=profile,
    source_sha256=source_sha256,
    profile=profile,
    source_type="prepared",
)
metadata_check = check_voice_cache_metadata(audio_path, expected)
```

### Response Cache Coverage Without Text
```python
# Source: saymo/analysis/response_cache.py
coverage = response_cache_coverage(cache)
metadata = {
    "ready": coverage.ready,
    "total": coverage.total,
    "missing_examples": list(coverage.missing),
    "stale_examples": list(coverage.stale),
}
```

### Voice Selector Readiness
```python
# Source: saymo/analysis/launch_cache.py
decision = resolve_voice_selector(config, purpose="live_call")
ok = decision.allowed and decision.is_voice_clone and decision.profile_approved
```

### No Default Force Guidance
```python
# Source: saymo/analysis/cache_advice.py
action = (
    f"Run saymo prepare-responses -p {profile} "
    "to rebuild only missing or stale variants."
)
warning = (
    "F5 regeneration can be expensive; avoid saymo prepare-responses --force "
    "unless intentionally rebuilding every response."
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate preflight/readiness concepts | Shared `LaunchReadinessReport` for call-ready and dry-run | Phase 48, 2026-07-10 | Phase 49 should parameterize, not duplicate. |
| Prepared/response artifacts stale only by engine fingerprint | Source-aware F5 metadata with `prepared` and `response_cache` source types | Phase 47 / v1.13 | Dry-run can prove preset-aware freshness. |
| Cache diagnostics as general cache-status output | Launch readiness consumes `response_cache_advice()` metadata | Phase 47 / v1.13 | Dry-run can surface the same safe preset vocabulary. |
| Voice readiness as manual trust | `resolve_voice_selector(live_call)` enforces approved cloned profile | v1.8-v1.9 | Dry-run can block unapproved/non-cloned/unknown engines before launch. |
| Source creation only through `call-ready --prepare` | Phase 49 adds dry-run source-only repair | Phase 49 target | Operator can stay in dry-run workflow while creating only the missing note. |

**Deprecated/outdated:**
- `saymo dry-run` with no preparation path at all: Phase 48 behavior remains default, but Phase 49 needs explicit `--prepare-source`.
- Cache repair through `--force`: keep as exceptional warning text only, never the default repair.
- Metadata-free WAV readiness: stale checks must use `VoiceCacheMetadata` sidecars.

## Open Questions

1. **Should dry-run source creation have any alias besides `--prepare-source`?**
   - What we know: The smart discuss preferred `--prepare-source`; standalone `--prepare` must remain invalid for dry-run.
   - What's unclear: Whether an alias such as `--create-source` is desired.
   - Recommendation: Use only `--prepare-source` for this phase to keep tests and docs unambiguous.

2. **How much private path detail should dry-run print?**
   - What we know: Existing launch readiness and cache-status already include paths such as note path, cache dir, and audio path, while sanitizing text/secrets.
   - What's unclear: Whether future evidence phases will further reduce path exposure.
   - Recommendation: Preserve current launch-readiness sanitization now; defer stronger artifact privacy to Phase 51.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none detected |
| Quick run command | `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SRC-01 | `saymo dry-run --prepare-source` creates a missing selected note and does not overwrite an existing note; plain dry-run stays read-only. | CLI unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_prepare_source_creates_note_without_overwrite -q` | ✅ Wave 0 test missing |
| SRC-02 | Prepared audio check reports source hash, voice profile/approval, and F5 prepared preset metadata. | unit | `uv run pytest tests/analysis/test_launch_readiness.py::test_dry_run_prepared_audio_reports_source_and_preset_metadata -q` | ✅ Wave 0 test missing |
| SRC-03 | Missing/stale prepared audio action is `saymo prepare -p <profile>` and dry-run rerun points back to dry-run. | CLI/unit | `uv run pytest tests/test_dry_run_cli.py::test_dry_run_prepared_audio_repair_guidance_is_targeted -q` | ✅ Wave 0 test missing |
| CACHE-01 | Response-cache launch check reports ready/total, missing/stale examples, source type, and resolved F5 preset metadata. | unit | `uv run pytest tests/analysis/test_response_cache.py::test_dry_run_response_cache_reports_source_aware_coverage -q` | ✅ Wave 0 test missing |
| CACHE-02 | Response-cache repair guidance uses `saymo prepare-responses -p <profile>` and does not default to `--force`. | unit | `uv run pytest tests/analysis/test_cache_advice.py::test_dry_run_response_cache_guidance_omits_force_default -q` | ✅ Wave 0 test missing |
| VOICE-01 | Cloned voice readiness blocks unapproved/stale selector metadata without importing trainer/checkpoint mutation paths. | unit/static | `uv run pytest tests/analysis/test_launch_readiness.py::test_dry_run_voice_metadata_is_read_only_and_actionable -q` | ✅ Wave 0 test missing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_dry_run_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py -q`
- **Per wave merge:** `uv run pytest tests/test_dry_run_cli.py tests/test_call_ready_cli.py tests/analysis/test_launch_readiness.py tests/analysis/test_cache_advice.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/tts/test_selector.py -q`
- **Phase gate:** `uv run pytest -q` before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dry_run_cli.py` - add `--prepare-source`, no standalone `--prepare`, note create/no-overwrite, targeted dry-run rerun/action contracts.
- [ ] `tests/analysis/test_launch_readiness.py` - add caller-context tests for dry-run-specific rerun commands, prepared metadata visibility, and read-only voice metadata.
- [ ] `tests/analysis/test_cache_advice.py` - add explicit no-default-`--force` dry-run guidance regression if existing advice coverage is too indirect.
- [ ] `tests/analysis/test_response_cache.py` - add/extend source-aware coverage regression for dry-run launch path.
- [ ] Framework install: none; pytest exists and is locked.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/49-source-prepared-audio-cache-and-voice-readiness/49-CONTEXT.md` - user decisions, scope, deferred ideas.
- `.planning/REQUIREMENTS.md` - Phase 49 requirements SRC-01, SRC-02, SRC-03, CACHE-01, CACHE-02, VOICE-01.
- `.planning/ROADMAP.md` and `.planning/STATE.md` - phase goal, success criteria, prior Phase 48 decisions.
- `CLAUDE.md` and `AGENTS.md` - repo architecture, test commands, safety and coding conventions.
- `saymo/commands/dry_run.py` and `saymo/commands/call_ready.py` - current CLI wrappers and prepare flag behavior.
- `saymo/analysis/launch_readiness.py` - shared readiness report/check contracts, render/artifact sanitizer, collector order.
- `saymo/analysis/launch_sources.py` - daily note and prepared-audio readiness checks.
- `saymo/analysis/launch_cache.py`, `saymo/analysis/cache_advice.py`, `saymo/analysis/cache_metadata.py`, `saymo/analysis/response_cache.py` - response cache, sidecar metadata, and voice readiness behavior.
- `saymo/tts/selector.py` and `saymo/tts/f5_presets.py` - cloned voice selector and F5 source-type preset fingerprints.
- `tests/test_dry_run_cli.py`, `tests/test_call_ready_cli.py`, `tests/analysis/test_launch_readiness.py`, `tests/analysis/test_cache_advice.py`, `tests/analysis/test_response_cache.py`, `tests/analysis/test_cache_metadata.py`, `tests/tts/test_selector.py` - existing test patterns and gaps.
- `.planning/milestones/v1.13-phases/47-source-type-pause-presets/*` - source-aware F5 metadata history and prior verification.

### Secondary (MEDIUM confidence)
- Local memory `MEMORY.md` Saymo v1.13 archive note - reinforces that source-aware metadata fixture drift is a known risk and protected voice assets require explicit approval.

### Tertiary (LOW confidence)
- None. No external web search was needed because this phase is repo-local and the current source plus lockfile are authoritative.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from `pyproject.toml`, `uv.lock`, `uv run python importlib.metadata`, and `uv run pytest --version`.
- Architecture: HIGH - based on current launch-readiness/source/cache/selector modules and Phase 48/47 planning history.
- Pitfalls: HIGH - derived from existing tests, hardcoded rerun/action strings, Phase 48 dry-run guard, and v1.13 source-aware metadata history.
- Validation: HIGH - pytest infrastructure exists; Wave 0 gaps are concrete missing tests in existing files.

**Research date:** 2026-07-10
**Valid until:** 2026-08-09 for repo-local architecture; re-check dependency versions and planning state if Phase 49 is delayed.

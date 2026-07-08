# Phase 39: Fail-Closed Realtime Meeting Loop - Research

**Researched:** 2026-07-08
**Domain:** Saymo realtime launch gating, response-cache-only automatic playback, provider/handbrake safety
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Use the Phase 36-38 readiness and control contracts as the safety boundary for
realtime mode:

- `saymo auto` remains the primary workflow; new aliases may wrap it, but they
  must share the same launch gate.
- Realtime startup must check the selected profile/provider through
  `collect_launch_readiness()` before capture, STT, provider control, or local
  hotkey registration starts.
- Automatic answers may play only from an approved response-cache hit whose
  cloned-voice metadata is current.
- Cache misses, stale cloned-voice metadata, disabled response cache, blocked
  voice selector, unsafe fallback, provider loss, manual takeover,
  hard-disable, disabled auto-answer, or deterministic addressing skip must
  block automatic playback.
- Explicit manual prepared-standup playback remains allowed through the
  existing `speak`/manual hotkey path when the handbrake state allows it, but
  that manual path must not become the automatic cache-miss fallback.
- Realtime decision output and audit/evidence must use sanitized reason labels
  only, not raw transcripts, generated answers, audio bytes, daily-note
  content, or secrets.

### Grey Areas Resolved By Assumption

#### Launch Gate Strictness

- `saymo auto` should require a passed launch-readiness report by default.
- A future explicit bypass can be considered later, but Phase 39 should not add
  a casual unsafe bypass that undermines the milestone.
- The launch gate should report the same grouped remediation as `saymo
  call-ready` so users fix blockers from one source of truth.
- The gate should run before expensive or stateful realtime setup.

#### Automatic Response Policy

- Automatic Q&A output must be response-cache-only for v1.9.
- Existing live LLM/TTS fallback paths are allowed only outside automatic live
  playback or behind explicit future opt-in work; for this phase, automatic
  cache miss means blocked.
- Fallback standup audio remains an explicit manual action, not an automatic
  answer to a question.
- Voice selector or metadata blockers must prevent automatic playback even if
  an audio file exists.

#### Runtime Provider And Handbrake Policy

- Provider loss should be rechecked before playback, not only at startup.
- Handbrake state is checked both before answer resolution and immediately
  before playback.
- Manual takeover, hard-disable, and auto-answer-off are authoritative; neither
  classifier output nor LLM wording can override them.
- When a trusted call-control daemon owns hotkeys, local `saymo auto` hotkeys
  should be disabled through the Phase 38 seam to avoid duplicate delivery.

#### Decision Evidence

- Decision reasons should be small stable labels such as
  `launch-readiness-blocked`, `response-cache-hit`, `cache-miss-blocked`,
  `fallback-blocked`, `provider-blocked`, `handbrake-blocked`,
  `manual-standup-requested`, `addressing-skip`, and `deterministic-skip`.
- Evidence must preserve operational facts and paths, but not the raw transcript
  window or generated answer text.
- Phase 39 should add enough local tests/events for Phase 40 scorecards and
  safety-soak to consume later, without building the Phase 40 reporting layer.

### Claude's Discretion

No explicit `Claude's Discretion` section exists in `39-CONTEXT.md`. Use the
suggested module boundaries there and the existing repo patterns.

### Guardrails

- Do not synthesize or play generated fallback audio automatically on a cache
  miss in Phase 39.
- Do not move provider repair, audio route mutation, or Chrome destructive
  actions into realtime startup.
- Do not weaken manual takeover, hard-disable, auto-answer-off, or
  deterministic addressing gates.
- Do not store raw transcripts, generated answers, daily-note content, audio
  bytes, or secrets in realtime decision evidence.
- Do not change the Phase 38 daemon into the realtime owner; the daemon remains
  control-plane only.

### Deferred Ideas (OUT OF SCOPE)

- Phase 40 will turn realtime decision events into richer artifacts,
  scorecards, and safety-soak gates.
- Guarded live LLM/TTS fallback remains future work after latency, approval,
  source-grounding, and voice-quality evidence justify it.
- Automatic provider repair remains future work behind explicit commands and
  provider-specific tests.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REAL-01 | Start realtime only after launch-readiness passes for profile, provider, cloned voice, cache, handbrake, and audio route. | Use `collect_launch_readiness()` before any `_auto` capture/STT/provider/hotkey setup. |
| REAL-02 | Preserve `saymo auto` while sharing the same gate as any realtime alias. | Keep `auto` as primary command; route aliases through the same helper, not copied checks. |
| REAL-03 | Automatic handling fails closed on cache miss, stale metadata, unsafe fallback, provider loss, takeover, hard-disable, or auto-answer-off. | Replace automatic fallback behavior with `realtime_policy` blocked decisions and provider/handbrake pre-play checks. |
| REAL-04 | Manual prepared standup playback remains explicit and allowed when safe. | Keep `manual_speak`/`speak` path separate from automatic question cache miss. |
| REAL-05 | Show sanitized spoke/skipped/blocked decision reasons. | Add small stable labels/events; do not write transcript, generated answer, or audio evidence. |
| REAL-06 | Deterministic addressing and handbrake remain safety boundary. | Existing addressing skip runs before classifier; make that ordering explicit and tested. |
</phase_requirements>

## Summary

Phase 39 should not introduce new libraries or new realtime ownership. The
standard implementation is to add two small analysis helpers and integrate them
into `saymo.commands.core`: `saymo.analysis.realtime_gate` for startup gating
with the existing `LaunchReadinessReport`, and `saymo.analysis.realtime_policy`
for response-cache-only automatic decisions and sanitized decision events.

The current `_auto()` path has the right broad shape but uses local prechecks
instead of the shared gate, constructs `ResponseCache` without voice metadata,
and still allows live LLM/TTS or prepared standup fallback after a cache miss.
The current `_play_cached_audio()` also rechecks provider tab state but falls
back to direct BlackHole playback if provider mute automation fails before
playback. Phase 39 must make those automatic paths block instead.

**Primary recommendation:** Wrap `saymo auto` at the very top of `_auto()` with
a shared launch gate, then change automatic response resolution to return
`speak` only for metadata-current response-cache hits and `block/skip` for
every other automatic path.

## Standard Stack

### Core

| Library/Module | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Python | 3.12.1 verified by `uv run python --version` | Runtime and async orchestration | Existing project runtime, compatible with `requires-python >=3.11`. |
| `saymo.analysis.launch_readiness` | repo-local | Shared launch gate contract and remediation rendering | Already covers daily note, prepared audio, response cache, cloned voice, provider/audio, and call-control rows. |
| `saymo.analysis.response_cache` | repo-local | Prepared response-cache lookup and metadata-aware variant readiness | Existing cache abstraction; do not duplicate path or stale checks. |
| `saymo.analysis.live_control` | repo-local | Handbrake state, queued commands, sanitized audit payloads | Existing control-plane contract for auto-answer, takeover, hard-disable, and command correlation. |
| `click` | 8.3.2 verified via `importlib.metadata.version` | CLI command wiring | Existing command framework. |
| `rich` | 15.0.0 verified via `importlib.metadata.version` | Human CLI rendering | Existing console output style. |

### Supporting

| Library/Module | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `pytest` | 9.0.3 verified by `uv run pytest --version` | Phase and regression tests | All Phase 39 behavior should be covered with focused unit/CLI tests. |
| `sounddevice` | 0.5.5 verified via `importlib.metadata.version` | Safe device setting probes in readiness | Use only through existing readiness helpers for launch checks; do not add playback/recording probes to Phase 39. |
| `saymo.analysis.provider_audio_readiness` | repo-local | Provider tab and route checks | Use `collect_launch_readiness()` for startup; for immediate pre-play provider drift, use only provider `check_ready()` style checks. |
| `saymo.analysis.launch_agent` / `control_daemon` | repo-local | LaunchAgent heartbeat and daemon status | Reuse call-ready rows; do not make daemon own realtime audio. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct `collect_launch_readiness()` call | Shell out to `saymo call-ready` | Subprocess would complicate tests, config mutation, and structured access to blockers. |
| New response matching engine | Modify `ResponseCache.lookup()` only | `ResponseCache` should stay cache-focused; policy belongs in a realtime helper that can express blocked decisions. |
| Add evidence to `append_control_audit()` | Add new live-control action names | Existing audit action normalization rejects unknown actions; use a small separate sanitized realtime decision JSONL or extend audit deliberately later. |
| Disable intent classifier entirely | Keep classifier as cache-key selector | Classifier can remain only after deterministic addressing says answer, and only if it returns a prepared cached variant; it must never generate or override a skip. |

**Installation:**
```bash
uv sync
```

**Version verification:**
```bash
uv run python --version
uv run pytest --version
uv run python -c "from importlib.metadata import version; print(version('click'), version('rich'), version('sounddevice'))"
```

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
├── analysis/
│   ├── realtime_gate.py      # startup gate, blocked launch rendering, provider pre-play probe
│   ├── realtime_policy.py    # response-cache-only decisions and sanitized event schema
│   ├── launch_readiness.py   # existing shared source of truth
│   ├── response_cache.py     # existing cache lookup/metadata readiness
│   └── live_control.py       # existing handbrake/control state
├── commands/
│   └── core.py               # thin integration into auto/manual playback loop
└── tests/
    ├── analysis/test_realtime_gate.py
    ├── analysis/test_realtime_policy.py
    ├── test_auto_qa_flow.py
    └── test_call_ready_cli.py
```

### Pattern 1: Shared Launch Gate Before Any Realtime Setup

**What:** Resolve provider, call `collect_launch_readiness()`, render the same
grouped remediation when blocked, and return before cached audio checks,
`find_device`, provider construction, `AudioCapture`, `LocalWhisper`,
response-cache setup, TTS warmup, local hotkey registration, or command loops.

**When to use:** At the top of `_auto()` after `meeting` and provider name are
known. The `--mic` mode mutates `config.audio.capture_device` in `auto()` before
`_auto()`, so the shared gate will validate the selected test input too.

**Example:**
```python
# Source: saymo/analysis/launch_readiness.py and saymo/commands/core.py
gate = evaluate_realtime_launch_gate(config, profile=profile, provider_name=provider_name)
if not gate.allowed:
    console.print(render_launch_readiness(gate.report), markup=False, soft_wrap=True)
    console.print("realtime: blocked (launch-readiness-blocked)")
    return
```

### Pattern 2: Cache-Only Automatic Decision

**What:** A deterministic addressed question may speak only when a
metadata-current cached response variant exists. Cache miss, disabled cache,
not-question-shaped transcript, stale metadata, selector block, and live
fallback all return a blocked/skipped decision.

**When to use:** Replace the automatic branch that currently calls
`_resolve_auto_response_decision()` and then always plays `decision.audio_path`.
Manual `force_speak` uses a separate manual-prepared decision label.

**Example:**
```python
# Source: saymo/commands/__init__.py currently falls back; Phase 39 should not.
decision = await resolve_realtime_response_decision(
    config,
    transcript_window=transcript_window,
    response_cache=response_cache,
    force_manual_standup=force_speak,
    prepared_standup_path=cached_audio,
)
if decision.outcome != "speak":
    append_realtime_decision_event(profile, decision.to_event())
    detector.reset_cooldown()
    continue
```

### Pattern 3: Two Handbrake Checks And One Provider Recheck

**What:** Check handbrake before response resolution and again immediately
before playback. Recheck provider readiness immediately before playback and
block on loss or check errors. Do not rely only on startup readiness.

**When to use:** In `_trigger_loop()` before resolving an automatic answer,
after pre-speak delay, and before creating the playback task.

**Example:**
```python
# Source: existing _automatic_speaking_allowed() and provider.check_ready() use.
block = automatic_handbrake_block(auto_answer_enabled, manual_takeover, hard_disabled)
if block:
    emit_block("handbrake-blocked", block)
    continue

provider_block = provider_playback_block(provider)
if provider_block:
    emit_block("provider-blocked", provider_block)
    continue
```

### Pattern 4: Sanitized Decision Events

**What:** Emit only stable labels and bounded metadata: `profile`, `provider`,
`outcome`, `label`, `source`, `intent_key`, `confidence`, `automatic`, and
optional sanitized artifact/log paths. Never include raw transcript,
`cached.text`, generated answer, daily-note body, audio bytes, or secrets.

**When to use:** For every spoke/skipped/blocked realtime decision. This is a
minimal event seam for Phase 40; do not implement scorecard/safety-soak
reporting here.

### Anti-Patterns to Avoid

- **Duplicating call-ready checks in `_auto()`:** use `collect_launch_readiness()` so Phase 36-38 blockers stay authoritative.
- **Returning prepared standup for automatic cache miss:** this is the exact unsafe fallback Phase 39 is closing.
- **Calling `answer_question()`, `get_selected_tts_engine()`, or `synthesize()` from automatic response policy:** live LLM/TTS fallback is future work.
- **Letting `_play_cached_audio()` recover by playing without provider mute control on automatic paths:** provider automation failure before playback is an unsafe fallback.
- **Writing transcript or answer text into decision evidence:** tests should grep for raw/private field names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Launch readiness | New ad hoc `_auto` preflight checks | `collect_launch_readiness()` + `render_launch_readiness()` | Existing checks include source, cache, cloned voice, provider/audio, and daemon state. |
| Response cache freshness | Manual file exists checks | `ResponseCache(..., voice_metadata=build_voice_cache_metadata(...))` and `response_cache_coverage()` | Metadata sidecars already encode stale voice/cache reasons. |
| Voice approval | Engine-name heuristics | `resolve_voice_selector()` through launch/cache helpers | Selector owns cloned voice approval policy. |
| Handbrake state | New globals or temp files | Existing asyncio events plus `LiveControlSnapshot`/command queue | Existing state has command/audit semantics and daemon integration. |
| Provider readiness | Custom Chrome scripts in realtime gate | Existing provider factory + `provider.check_ready()` | Provider classes already sanitize readiness and Phase 37 proved non-destructive checks. |
| Evidence redaction | Inline string replacements per caller | Small event schema with allowed fields only | Allowlist schema is safer than post-hoc redaction. |

**Key insight:** Fail-closed behavior is a policy layer over existing contracts,
not a new audio/control subsystem.

## Common Pitfalls

### Pitfall 1: Gate Runs Too Late

**What goes wrong:** `AudioCapture`, Whisper, provider control, TTS warmup, or
hotkeys start before readiness blockers are known.
**Why it happens:** Existing `_auto()` starts with local file/device/provider
checks and creates runtime objects after those checks.
**How to avoid:** Put the new gate at the top of `_auto()`, before line-level
equivalents of cached audio, `find_device`, `get_provider`, `AudioCapture`, and
`LocalWhisper`.
**Warning signs:** Tests need to monkeypatch capture/STT constructors as
forbidden when readiness is blocked.

### Pitfall 2: ResponseCache Ignores Voice Metadata At Runtime

**What goes wrong:** A file exists and plays even though its cloned-voice
sidecar is stale.
**Why it happens:** Current `_auto()` constructs `ResponseCache` without
`voice_metadata`, so `_variant_ready()` treats existence as enough.
**How to avoid:** Build runtime cache with
`build_voice_cache_metadata(config, purpose="response_cache")`.
**Warning signs:** A stale sidecar cache variant returns a cache hit in tests.

### Pitfall 3: Standup Fallback Survives In Automatic Path

**What goes wrong:** A question cache miss speaks prepared standup audio.
**Why it happens:** Current `_resolve_auto_response_decision()` returns
`standup_fallback` or `standup` for misses, disabled cache, and non-question
text.
**How to avoid:** For automatic decisions, return `cache-miss-blocked`,
`response-cache-disabled-blocked`, `fallback-blocked`, or `addressing-skip`
without an audio path. Reserve prepared standup for explicit manual speak.
**Warning signs:** Existing tests expecting fallback paths must be updated to
expect blocked decisions.

### Pitfall 4: Provider Loss Falls Back To Direct Playback

**What goes wrong:** Provider mute automation fails and Saymo still plays to
BlackHole automatically.
**Why it happens:** `_play_cached_audio()` catches provider mute-flow
exceptions and calls direct playback if nothing has played yet.
**How to avoid:** Add a strict automatic playback mode or wrapper that returns
`provider-blocked`/`fallback-blocked` instead of direct playback fallback.
**Warning signs:** Tests patch `play_audio_bytes` and provider mute failure;
automatic path still calls playback.

### Pitfall 5: Decision Events Leak Private Text

**What goes wrong:** Evidence contains transcript windows, cached answer text,
generated answer text, daily-note content, or audio bytes.
**Why it happens:** Existing console output prints transcript text and cached
response text during auto Q&A.
**How to avoid:** Realtime decision events should be allowlisted labels only;
automatic console decision labels should avoid `cached.text` and generated
answers.
**Warning signs:** Static guard finds `transcript_window`, `answer_text`, or
`audio_bytes` in `realtime_policy.py` or `realtime_gate.py`.

## Code Examples

Verified patterns from repo sources:

### Launch Gate Report

```python
# Source: saymo/analysis/launch_readiness.py
report = collect_launch_readiness(
    config,
    profile=profile,
    provider_name=provider_name,
    prepare=False,
)
if not report.ready:
    render_launch_readiness(report)
```

### Metadata-Aware Response Cache

```python
# Source: saymo/analysis/response_cache.py and saymo/analysis/launch_cache.py
cache = ResponseCache(
    library=build_library(config.responses.library),
    cache_dir=cache_dir,
    confidence_threshold=config.responses.confidence_threshold,
    voice_metadata=build_voice_cache_metadata(config, purpose="response_cache"),
)
cached = cache.lookup(transcript_window)
```

### Manual Speak Remains Explicit

```python
# Source: saymo/commands/core.py
result = _request_manual_speak(
    triggered,
    manual_speak,
    speaking,
    manual_takeover,
    hard_disabled,
)
```

### Sanitized Payload Allowlist

```python
# Source: saymo/analysis/live_control.py
payload = {
    "outcome": decision.outcome,
    "label": decision.label,
    "source": decision.source,
    "intent_key": decision.intent_key,
    "confidence": decision.confidence,
}
```

## State of the Art

| Old Approach | Current Approach For Phase 39 | When Changed | Impact |
|--------------|-------------------------------|--------------|--------|
| `_auto()` local cached-audio/device/provider checks | Shared `collect_launch_readiness()` gate | Phase 39 | One source of truth for launch blockers. |
| Automatic cache miss falls back to standup or live LLM/TTS | Automatic cache miss blocks | Phase 39 | No unapproved speech on unknown question. |
| Runtime cache only checks files exist | Runtime cache checks voice metadata | Phase 39 | Stale cloned-voice cache cannot speak. |
| Provider checked at startup and inside playback helper | Provider rechecked immediately before playback, with strict automatic failure | Phase 39 | Provider drift blocks before audio starts. |
| Classifier can assist after deterministic yes | Classifier cannot override deterministic skip/handbrake | Already intended; Phase 39 tests it | Safety boundary remains deterministic. |

**Deprecated/outdated:**
- `standup_fallback` as automatic response source: replace with
  `cache-miss-blocked` or `fallback-blocked`.
- Live fallback warmup in automatic path: skip unless a future explicit mode is
  added outside Phase 39.
- Automatic path console/evidence that includes answer text: use labels only.

## Open Questions

1. **Should intent_classifier stay enabled for automatic cache selection?**
   - What we know: It only selects a cache key and does not synthesize audio when a cached variant exists.
   - What's unclear: It still sends the transcript window to the local LLM and could be considered beyond strict deterministic policy.
   - Recommendation: Allow it only after deterministic addressing says answer, only for cached variant lookup, and block on miss; add tests proving deterministic skip never calls it.

2. **Should `saymo auto --mic` require the same full launch gate?**
   - What we know: The context says no casual unsafe bypass in Phase 39.
   - What's unclear: `--mic` is currently described as a test trigger path.
   - Recommendation: Gate it too; because `auto()` mutates the capture device before `_auto()`, the shared gate validates the selected mic path.

3. **Should Phase 39 add a `saymo realtime` alias?**
   - What we know: No alias exists today; requirement only says any alias must share the gate.
   - What's unclear: Whether the product needs a new command now.
   - Recommendation: Keep `saymo auto` primary. If an alias is added, make it a thin wrapper over the same start helper and test both command names with one mocked gate.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` dependency group only; no pytest config detected |
| Quick run command | `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REAL-01 | Blocked shared launch readiness exits before capture/STT/provider/hotkeys; passed readiness continues. | unit/CLI | `uv run pytest tests/analysis/test_realtime_gate.py tests/test_auto_qa_flow.py -q` | ❌ Wave 0 |
| REAL-02 | `saymo auto` and any alias call the same launch gate helper. | CLI | `uv run pytest tests/test_auto_qa_flow.py -q` | ✅ extend |
| REAL-03 | Automatic cache hit speaks; cache miss, stale metadata, fallback, provider loss, takeover, hard-disable, and auto-answer-off block. | unit | `uv run pytest tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q` | ❌ Wave 0 |
| REAL-04 | Manual prepared standup playback remains explicit and does not satisfy automatic cache miss. | unit | `uv run pytest tests/test_auto_qa_flow.py -q` | ✅ extend |
| REAL-05 | Decision labels/events are sanitized and stable. | unit/static | `uv run pytest tests/analysis/test_realtime_policy.py -q` | ❌ Wave 0 |
| REAL-06 | Deterministic addressing skip and handbrake state cannot be overridden by classifier/LLM. | unit | `uv run pytest tests/test_auto_qa_flow.py tests/analysis/test_realtime_policy.py -q` | ✅ extend / ❌ new |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/test_auto_qa_flow.py -q`
- **Per wave merge:** `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q`
- **Phase gate:** `uv run pytest` plus static guards from `39-VALIDATION.md`

### Wave 0 Gaps

- [ ] `tests/analysis/test_realtime_gate.py` - covers REAL-01, provider pre-play block labels, and launch remediation reuse.
- [ ] `tests/analysis/test_realtime_policy.py` - covers REAL-03, REAL-05, REAL-06 cache/blocked/sanitized decisions.
- [ ] `tests/test_auto_qa_flow.py` updates - existing fallback expectations must change to fail-closed expectations and manual speak preservation.
- [ ] Static guard commands from `39-VALIDATION.md` - fail-closed, privacy, and provider/audio mutation scans.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-CONTEXT.md` - locked design direction, guardrails, deferred ideas.
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-VALIDATION.md` - required validation commands and done criteria.
- `saymo/analysis/launch_readiness.py` - shared readiness report, renderer, Phase 36-38 collector order, call-control rows.
- `saymo/analysis/launch_cache.py` - response-cache coverage and cloned-voice metadata launch checks.
- `saymo/analysis/response_cache.py` - metadata-aware cache lookup and coverage behavior.
- `saymo/analysis/provider_audio_readiness.py` - read-only provider/audio readiness and provider tab checks.
- `saymo/analysis/live_control.py` and `saymo/analysis/control_daemon.py` - handbrake state, command queue, sanitized control payloads, heartbeat/probe.
- `saymo/commands/core.py` and `saymo/commands/__init__.py` - current auto startup sequence, response resolution, playback helper, manual speak and handbrake helpers.
- `tests/test_auto_qa_flow.py`, `tests/test_call_ready_cli.py`, `tests/test_takeover_check.py` - existing seams and regression coverage.
- `pyproject.toml` and local `uv run ...` commands - version and test framework verification.

### Secondary (MEDIUM confidence)

- `.planning/phases/36-call-ready-preflight-and-cache-gate/*-SUMMARY.md`, `37-VERIFICATION.md`, `38-VERIFICATION.md` - prior phase decisions and verification evidence.
- `CLAUDE.md` and AGENTS instructions - repo conventions and local-by-default constraints.

### Tertiary (LOW confidence)

- None. No web research was used by request; this phase is repo-local design.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from `pyproject.toml`, `uv run`, and repo modules.
- Architecture: HIGH - direct source inspection shows exact startup, policy, provider, and handbrake seams.
- Pitfalls: HIGH - based on current tested behavior and validation contract.

**Research date:** 2026-07-08
**Valid until:** 2026-08-07 or until `saymo/commands/core.py`, `saymo/commands/__init__.py`, or launch-readiness modules change materially.

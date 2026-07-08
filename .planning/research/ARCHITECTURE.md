# Architecture Research: Saymo v1.9 Call Launch Readiness

**Domain:** Local macOS live-call assistant readiness and realtime control loop
**Researched:** 2026-07-08
**Confidence:** HIGH for existing integration points, MEDIUM for daemon/LaunchAgent details until implemented on a live macOS session

## Executive Recommendation

v1.9 should integrate as a readiness and control layer around the current
Saymo runtime. Do not build a second realtime call stack. The existing
architecture already has the right seams:

- `saymo.commands.core._auto()` owns the live capture -> STT -> trigger ->
  response -> playback loop.
- `saymo.commands.tests._collect_auto_preflight()` owns most readiness checks,
  but it currently lives in a CLI module and should be extracted into a shared
  analysis module.
- `saymo.analysis.live_control` owns the file-backed command/state/audit bus
  under `~/.saymo/live_control/<profile>/`.
- `saymo.providers.*` owns Chrome-tab provider automation.
- `saymo.analysis.cache_metadata`, `saymo.analysis.response_cache`, and
  `saymo.tts.selector` already enforce voice/cache freshness for call-ready
  audio.
- `saymo.analysis.rehearsal`, `session_scorecard`, `remediation`, and
  `safety_soak` already provide the reliability evidence loop.

The roadmap should build v1.9 in this order: extract shared preflight
contracts, add the one call-ready command, extend provider/launchd readiness,
add the local control daemon as a command producer on the existing live-control
bus, then make the realtime loop consume a strict launch gate and emit runtime
events that scorecard/safety-soak can read.

## Recommended Architecture

### System Overview

```text
User / LaunchAgent / CLI
    |
    | saymo call-ready, saymo auto, saymo call-control-daemon
    v
Command Layer
    |-- saymo.commands.call_launch       NEW: call-ready / call-start / launchd commands
    |-- saymo.commands.core              MOD: auto uses shared readiness + strict response policy
    |-- saymo.commands.tests             MOD: diagnostics delegate to shared readiness modules
    |
    v
Readiness and Control Layer
    |-- saymo.analysis.preflight         NEW: extracted auto-preflight checks
    |-- saymo.analysis.launch_readiness  NEW: one green launch report
    |-- saymo.analysis.live_control      MOD: existing state/command/audit bus
    |-- saymo.analysis.live_events       NEW: runtime decision/event JSONL
    |-- saymo.analysis.remediation       MOD: launch/provider/cache/daemon hints
    |
    v
Runtime Layer
    |-- capture + LocalWhisper + TurnDetector + addressing
    |-- ResponseCache + voice metadata
    |-- TTS selector + cached playback
    |-- provider.unmute_speak_mute()
    |
    v
Local Artifacts
    |-- Obsidian daily note
    |-- ~/.saymo/audio_cache/
    |-- ~/.saymo/audio_cache/responses/
    |-- ~/.saymo/live_control/<profile>/{state,commands,audit,events}.jsonl
    |-- ~/.saymo/rehearsals/
    |-- scorecard / safety-soak JSON
    |-- ~/Library/LaunchAgents/<saymo label>.plist
```

## New vs Modified Components

| Component | Status | Responsibility | Roadmap Notes |
|-----------|--------|----------------|---------------|
| `saymo/analysis/preflight.py` | New extraction | Own typed readiness checks currently implemented by `_collect_auto_preflight`. | Move `PreflightCheck` and collection logic out of `commands/tests.py`. CLI commands should render reports, not own readiness policy. |
| `saymo/analysis/launch_readiness.py` | New | Compose one launch report from daily note, prepared standup audio, response cache, voice metadata, provider, BlackHole devices, hotkeys, daemon heartbeat, and profile tuning. | This is the central v1.9 contract. `call-ready`, `rehearsal`, `call-start`, and safety gates should consume the same result. |
| `saymo/commands/call_launch.py` | New | User-facing commands: `call-ready`, `call-start`, `call-control-daemon`, `launch-agent install/status/start/stop` or equivalent names. | Keep as thin Click wrappers. Register from `saymo/commands/__init__.py`. Avoid adding more production flow into `commands/tests.py`. |
| `saymo/obsidian/daily_notes.py` | Modified | Add `ensure_daily_note(config.obsidian, date)` package helper. | The existing script should delegate to this helper. Avoid a second YAML parser as the source of truth. |
| `scripts/ensure_obsidian_daily_note.py` | Modified | Keep as standalone launchd/script entry point. | Use the package helper or remain a thin compatibility wrapper. |
| `saymo/providers/base.py` | Modified | Extend `MeetingStatus` with readiness details that remediation can consume. | Keep provider interface small, but add structured fields for `detail`, `blockers`, `mic_switch_supported`, and `mic_is_correct` instead of parsing strings. |
| `saymo/providers/_chrome_base.py` and provider modules | Modified | Report Chrome tab state and provider capabilities consistently. | Glip and MTS Link support mic switching; most providers currently return false. That should be an explicit capability, not an ambiguous failure. |
| `saymo/analysis/live_control.py` | Modified | Keep command/state/audit primitives; add daemon heartbeat helpers if needed. | Do not replace the existing file-backed bus. The daemon should write commands and read state through this module. |
| `saymo/analysis/live_events.py` | New | Append sanitized runtime events for launch start/end, preflight summary, cache hit/miss, fallback blocked, playback started/finished, and provider failures. | Keep separate from `audit.jsonl`, which is currently action-oriented and validates action names. |
| `saymo/daemon/call_control.py` or `saymo/call_control_daemon.py` | New | Foreground daemon process run by LaunchAgent. Registers global hotkeys, appends live-control commands, publishes heartbeat/status. | It must not capture call audio, synthesize speech, or execute playback. `auto` remains the only realtime executor. |
| `saymo/platform/launchd.py` | New | Generate, validate, bootstrap, kickstart, stop, and inspect LaunchAgent plist. | Use launchd, not cron. Keep plist generation deterministic and testable with command runner injection. |
| `saymo/commands/core.py` | Modified | `_auto()` calls shared launch gate; response decision can block instead of falling back; runtime emits live events. | Keep capture/STT/provider/playback flow intact. No broad rewrite. |
| `saymo/commands/__init__.py` | Modified | Register new command module. | Small import-only change. |
| `saymo/commands/tests.py` | Modified | `auto-preflight`, `rehearsal`, provider diagnostics delegate to extracted modules. | Do not remove existing commands; keep backwards-compatible CLI. |
| `saymo/config.py` | Modified | Add minimal launch/control/realtime policy fields. | Prefer `LiveConfig` additions and per-profile `meeting.live` overrides before adding many new config trees. |
| `saymo/analysis/rehearsal.py` | Modified | Include launch readiness and realtime strictness checks in artifacts. | Keep transcript sanitization behavior. |
| `saymo/analysis/session_scorecard.py` | Modified | Add launch/realtime/cache metrics from live events. | Preserve current sanitized JSON contract; add optional fields with defaults. |
| `saymo/analysis/safety_soak.py` | Modified | Fail on launch readiness blockers, stale voice/cache metadata, unsafe fallback, and cache miss policies when `would_speak` is true. | Existing voice readiness violations already cover part of this. Extend, do not replace. |
| `saymo/analysis/remediation.py` | Modified | Add hint families for daily note, launchd daemon, provider tab/mic, response cache completeness, permissions. | Reuse the current `RemediationHint` renderer. |

## Component Boundaries

| Boundary | Communication | Rule |
|----------|---------------|------|
| CLI -> analysis | Dataclasses and return values | CLI renders output and exit codes. Readiness policy lives in `saymo.analysis.*`. |
| Launch readiness -> preparation | Function calls into package helpers | `call-ready --prepare` may create daily note and run preparation. Dry checks should not mutate. |
| Daemon -> live loop | `commands.jsonl` and `state.json` | Daemon queues commands; `_auto()` consumes commands and writes authoritative state. |
| Runtime -> evidence | `events.jsonl` plus existing `audit.jsonl` | Runtime events capture automatic decisions. Audit remains for operator/control actions. |
| Provider readiness -> remediation | Structured `MeetingStatus` fields | Avoid string matching for provider blockers where possible. |
| Response cache -> realtime | `AutoResponseDecision` result | Strict launch mode blocks cache misses instead of silently playing generic standup audio. |
| Voice selector/cache metadata -> launch gate | Existing metadata checks | Reuse `build_voice_cache_metadata` and `check_voice_cache_metadata`; do not invent a second voice-readiness mechanism. |

## Data Flows

### 1. Call-Ready Flow

```text
saymo call-ready -p personal [--prepare]
    |
    v
load_config()
    |
    v
launch_readiness.collect(profile)
    |-- ensure_daily_note()                 optional mutation
    |-- prepared standup cache check        existing audio cache + metadata
    |-- prepare / prepare-responses         optional mutation
    |-- response cache completeness         ResponseCache + voice metadata
    |-- voice selector readiness            live_call purpose
    |-- audio devices                       capture/playback/BlackHole
    |-- provider readiness                  provider.check_ready()
    |-- hotkey readiness                    effective_hotkey_bindings()
    |-- daemon/LaunchAgent status           heartbeat + launchctl status
    v
LaunchReadinessReport
    |-- ready / not ready
    |-- blocking checks
    |-- warning checks
    |-- exact rerun/remediation commands
```

This flow should be the single operator-facing source of truth before a call.
`auto-preflight` can remain as a lower-level diagnostic, but roadmap phases
should treat `call-ready` as the product workflow.

### 2. Realtime Start Flow

```text
saymo call-start -p personal
    |
    v
launch_readiness.collect(strict=True)
    |
    | if blockers -> print remediation, exit nonzero, do not start capture
    v
core._auto(config, model, profile, launch_report=...)
    |
    | capture -> STT -> trigger -> addressing
    v
resolve_auto_response_decision(strict_cache=True)
    |-- response cache hit -> cached WAV
    |-- cache miss -> block + event
    |-- unsafe live fallback -> block + event
    v
provider.unmute_speak_mute(_play_cached_audio)
    |
    v
live_events.append(...)
```

The existing `saymo auto` currently falls back to prepared standup audio on a
question-shaped cache miss when live fallback is disabled. That is acceptable
legacy behavior, but v1.9 call launch readiness should introduce strict mode
for the call-start path: a cache miss or unapproved fallback becomes a blocked
decision, not generic playback.

### 3. Local Control Daemon Flow

```text
LaunchAgent
    |
    v
saymo call-control-daemon -p personal
    |-- registers global hotkeys
    |-- writes heartbeat/status
    |-- appends commands.jsonl entries
    |-- reads state.json for status
    v
~/.saymo/live_control/personal/
    |-- commands.jsonl      command queue
    |-- state.json          authoritative state from auto
    |-- audit.jsonl         operator action audit
    |-- daemon.json         daemon heartbeat/capabilities
    |-- events.jsonl        runtime launch/realtime events
    |
    v
saymo auto / call-start
    |-- reads commands after startup offset
    |-- applies actions
    |-- writes state and audit
```

Important boundary: the daemon is a control-plane process only. It must not
attempt to speak, capture audio, transcribe, or own provider mute state. That
keeps the live loop single-owner and prevents duplicate playback paths.

### 4. Evidence Flow

```text
rehearsal / realtime run
    |
    | writes checks, live-control audit, live events
    v
session-scorecard
    |-- launch readiness metrics
    |-- cache hit/miss counts
    |-- fallback blocked counts
    |-- provider failures
    |-- handbrake actions
    v
safety-soak
    |-- fails on unsafe playback
    |-- fails on strict cache miss with would_speak
    |-- fails on stale/unapproved voice/cache metadata
    |-- compares drift
```

The scorecard should stay sanitized. Store event types, timings, keys, and
blocker names. Do not store raw private transcript windows beyond existing
sanitized snippets.

## Config Shape

Keep config additions small and close to existing concepts:

```python
@dataclass
class LiveConfig:
    chunk_seconds: float = 4.0
    overlap_seconds: float = 2.0
    read_timeout_seconds: float = 3.0
    trigger_cooldown_seconds: float = 45.0
    silence_rms_threshold: float = 0.001
    pre_speak_delay_seconds: float = 2.0
    require_launch_readiness: bool = True
    fail_on_cache_miss: bool = True
    runtime_events: bool = True


@dataclass
class CallControlConfig:
    enabled: bool = True
    heartbeat_timeout_seconds: float = 10.0
    launch_agent_label: str = "com.saymo.call-control"
```

Add `call_control: CallControlConfig` to `SaymoConfig` only if daemon settings
need global config. Per-profile differences should use the existing
`MeetingProfile.live` override mechanism where possible.

## Patterns to Follow

### Pattern 1: Shared Check Contracts

**What:** Use one dataclass for readiness checks across `call-ready`,
`auto-preflight`, `rehearsal`, scorecard, and safety-soak.

**Why:** Current preflight checks are useful but trapped in
`saymo.commands.tests`. Moving them to `saymo.analysis.preflight` avoids
duplicated readiness policy.

**Recommended shape:**

```python
@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    ok: bool
    detail: str
    blocking: bool = True
    category: str = "retest"
    remediation: str = ""
    rerun: str = ""
```

### Pattern 2: File-Backed Control Bus

**What:** Continue using append-only JSONL commands and JSON state files under
`~/.saymo/live_control/<profile>/`.

**Why:** It already lets terminal UI, scriptable CLI actions, hotkeys, and the
live loop communicate without a socket server. A LaunchAgent daemon can join
this bus with low blast radius.

**Rules:**

- `commands.jsonl`: command producers append; `_auto()` consumes from startup
  offset.
- `state.json`: `_auto()` remains authoritative writer.
- `audit.jsonl`: operator/control actions only.
- `events.jsonl`: automatic runtime decisions and launch health.
- `daemon.json`: daemon heartbeat and capabilities.

### Pattern 3: Strict Runtime Decision

**What:** Change response resolution from "always return an audio path" to a
decision that may block.

**Why:** v1.9 requires the realtime meeting loop to fail closed on cache miss
or unsafe fallback. The current `AutoResponseDecision` can be extended without
rewriting the loop.

**Recommended shape:**

```python
@dataclass(frozen=True)
class AutoResponseDecision:
    allowed: bool
    audio_path: Path | None
    source: str
    reason: str
    blocked_reason: str = ""
```

Legacy `saymo auto` can keep fallback behavior by passing
`strict_cache=False`; `call-start` should pass `strict_cache=True`.

### Pattern 4: LaunchAgent as Process Manager Only

**What:** LaunchAgent starts and restarts the control daemon, not the realtime
meeting loop.

**Why:** The user should choose when call capture starts. The always-on piece
is the handbrake/control plane, not transcription or audio playback.

**Implementation boundary:**

- LaunchAgent command: `saymo call-control-daemon -p <profile>`.
- Status command checks `launchctl`, plist existence, process liveness, and
  `daemon.json` heartbeat.
- No cron. No background capture. No hidden auto-answer.

## Anti-Patterns to Avoid

### Anti-Pattern 1: A Parallel Realtime Loop

**What goes wrong:** New launch command implements its own capture, STT,
provider playback, or hotkey state.

**Consequence:** Trigger decisions, handbrake semantics, cache policy, and
scorecard evidence diverge.

**Instead:** Make `call-start` run the shared readiness gate and then invoke
the existing `_auto()` executor with stricter policy.

### Anti-Pattern 2: Daemon Executes Playback

**What goes wrong:** The LaunchAgent process tries to stop/start playback,
switch provider mics, or synthesize speech.

**Consequence:** Two processes can fight over provider mute state and the
operator loses a clear safety boundary.

**Instead:** Daemon only appends commands and publishes heartbeat. `_auto()`
applies commands and writes authoritative state.

### Anti-Pattern 3: Reusing the Standalone Daily-Note Parser as Core Logic

**What goes wrong:** `scripts/ensure_obsidian_daily_note.py` parses YAML
separately from `load_config()`.

**Consequence:** Call-ready and launchd behavior can diverge from normal CLI
config.

**Instead:** Put `ensure_daily_note()` in `saymo.obsidian.daily_notes` and make
the script a wrapper.

### Anti-Pattern 4: Treating Partial Response Cache as Ready

**What goes wrong:** Preflight reports ready when only one response-cache
variant exists.

**Consequence:** Strict realtime Q&A can hit an unprepared intent and either
fall back incorrectly or block during the call.

**Instead:** For `call-ready --prepare` and `call-start`, require all configured
variants or at least one valid variant per enabled intent, with the rule stated
in the readiness report. Keep lower-level `auto-preflight` warnings
nonblocking if backwards compatibility needs it.

### Anti-Pattern 5: String-Only Provider Failures

**What goes wrong:** Provider readiness is inferred from printed text such as
"tab not found" or "mic switch failed".

**Consequence:** Remediation becomes brittle and provider-specific.

**Instead:** Extend `MeetingStatus` with structured details and provider
capabilities.

## Suggested Phase Order

1. **Shared Readiness Contracts**
   - Extract `PreflightCheck` and `_collect_auto_preflight` into
     `saymo.analysis.preflight`.
   - Add `ReadinessCheck`/`LaunchReadinessReport`.
   - Add package-level `ensure_daily_note()` and make the script delegate.
   - Tests: pure unit tests with temp config, fake caches, fake providers.

2. **One Call-Ready Command**
   - Add `saymo call-ready -p <profile> [--prepare]`.
   - It checks/creates the daily note, optionally runs existing prepare and
     response-cache build, validates voice/cache metadata, and prints only
     actionable blockers.
   - Tests: CLI with monkeypatched `_prepare`, `_prepare_responses`, devices,
     provider, and temp Obsidian vault.

3. **Provider and Remediation Readiness**
   - Extend `MeetingStatus` and provider readiness details.
   - Add remediation hints for Chrome tab, mic switch unsupported, BlackHole
     routing, permissions, stale provider tab, and provider latency history.
   - Tests: provider fake objects and remediation rendering.

4. **Control Daemon and LaunchAgent**
   - Add foreground `call-control-daemon` that writes heartbeat and appends
     commands from global hotkeys.
   - Add launchd helper commands to install/status/start/stop the LaunchAgent.
   - Make `hotkey-doctor` understand daemon heartbeat so it no longer assumes
     `saymo auto` must own hotkeys.
   - Tests: no real `launchctl` in unit tests; inject runner and assert plist,
     labels, commands, heartbeat timeout behavior.

5. **Strict Realtime Start**
   - Add `call-start` or make `auto --require-ready` default for the new path.
   - `_auto()` accepts a launch report or calls shared readiness itself.
   - Extend `AutoResponseDecision` to support blocked decisions.
   - Strict mode blocks cache misses and unsafe live fallbacks, then emits a
     runtime event.
   - Tests: cache hit speaks; cache miss blocks; handbrake still blocks; stale
     voice metadata blocks.

6. **Runtime Evidence Integration**
   - Add `live_events.py` and event writes inside launch start, cache
     decisions, provider playback, fallback blocks, and shutdown.
   - Extend rehearsal artifacts and scorecards with launch/cache/provider
     evidence.
   - Safety-soak fails on unsafe fallback, strict cache miss, stale metadata,
     and launch blockers.
   - Tests: scorecard and safety-soak fixtures with sanitized events.

7. **Docs and Operator Runbook**
   - Update `docs/`, `config.example.yaml`, command help, and LaunchAgent
     troubleshooting notes.
   - Document the difference between `call-ready`, `auto-preflight`,
     `call-control-daemon`, and `call-start`.
   - Manual evidence: one local dry run with `call-ready`, daemon status,
     rehearsal, scorecard, and safety-soak.

## Test Boundaries

| Area | Unit Tests | CLI Tests | Manual/Integration Evidence |
|------|------------|-----------|-----------------------------|
| Daily note helper | Temp vault creates/preserves note | `call-ready --prepare` calls helper | Actual Obsidian vault path check |
| Launch readiness | Fake devices/providers/cache metadata | Ready/not-ready output and exit code | Run before real standup |
| Provider readiness | Fake `MeetingStatus` variants | Provider blocker remediation | Chrome tab and BlackHole routing |
| Daemon bus | Temp live-control dir, command offsets, heartbeat | `call-control-daemon --once` or test mode | LaunchAgent bootstrap/kickstart/status |
| Strict response policy | Cache hit/miss decisions | `call-start` blocks on cache miss | Rehearsal with known question |
| Runtime events | JSONL event serialization/sanitization | Scorecard consumes event file | Post-call scorecard |
| Safety soak | Violations from synthetic scorecards/events | Nonzero failure on unsafe fallback | Baseline drift check |

Unit tests should not require Chrome, BlackHole, launchctl, real hotkey
permissions, real TTS, or real Obsidian. Those belong to explicit manual
evidence and provider-latency style probes.

## Roadmap Integration Points

| Existing Feature | v1.9 Integration |
|------------------|------------------|
| `prepare` | Called by `call-ready --prepare`; its prepared audio metadata remains the live-call readiness source. |
| `prepare-responses` | Called by `call-ready --prepare`; strict mode requires response-cache coverage before call start. |
| `auto-preflight` | Delegates to shared preflight. It remains a diagnostic subset of `call-ready`. |
| `rehearsal` | Adds launch readiness and strict response checks to the existing artifact. |
| `session-scorecard` | Reads live events to report launch health, cache hit/miss, provider failures, and fallback blocks. |
| `safety-soak` | Adds v1.9 violations without changing existing trigger/handbrake/voice checks. |
| `live-control` TUI | Continues to read/write the same bus. Daemon is an additional command producer, not a replacement. |
| Provider abstractions | Keep factory and Chrome base. Extend status detail and capabilities only. |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Existing runtime integration | HIGH | `_auto`, response cache, voice metadata, provider playback, and live-control bus were inspected directly. |
| Readiness extraction | HIGH | Current `_collect_auto_preflight` is already close to the desired shared contract. |
| Daily note integration | HIGH | Existing package reader and standalone script can be unified with low risk. |
| Strict cache miss policy | HIGH | Current response decision function is a narrow seam for this change. |
| Daemon and LaunchAgent | MEDIUM | Architecture boundary is clear, but implementation must be verified against macOS permissions and launchctl behavior. |
| Scorecard/safety-soak extension | HIGH | Current sanitized dataclasses and tests already support additive metrics and violations. |

## Sources

- `.planning/PROJECT.md` - v1.9 milestone scope and constraints.
- `saymo/config.py` - config dataclasses, live tuning, meetings, safety, voice selector, response cache.
- `saymo/commands/core.py` - `auto`, `prepare`, `speak`, live-control commands, response resolution, cache metadata gate.
- `saymo/commands/tests.py` - `prepare-responses`, `auto-preflight`, `rehearsal`, `session-scorecard`, `safety-soak`, `provider-latency`, `hotkey-doctor`.
- `saymo/analysis/live_control.py` - action catalog, command/state/audit file bus, hotkey diagnostics.
- `saymo/analysis/remediation.py` - reusable remediation hint renderer and existing hint families.
- `saymo/analysis/rehearsal.py` - sanitized rehearsal artifact contract.
- `saymo/analysis/session_scorecard.py` - sanitized scorecard metrics and live-control audit parsing.
- `saymo/analysis/cache_metadata.py` and `saymo/analysis/response_cache.py` - voice/cache freshness and runtime response-cache contracts.
- `saymo/analysis/safety_soak.py` - current safety invariants and voice-readiness violations.
- `saymo/providers/*` - Chrome provider abstraction and provider-specific mic switching.
- `saymo/obsidian/daily_notes.py` and `scripts/ensure_obsidian_daily_note.py` - daily note read/create integration points.
- Existing tests under `tests/` for preflight, rehearsal, live-control, response cache, provider latency, scorecard, and safety-soak.

---
*Architecture research for: Saymo v1.9 Call Launch Readiness*
*Researched: 2026-07-08*

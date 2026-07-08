# Project Research Summary: Saymo v1.9 Call Launch Readiness

**Project:** Saymo
**Domain:** Local macOS voice assistant call launch, realtime loop readiness,
and local handbrake daemon/control surface
**Researched:** 2026-07-08
**Confidence:** HIGH for repo-local architecture and feature boundaries; MEDIUM
for daemon/LaunchAgent behavior until verified in the user's GUI session

## Executive Summary

v1.9 should make Saymo operationally reliable before a meeting: one command
answers whether the daily note, prepared standup audio, response cache,
approved cloned voice, provider tab, BlackHole routing, hotkeys, and local
control listener are ready. The milestone should not add another realtime
stack. It should extract and reuse existing readiness checks, voice/cache
metadata gates, live-control files, provider abstractions, rehearsal,
scorecard, and safety-soak.

The recommended stack change is small: add a shared launch-readiness contract,
a `saymo call-ready` operator command, a local call-control daemon supervised
by a user LaunchAgent, strict realtime start gates around the existing
`saymo auto` loop, and sanitized launch/realtime events that feed scorecards.
No required third-party dependency is justified for v1.9; use Python stdlib
`plistlib`, `subprocess`, `json`, `pathlib`, existing Click/Rich output, the
existing `pynput` hotkey integration, and the existing file-backed
`~/.saymo/live_control/<profile>/` bus.

The main risk is false confidence. A green launch result must not hide
nonblocking response-cache, daemon, hotkey, provider, or stale-cache warnings
that can lead to unsafe automatic speaking. Realtime mode should fail closed:
cache miss, stale cloned-voice metadata, unsafe fallback, manual takeover,
hard-disable, or provider loss blocks playback and writes evidence instead of
speaking a generic or live-generated answer.

## Key Findings

### Recommended Stack

**Core technologies:**
- Python 3.11+ and existing Click/Rich commands — enough for orchestration,
  daemon, LaunchAgent management, and diagnostics.
- macOS LaunchAgent plus stdlib `plistlib` — correct per-user GUI-session
  supervisor for hotkeys, Chrome automation, logs, and restart/status.
- Existing `pynput` global hotkeys — keep the current hotkey model, but make
  Accessibility and listener reachability explicit readiness checks.
- Existing JSON/JSONL live-control files — use them as local IPC; do not add a
  web server, WebSocket, FastAPI, Electron, or native app framework in v1.9.
- Existing response cache, voice selector, cache metadata, provider
  abstractions, rehearsal, scorecard, and safety-soak — extend them instead of
  duplicating readiness logic.

**No required dependency additions.** If future package resolution is needed,
prefer the internal Nexus PyPI mirror for local installs, but this milestone
does not need new packages.

### Expected Features

**Must have:**
- `saymo call-ready -p <profile>` or equivalent one-shot launch gate that can
  create/check the daily note, prepare standup audio, build response-cache
  variants, validate approved cloned-voice metadata, check provider/audio
  routing, check permissions, check daemon/hotkeys, and report ready/not-ready.
- Structured `block` / `warn` / `info` readiness output with exact remediation
  and rerun commands.
- Response-cache completeness and stale metadata detection before automatic
  realtime Q&A.
- Provider and BlackHole readiness beyond "tab exists": provider tab,
  activation, mic route, takeover path, and provider capability evidence.
- Local call-control daemon/LaunchAgent lifecycle: install/start/stop/status,
  heartbeat, hotkey registration, command queue, and audit continuity.
- Strict realtime start gate around the existing `saymo auto` loop.
- Sanitized launch/realtime event artifacts for scorecard and safety-soak.

**Should have:**
- Minimal menu-bar-adjacent status/actions backed by the daemon and existing
  live-control actions.
- Post-call launch-health scorecard fields: launch pass/fail, provider drift,
  daemon heartbeat, cache hits/misses, unsafe fallback blocks, and handbrake
  actions.
- A clear `saymo realtime` or `saymo call-start` alias only if it shares the
  existing `auto` implementation.

**Defer:**
- Full native menu bar application packaging, settings UI, history dashboard,
  calendar-based auto-launch, automatic provider repair, voice-command
  handbrake, live LLM+TTS fallback, new voice training/downloads, and full
  autonomous meeting participation.

### Architecture Approach

v1.9 should add a readiness/control layer around current runtime ownership:

1. `saymo.analysis.preflight` — extract typed checks from the current
   `auto-preflight` implementation.
2. `saymo.analysis.launch_readiness` — central report composing daily note,
   prepared cache, response cache, voice selector metadata, provider, audio,
   hotkeys, daemon, and profile checks.
3. `saymo.commands.call_launch` — thin Click wrappers for `call-ready`,
   call-start/realtime alias, call-control daemon, and LaunchAgent lifecycle.
4. `saymo.analysis.live_control` — extend existing command/state/audit bus with
   daemon heartbeat helpers; do not replace it.
5. `saymo.platform.launchd` — deterministic LaunchAgent generation and
   `launchctl` status/start/stop helpers.
6. `saymo.commands.core._auto()` — consume launch readiness, enforce strict
   cache/fallback policy, and emit sanitized runtime events.
7. `session-scorecard` and `safety-soak` — consume launch/realtime events and
   fail on unsafe launch or playback conditions.

The daemon is control-plane only. It may register hotkeys, write heartbeat, and
queue live-control actions. It must not capture audio, transcribe, synthesize,
play audio, or own provider mute state; the existing realtime loop remains the
single executor.

### Critical Pitfalls

1. **Green launch with hidden warnings** — define mode-specific blocking rules;
   automatic speaking requires `realtime_ready`, not merely rehearsal-ready.
2. **Cache miss speaks the wrong thing** — automatic question handling blocks
   and audits cache misses; generic standup is manual/explicit only.
3. **Stale voice/cache metadata accepted** — every launch-critical WAV needs
   privacy-safe sidecar metadata and exact stale reason reporting.
4. **False positives become easier to trigger** — keep deterministic
   addressing, handbrake, and safety-soak gates in the realtime path.
5. **Handbrake exists but is unreachable** — daemon readiness must prove
   heartbeat, hotkey registration, command write/consume, and audit evidence.
6. **LaunchAgent works only in terminal assumptions** — use absolute paths,
   explicit environment, GUI `launchctl` domain, logs, and no double-forking.
7. **Provider readiness too shallow** — check tab, activation, mic route,
   takeover, latency, mute recovery, and provider capabilities separately.
8. **Daily note creation masks empty content** — note existence and usable
   standup content are separate checks.
9. **Evidence leaks private call content** — launch/realtime artifacts contain
   statuses, counts, hashes, keys, and decisions, not raw audio/transcripts.

## Implications for Roadmap

### Phase 36: Call-Ready Preflight and Cache Gate

**Rationale:** The user's selected first priority is launch readiness, and all
later realtime work depends on a single trustworthy ready/not-ready contract.
**Delivers:** Shared readiness dataclasses, `saymo call-ready`, daily-note
ensure integration, prepared standup/cache metadata validation, response-cache
coverage, and concise remediation.
**Addresses:** launch orchestration, daily note, prepared cache, response
cache, cloned voice metadata.
**Avoids:** green launch with hidden warnings; stale cache accepted; empty note
treated as useful content.

### Phase 37: Provider and Audio Remediation

**Rationale:** The last observed blocker was provider tab readiness, and a real
call launch cannot stop at "prepared cache exists".
**Delivers:** Provider/Chrome/Glip readiness, BlackHole/capture/playback checks,
permission-oriented blockers, takeover/mic-route verification, and better
remediation hints.
**Addresses:** provider tab, audio route, permissions, mic switching, latency.
**Avoids:** shallow provider readiness and confusing macOS permission failures.

### Phase 38: Local Call-Control Daemon and LaunchAgent

**Rationale:** Live handbrake must survive terminal focus and expose real
listener health before strict realtime can be trusted.
**Delivers:** daemon command, LaunchAgent install/start/stop/status, heartbeat,
hotkey registration status, command queue probe, logs, and status output.
**Addresses:** terminal-independent handbrake and minimal menu-adjacent status.
**Avoids:** stale live-control state and LaunchAgent false positives.

### Phase 39: Fail-Closed Realtime Meeting Loop

**Rationale:** The user's third selected priority is realtime loop, but it
should start only after launch/provider/control gates are real.
**Delivers:** strict launch gate in `saymo auto` or shared call-start alias,
fail-closed cache-miss policy, blocked unsafe fallbacks, provider-loss
handling, handbrake enforcement, and runtime event writes.
**Addresses:** realtime route safety and controlled automatic answering.
**Avoids:** cache miss speaking standup/live fallback and faster false
positives.

### Phase 40: Launch and Realtime Evidence Feedback

**Rationale:** v1.7 already created rehearsal/scorecard/safety-soak. v1.9
should feed launch and realtime failures back into that loop.
**Delivers:** launch artifact schema, scorecard launch-health fields,
safety-soak checks for readiness/fallback/cache/daemon failures, and docs for
the operator workflow.
**Addresses:** post-call confidence and regression prevention.
**Avoids:** "looks done" launch tooling with no evidence that the call stayed
safe.

### Phase Ordering Rationale

- Phase 36 creates the shared contract; without it, other phases duplicate
  checks and disagree about "ready".
- Phase 37 fills the provider/audio gap that currently blocks real preflight.
- Phase 38 makes the control plane reachable outside the terminal before
  strict realtime relies on it.
- Phase 39 changes live behavior only after readiness, provider, and handbrake
  gates exist.
- Phase 40 closes the loop by proving launches and realtime decisions through
  sanitized artifacts and safety-soak.

### Research Flags

- **Phase 38:** verify LaunchAgent behavior in the user's GUI session, including
  Accessibility, logs, and crash/restart behavior.
- **Phase 39:** inspect `_resolve_auto_response_decision()` and `ResponseCache`
  before changing fallback semantics; legacy auto behavior may need a
  compatibility mode.

Phases 36, 37, and 40 mostly use established repo patterns and should not need
external research during phase planning.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing Python/Click/Rich/stdlib/launchd/live-control stack is sufficient. |
| Features | HIGH | User-selected priorities and current blockers map cleanly to one call-ready flow. |
| Architecture | HIGH | Existing seams are clear: preflight, live-control, provider, cache metadata, auto loop, scorecard. |
| Pitfalls | HIGH | Risks are visible from current commands and prior milestones. |
| LaunchAgent runtime | MEDIUM | Must be verified on the user's macOS GUI session with real permissions. |
| Menu-bar specifics | MEDIUM | v1.9 should stay menu-adjacent unless a native framework is chosen later. |

**Overall confidence:** HIGH

## Gaps to Address

- **Command naming:** choose whether strict realtime is `saymo auto` with a
  default gate, a `saymo call-start` wrapper, or a `saymo realtime` alias.
- **Readiness mutability:** define which `call-ready` actions are safe by
  default and which require explicit flags, especially helper restarts and
  audio/provider route changes.
- **Daemon single-instance policy:** define profile-specific labels, stale
  heartbeat TTL, and command consume probe semantics during Phase 38.
- **Legacy fallback compatibility:** preserve older manual/legacy standup
  fallback where useful, but block it for automatic realtime question answers.

## Sources

### Primary

- `.planning/PROJECT.md` — current Saymo milestone context and constraints.
- `.planning/research/STACK.md` — stack and dependency recommendations.
- `.planning/research/FEATURES.md` — feature landscape and priority order.
- `.planning/research/ARCHITECTURE.md` — integration boundaries and data flows.
- `.planning/research/PITFALLS.md` — safety, launchd, provider, cache, and
  privacy failure modes.
- Apple launchd documentation — LaunchAgent behavior and plist constraints.
- Python `plistlib` documentation — deterministic plist generation.
- pynput keyboard documentation — existing global hotkey integration caveats.

---
*Research completed: 2026-07-08*
*Ready for roadmap: yes*

---
phase: 39-fail-closed-realtime-meeting-loop
verified: 2026-07-08T18:10:36Z
status: human_needed
score: 6/6 must-haves verified
human_verification:
  - test: "Live launch gate smoke with the real configured profile/provider"
    expected: "saymo auto blocks with grouped call-ready remediation when any readiness row is unsafe, and starts only after all rows pass."
    why_human: "Real Chrome tab, BlackHole routing, local voice/cache files, and call-control daemon state cannot be fully proven by unit tests."
  - test: "Runtime provider and handbrake smoke during an actual call"
    expected: "Manual takeover, hard-disable, auto-answer-off, provider loss, and provider automation failure block automatic playback before audio starts."
    why_human: "Provider drift and mute/unmute behavior depend on live browser and call-app state."
  - test: "Manual prepared standup route smoke"
    expected: "Explicit manual speak can play prepared standup audio when allowed, while automatic cache miss remains blocked."
    why_human: "End-to-end audio playback and operator hotkey/control timing require a live local runtime."
---

# Phase 39: Fail-Closed Realtime Meeting Loop Verification Report

**Phase Goal:** User can start realtime mode only through the shared launch gate, and automatic speaking fails closed whenever cache, voice, provider, fallback, or handbrake state is unsafe.
**Verified:** 2026-07-08T18:10:36Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

Automated goal-backward verification found no blocking gaps. All six REAL requirements are implemented, wired, and covered by focused and full test suites. Status is `human_needed` only because real Chrome/provider/audio behavior still needs a live-call smoke test before trusting an actual meeting.

Tooling note: `gsd-tools verify artifacts` and `verify key-links` returned `No must_haves...found in frontmatter` for plans 39-01 through 39-05, so artifact and key-link verification below was performed manually against the plan YAML and source.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Realtime starts only after launch-readiness passes for selected profile/provider/cache/cloned voice/handbrake/audio route. | VERIFIED | `evaluate_realtime_launch_gate()` calls `collect_launch_readiness(..., prepare=False)` in `saymo/analysis/realtime_gate.py:34`; `_auto()` checks it before cached-audio stat, device lookup, provider construction, capture/STT, hotkeys, and loops in `saymo/commands/core.py:407`. |
| 2 | Existing `saymo auto` is preserved and any realtime alias shares the same gate. | VERIFIED | `auto` and `realtime` both delegate to `_run_auto_start()` in `saymo/commands/core.py:353`; tests cover alias delegation and no unsafe gate flags in `tests/test_auto_qa_flow.py:727`. |
| 3 | Automatic question handling fails closed on cache miss, stale metadata, unsafe fallback, provider loss, takeover, hard-disable, and auto-answer-off. | VERIFIED | Cache-only policy is in `saymo/analysis/realtime_policy.py:102`; handbrake and provider blockers are in `saymo/commands/core.py:840`, `core.py:1026`, and `core.py:1064`; strict provider fallback is in `saymo/commands/__init__.py:160`. |
| 4 | Explicit manual prepared standup playback is separate from automatic cache-miss fallback. | VERIFIED | Manual route uses `resolve_manual_standup_decision()` in `saymo/analysis/realtime_policy.py:67` and is called only in the `force_speak` branch in `saymo/commands/core.py:992`; automatic cache miss returns `cache-miss-blocked` in `realtime_policy.py:152`. |
| 5 | Decision labels/events are sanitized and expose spoke/skipped/blocked reasons without private content. | VERIFIED | `RealtimeDecisionEvent.to_dict()` allowlists fields in `saymo/analysis/realtime_events.py:58`; `_emit_realtime_event()` appends best-effort events in `saymo/commands/core.py:36`; tests cover event sanitization in `tests/analysis/test_realtime_events.py:30`. |
| 6 | Deterministic addressing and handbrake remain authoritative safety boundaries. | VERIFIED | Deterministic skip returns before cache/classifier in `saymo/analysis/realtime_policy.py:110`; `_trigger_loop()` applies addressing before live assist and response policy in `saymo/commands/core.py:872`; tests assert deterministic skip prevents response resolution in `tests/test_auto_qa_flow.py:1135`. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `saymo/analysis/realtime_gate.py` | Launch gate plus runtime provider/handbrake blockers | VERIFIED | 108 substantive lines; exports `RealtimeLaunchGate`, `evaluate_realtime_launch_gate`, `render_realtime_launch_block`, `RealtimePlaybackBlock`, `automatic_handbrake_block`, and `provider_playback_block`. |
| `saymo/analysis/realtime_policy.py` | Cache-only automatic policy and manual standup decision helper | VERIFIED | 208 substantive lines; builds `ResponseCache` with cloned-voice metadata, blocks fallback/cache misses, and converts decisions to events. |
| `saymo/analysis/realtime_events.py` | Sanitized JSONL event schema and append helper | VERIFIED | 124 substantive lines; allowlisted event payload, bounded text, secret/token redaction, live-control profile path. |
| `saymo/commands/core.py` | Realtime gate/policy/event integration in actual auto loop | VERIFIED | `_auto()` gates before setup; trigger loop blocks handbrake/provider drift; emits decision events; manual route remains explicit. |
| `saymo/commands/__init__.py` | Strict provider fallback option for automatic playback | VERIFIED | `_play_cached_audio(..., allow_provider_fallback=False)` blocks direct fallback when provider automation fails before playback starts. |
| Tests listed in the phase prompt | Regression coverage for gate, policy, events, auto loop, static guards | VERIFIED | Focused suite passed: 96 tests. Safety regression suite passed: 78 tests. Full suite passed: 518 tests. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `realtime_gate.py` | `collect_launch_readiness()` | Startup gate evaluation | WIRED | Imported at `realtime_gate.py:7`; called at `realtime_gate.py:43` with `prepare=False`. |
| `realtime_gate.py` | `render_launch_readiness()` | Blocked remediation rendering | WIRED | Imported at `realtime_gate.py:10`; reused in `render_realtime_launch_block()` at `realtime_gate.py:59`. |
| `core.py` | `evaluate_realtime_launch_gate()` | Top of `_auto()` before realtime setup | WIRED | Called at `core.py:407`; setup starts after blocked return at `core.py:441`. |
| `realtime_policy.py` | `ResponseCache` + `build_voice_cache_metadata()` | Metadata-aware automatic cache | WIRED | `build_realtime_response_cache()` constructs `ResponseCache` with `build_voice_cache_metadata(..., purpose="response_cache")` at `realtime_policy.py:53`. |
| `core.py` | `resolve_realtime_response_decision()` | Automatic trigger response resolution | WIRED | Called only for non-manual automatic triggers at `core.py:1001`; non-speak decisions continue without playback at `core.py:1016`. |
| `core.py` | `automatic_handbrake_block()` | Before resolution and before playback | WIRED | Before response resolution at `core.py:840`; repeated after pre-speak delay at `core.py:1026`. |
| `core.py` | `provider_playback_block()` | Immediate pre-play provider readiness check | WIRED | Called before automatic playback at `core.py:1064`; blocks without `_play_cached_audio()`. |
| `core.py` | `_play_cached_audio()` | Strict automatic provider fallback | WIRED | Automatic decisions pass `allow_provider_fallback=False` via `not response_decision.automatic` at `core.py:1107`. |
| `core.py` | `resolve_manual_standup_decision()` | Explicit force-speak branch | WIRED | Called only when `force_speak` is true at `core.py:992`; automatic cache miss policy never receives standup fallback. |
| `core.py` | `append_realtime_decision_event()` | Launch, skip, block, speak, playback outcomes | WIRED | Best-effort wrapper at `core.py:36`; launch block at `core.py:413`; response decision at `core.py:1008`; provider/playback blocks at `core.py:1066` and `core.py:1153`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| REAL-01 | 39-01 | Start realtime only after launch-readiness passes for profile, provider, cloned voice, cache, handbrake, and audio route. | SATISFIED | Shared launch gate is first safety check in `_auto()`; blocked test prevents any realtime setup. |
| REAL-02 | 39-01 | Preserve `saymo auto` while realtime alias shares same gate. | SATISFIED | `auto` and `realtime` share `_run_auto_start()`; CLI tests cover both. |
| REAL-03 | 39-02, 39-03 | Automatic handling fails closed on cache miss, stale metadata, unsafe fallback, provider loss, takeover, hard-disable, auto-answer-off. | SATISFIED | Cache policy, metadata checks, strict playback, handbrake and provider rechecks all wired and tested. |
| REAL-04 | 39-04 | Manual prepared standup remains explicit and is not automatic cache-miss fallback. | SATISFIED | Manual helper is `automatic=False`; auto cache miss returns block decision and no prepared standup path. |
| REAL-05 | 39-05 | User can inspect sanitized decision labels for spoke/skipped/blocked outcomes. | SATISFIED | `RealtimeDecisionEvent` JSONL schema and event appends are implemented and privacy-tested. |
| REAL-06 | 39-02, 39-05 | Deterministic addressing and handbrake remain safety boundary; classifier/LLM wording cannot override deterministic skip. | SATISFIED | Deterministic skip happens before cache/classifier in policy and before live assist in loop; tests block response resolution on deterministic skip. |

No orphaned Phase 39 requirements found: `.planning/REQUIREMENTS.md` maps only REAL-01 through REAL-06 to Phase 39.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `saymo/commands/__init__.py` | 213 | Legacy `_resolve_auto_response()` still supports standup/live fallback behavior. | Info | Not a Phase 39 blocker: `saymo/commands/core.py` no longer imports or calls this helper, and static guards assert `_resolve_auto_response_decision` and `answer_question(` stay out of `core.py`. Residual regression risk is covered by tests. |

No blocker TODO/FIXME/placeholders, empty implementations, provider/audio mutation in realtime analysis modules, or privacy-dangerous event fields were found.

### Automated Verification

| Command | Result |
|---|---|
| `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py -q` | 96 passed in 3.00s |
| `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q` | 78 passed in 3.67s |
| `uv run pytest -q` | 518 passed in 7.01s |
| Scoped fail-closed, privacy, provider/audio mutation, Phase 40 scope guards | Passed |
| `git diff --check` | Passed |

### Human Verification Required

#### 1. Live Launch Gate Smoke

**Test:** Run `uv run saymo call-ready -p standup --provider glip`, then `uv run saymo auto -p standup` with one deliberately unsafe readiness condition and again after remediation.
**Expected:** Unsafe state prints grouped remediation and exits before realtime setup; ready state starts realtime normally.
**Why human:** Depends on local Chrome, BlackHole devices, voice/cache files, and call-control daemon.

#### 2. Runtime Handbrake And Provider Drift Smoke

**Test:** In a real call, start `saymo auto -p standup`, then toggle auto-answer off, manual takeover, hard-disable, and simulate provider tab loss before a queued answer.
**Expected:** Automatic playback blocks before audio starts and records sanitized labels such as `handbrake-blocked` or `provider-blocked`.
**Why human:** Browser provider state and mute/unmute timing are external runtime behavior.

#### 3. Manual Standup Route Smoke

**Test:** Trigger explicit manual speak from live-control while auto-answer is off, then trigger an automatic question with no response-cache hit.
**Expected:** Manual prepared playback is allowed when takeover/hard-disable/speaking do not block it; automatic cache miss records `cache-miss-blocked` and does not play standup fallback.
**Why human:** Requires live control command timing and actual audio output.

### Gaps Summary

No blocking implementation gaps found. Automated verification supports the Phase 39 goal and REAL-01 through REAL-06. Residual risk is limited to real-device/provider behavior that requires the manual smoke tests above before live-call trust.

---

_Verified: 2026-07-08T18:10:36Z_
_Verifier: Claude (gsd-verifier)_

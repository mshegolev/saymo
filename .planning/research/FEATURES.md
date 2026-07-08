# Feature Research: Saymo v1.9 Call Launch Readiness

**Domain:** Local macOS AI voice assistant for live calls
**Researched:** 2026-07-08
**Confidence:** HIGH for CLI/readiness/cache/handbrake behavior from local docs and code; MEDIUM for native menu-bar specifics because no existing menu-bar implementation was present in the required sources.

## Scope

This research covers only new v1.9 user-facing capabilities. Saymo already has
`prepare`, `speak`, `auto`, response-cache preparation, approved
`f5tts_clone` voice selection, voice/cache metadata gates, `auto-preflight`,
`rehearsal`, `session-scorecard`, `safety-soak`, terminal live-control actions,
global hotkeys, and a daily-note creation script/LaunchAgent.

v1.9 should not feel like more diagnostics to memorize. From the user's
perspective it should answer one operational question before a call:

> Can I join the meeting now with Saymo ready to speak safely, and if not,
> exactly what do I fix?

The milestone should create a single launch-readiness path, make the realtime
loop refuse unsafe starts, and move the handbrake/control state out of a
terminal-only dependency. It should preserve the local-by-default and
fail-closed posture from earlier milestones.

## Feature Landscape

### Table Stakes

Features users should expect in v1.9. Missing these means the milestone does
not actually make launch reliable.

| Feature | Why Expected | Complexity | Notes |
|---|---|---:|---|
| One call-ready command or flow | The user should not run `test-notes`, `prepare`, `prepare-responses`, `auto-preflight`, `hotkey-doctor`, `takeover-check`, and `rehearsal` manually before every call. | HIGH | Recommend a `saymo call-ready -p personal` orchestration entry point. It should run the existing checks in the correct order, create or verify the daily note, prepare standup audio, build response-cache variants, validate voice metadata, check provider/audio/daemon state, and return `ready` or `not ready`. |
| Concise ready/not-ready result | A launch gate that emits a long raw diagnostic dump is not usable five minutes before standup. | MEDIUM | Output should group failures as `block`, `warn`, and `info`, then show the smallest rerun/fix commands. Existing remediation categories should be reused and expanded rather than inventing a new prose format. |
| Daily-note readiness integration | The user already has a daily-note helper; the call-ready path must make note presence boring and reliable. | LOW | If the note is missing and the configured helper/LaunchAgent exists, call-ready should create it or report the exact helper failure. It should not edit unrelated Obsidian content beyond the known daily-note bootstrap/standup summary behavior. |
| Prepared standup cache freshness | `speak` and current `auto` depend on cached prepared audio. v1.9 must prove the cache is for today's profile and approved voice. | MEDIUM | Check cache existence, profile/team mode, voice selector approval, cache metadata fingerprint, generated text freshness, file size, and likely duration. Stale cache is a blocker with `saymo prepare -p <profile>` as remediation. |
| Response-cache coverage gate | Realtime Q&A is only safe when short answers are pre-synthesized in the approved voice. | MEDIUM | Build/check `config.responses.library` variants and voice metadata. A partial cache should be visible as coverage, for example `38/42 variants`. Missing variants are at least warnings; for automatic realtime Q&A they become blockers unless the loop is configured to prepared-standup-only mode. |
| Fail-closed cache miss policy | The user specifically needs the realtime loop to avoid unsafe fallback. | MEDIUM | For v1.9, cache miss during automatic answering should not silently run live LLM+TTS. It should block, skip, or use an explicitly allowed prepared-standup fallback depending on mode. `responses.live_fallback=true` should be treated as an explicit advanced opt-in and surfaced as a readiness warning. |
| Provider and Chrome tab readiness | A prepared voice cache is useless if Glip/Chrome is not in a controllable call state. | MEDIUM | Check provider resolution from profile, Chrome tab found, tab identity, provider mute/mic automation support, and provider-specific limits. Glip should get the most complete remediation because it is the primary launch target in current docs. |
| Audio routing readiness | The launch path must catch BlackHole and mic mistakes before the meeting starts. | MEDIUM | Check BlackHole 2ch output for call mic, BlackHole 16ch/capture input, monitor output, real `audio.recording_device`, and whether takeover can switch back to Saymo's virtual mic when provider support exists. |
| macOS permission readiness | Hotkeys, Chrome automation, mic capture, and audio routing fail confusingly when macOS permissions are missing. | MEDIUM | Reuse `hotkey-doctor` probe behavior and add permission-oriented blockers where detectable: Accessibility for the launcher/daemon, Apple Events/Chrome automation, microphone capture, and visible audio devices. |
| LaunchAgent/helper health | v1.9 explicitly depends on daily-note and call-control background helpers. | MEDIUM | Call-ready should report helper installed/loaded/running state, last exit/status if available, stale plist paths, and log paths. It should distinguish "not installed" from "installed but stopped" from "installed and stale". |
| Call-control daemon lifecycle | Hotkeys and control state should not require the user to keep the `saymo auto` terminal focused or alive. | HIGH | Add a local daemon/LaunchAgent lifecycle surface: install/start/stop/restart/status/doctor. It should own or supervise live-control state, hotkey registration, command queue reading, and status heartbeat. |
| Handbrake parity outside terminal | The background control surface must behave exactly like existing hotkeys/actions. | MEDIUM | `toggle_auto_answer`, `speak`, `stop`, `takeover`, `skip_current`, `capture_marker`, `status`, and `hard_disable` should use the existing live-control action/state model and audit format. No separate semantics for menu bar vs CLI. |
| Minimal menu-bar control surface | If the daemon is running, the user needs a visible control point during calls. | HIGH | v1.9 menu bar should stay narrow: status indicator plus Auto Answer, Stop, Takeover, Speak, Hard Disable, and Open Status/Logs. Full settings, history browsing, or cockpit review belongs later. |
| Realtime loop start gate | The live meeting loop must start only when launch readiness is green enough for the selected mode. | HIGH | Existing `saymo auto` should either call the new readiness gate or accept a readiness artifact produced by `call-ready`. The loop should refuse to start when voice/cache/provider/handbrake/profile checks fail. |
| Realtime route explanation | During a call, the user should know why Saymo spoke, skipped, or blocked. | MEDIUM | Extend current console/status evidence with `route=prepared_standup`, `route=response_cache:<key>`, `route=blocked_cache_miss`, `route=handbrake_block`, or `route=provider_block`. Keep raw transcripts out of sanitized reports. |
| Launch/realtime evidence artifact | Safety-soak and scorecards need to learn from launch and live-loop failures. | MEDIUM | Write a sanitized launch artifact under a stable local directory such as `~/.saymo/launch_readiness/<profile>/`. Include checks, blocker categories, cache counts, voice/cache metadata result, provider result, daemon state, selected mode, and rerun commands. |
| Post-call health summary | The user should see whether launch stayed healthy after the call, not only whether preflight passed. | MEDIUM | Extend scorecard/rehearsal evidence with launch artifact id, daemon uptime/heartbeat, provider tab drift, cache hits/misses, handbrake actions, blocked unsafe fallbacks, and loop stop reason. |
| Backward-compatible command path | Existing docs and habits use `prepare`, `speak`, `auto`, `auto-preflight`, `rehearsal`, and `safety-soak`. | MEDIUM | v1.9 should add orchestration and stricter gates without breaking existing commands. `auto-preflight` can remain the focused diagnostic; `call-ready` becomes the operator path. |

### Differentiators

Features that make Saymo stronger than a generic local TTS script or meeting
macro.

| Feature | Value Proposition | Complexity | Notes |
|---|---|---:|---|
| Single green launch contract | The product feels operational, not experimental: one command tells the user whether they can trust Saymo for the next call. | HIGH | The differentiator is not one more check; it is correct ordering, actionable blockers, and no hidden unsafe fallback. |
| Local fail-closed realtime loop | Saymo preserves trust by refusing to improvise when the prepared local cache or approved voice path is not ready. | HIGH | Strongly aligns with the local-by-default product value and v1.8 voice approval gates. |
| Terminal-independent handbrake | The user can stop, disable, or take over even if the main terminal is minimized, lost, or not focused. | HIGH | Use daemon/LaunchAgent plus the existing local control files/audit events as the stable boundary. |
| Voice/cache provenance at launch | The user can see exactly which approved voice and cache will be heard in the call. | MEDIUM | Cache metadata makes this feasible and should be visible in launch evidence without exposing private text or audio. |
| Provider-aware remediation | Instead of "provider failed", Saymo can say "open Glip in Chrome", "BlackHole 2ch missing", or "mic switching unsupported for this provider". | MEDIUM | Current provider checks and latency probes already contain useful segmented evidence; call-ready should make it operator-friendly. |
| Rehearsal-to-launch feedback loop | Failed rehearsals, launch attempts, and live-loop blocks feed back into the next preflight/safety-soak run. | MEDIUM | This compounds the value of v1.7 scorecards rather than creating a separate readiness world. |
| Small local daemon instead of cloud control | Background reliability improves without adding a server, account, or cloud dependency. | MEDIUM | Keep files under `~/.saymo/`, use LaunchAgent semantics on macOS, and avoid network services unless explicitly configured. |

### Anti-Features

Features to explicitly avoid in v1.9 even if they seem convenient.

| Anti-Feature | Why Requested | Why Problematic | What to Do Instead |
|---|---|---|---|
| Silent "fix everything" launch command | It sounds convenient before a meeting. | It can change audio routing, Chrome state, or helper state in surprising ways right before a live call. | Default to check/report plus safe idempotent note/cache preparation. Require explicit flags for starting/restarting helpers or changing routes. |
| Live LLM+TTS fallback on automatic cache miss | It makes Q&A feel more capable. | Latency, voice quality, and safety are not predictable enough for automatic live-call output. | Fail closed by default; allow preview/manual approved draft paths; make live fallback an explicit future/advanced mode. |
| Starting realtime loop with warnings ignored | It avoids blocking the user. | Warnings like missing hotkeys, stale cache, or stopped daemon are exactly the failure modes v1.9 exists to prevent. | Define mode-specific gates: some warnings may allow listen-only, but automatic speaking requires stricter readiness. |
| Full native settings/history app | A polished UI is appealing. | It expands scope before the daemon/control contract is proven. | v1.9 menu bar should expose status and emergency controls only. Defer settings/history dashboards. |
| Autonomous meeting participation | It sounds like the final product vision. | Saymo is currently an assistant for prepared answers and addressed questions; full autonomy risks wrong speech and social failures. | Keep manual takeover, explicit approved drafts, and fail-closed automation boundaries. |
| Voice model training, downloads, or cleanup during call-ready | It can appear to "repair" voice readiness. | Training/downloads are long, heavy, and risky; cleanup can destroy expensive voice assets. | Report the blocker and route to explicit voice/profile commands outside the launch path. |
| Raw transcript/audio in launch reports | More evidence seems useful for debugging. | Launch evidence may be shared or inspected quickly; raw call content and audio are private. | Store sanitized counts, statuses, fingerprints, and route decisions; link to local detailed artifacts only when already part of existing workflows. |
| Treat terminal live-control as sufficient | It is already implemented. | The v1.9 goal is reliable live control outside the terminal. | Keep terminal controls as fallback and test harness; add daemon/menu-bar lifecycle for call use. |
| Killing/restarting Chrome or meeting apps automatically | It might recover provider automation. | It can drop the user from a live call or destroy browser state. | Tell the user which tab/app state is wrong and provide manual remediation. |

## Feature Dependencies

```text
Daily note helper
    -> prepared standup text/audio
        -> prepared cache metadata check
            -> call-ready launch gate

Response library + approved voice selector
    -> response-cache variants with metadata
        -> realtime Q&A route gate
            -> fail-closed automatic answering

Provider tab + BlackHole devices + macOS permissions
    -> provider/audio readiness
        -> call-ready launch gate
            -> realtime loop start

Existing live-control state/actions/hotkeys
    -> call-control daemon/LaunchAgent
        -> menu-bar/status surface
        -> handbrake availability during realtime loop

Launch artifact + live-loop event evidence
    -> session-scorecard/rehearsal extensions
        -> safety-soak regression gate
```

### Dependency Notes

- **Call-ready requires prepared cache and response cache:** The user-facing launch contract is meaningless unless both the planned standup audio and short Q&A variants are known fresh for the selected profile.
- **Realtime loop requires call-ready pass:** `saymo auto` should not perform its own partial, divergent check set. Use the same gate or a freshly validated readiness artifact.
- **Daemon requires existing live-control semantics:** The daemon should not introduce new control behavior. It should expose the existing command queue, state snapshot, hotkey bindings, and audit events from a background process.
- **Menu bar requires daemon status:** A menu item that queues actions without knowing whether the daemon/listener is alive creates false confidence.
- **Post-call evidence requires launch/live artifacts:** Scorecards can only explain launch health if launch readiness writes structured local evidence before the call starts.
- **Fail-closed cache behavior conflicts with default live fallback:** If `responses.live_fallback` is enabled, call-ready should warn or block automatic answering unless the selected mode explicitly accepts live fallback risk.

## v1.9 Priority Ordering

The milestone should follow the user's selected order: Call Launch Readiness,
then Realtime Meeting Loop, then Live Control Daemon/Menu Bar. There is one
practical caveat: the realtime loop can be implemented before the polished menu
bar, but it should still depend on at least a minimal daemon/status contract if
the user is expected to rely on hotkeys outside the terminal.

| Capability | User Value | Implementation Cost | Priority | Boundary |
|---|---:|---:|---:|---|
| `saymo call-ready -p <profile>` orchestration | HIGH | HIGH | P1 | v1.9 MVP |
| Blocker/warning remediation output | HIGH | MEDIUM | P1 | v1.9 MVP |
| Daily-note + prepare + response-cache integration | HIGH | MEDIUM | P1 | v1.9 MVP |
| Voice/cache metadata launch gate | HIGH | MEDIUM | P1 | v1.9 MVP |
| Provider/audio/permission readiness | HIGH | MEDIUM | P1 | v1.9 MVP |
| Strict realtime start gate for `saymo auto` | HIGH | HIGH | P1 | v1.9 MVP |
| Fail-closed automatic cache-miss handling | HIGH | MEDIUM | P1 | v1.9 MVP |
| Launch artifact for scorecard/soak | MEDIUM | MEDIUM | P1 | v1.9 MVP |
| Daemon lifecycle: install/start/stop/status/doctor | HIGH | HIGH | P2 | v1.9 should include before menu polish |
| Daemon-backed handbrake actions and heartbeat | HIGH | HIGH | P2 | v1.9 should include before menu polish |
| Minimal menu-bar status/actions | MEDIUM | HIGH | P2 | v1.9 if daemon contract is stable |
| Post-call launch-health scorecard extension | MEDIUM | MEDIUM | P2 | v1.9 after artifact format exists |
| Provider-specific one-click repairs | MEDIUM | HIGH | P3 | Future; start with actionable instructions |
| Calendar-based automatic call launch | LOW | HIGH | P3 | Future |
| Rich menu-bar settings/history/cockpit UI | MEDIUM | HIGH | P3 | Future |
| Guarded live synthesis fallback | MEDIUM | HIGH | P3 | Future after latency/quality evidence |

**Priority key:**
- **P1:** required for v1.9 to satisfy Call Launch Readiness.
- **P2:** should ship in v1.9 if it does not destabilize P1; otherwise next patch.
- **P3:** defer until core launch/realtime behavior is proven.

## MVP Definition

### Launch With in v1.9

- [ ] **Call-ready orchestrator** - One operator entry point that runs the existing preparation and readiness primitives in the correct order.
- [ ] **Actionable readiness model** - Structured `block/warn/info` output with remediation categories and rerun commands.
- [ ] **Daily-note and cache preparation** - Missing daily note handled idempotently; standup audio and response-cache variants prepared or clearly blocked.
- [ ] **Voice/cache/provider/handbrake gate** - Approved cloned voice, cache metadata, provider tab, BlackHole routing, triggers, hotkeys/control state, and profile readiness checked together.
- [ ] **Strict realtime start behavior** - `saymo auto` or a new realtime alias starts only after readiness passes for the selected mode.
- [ ] **Fail-closed automatic response policy** - Cache miss, stale voice metadata, unsafe fallback, hard-disable, manual takeover, or provider loss blocks automatic playback.
- [ ] **Sanitized launch artifact** - Readiness result can be consumed by scorecards/safety-soak without raw transcripts or audio.

### Add During v1.9 if P1 Is Stable

- [ ] **Call-control daemon lifecycle** - Install/start/stop/restart/status/doctor for a local LaunchAgent-backed control process.
- [ ] **Daemon-backed action queue and heartbeat** - Same handbrake actions as current CLI/hotkeys, with visible alive/stale state.
- [ ] **Minimal menu-bar surface** - Status plus core emergency controls only.
- [ ] **Post-call launch-health scorecard** - Show launch pass/fail, cache hits/misses, daemon state, provider drift, and blocked unsafe fallbacks.

### Future Boundaries

- [ ] **Calendar-aware auto-launch** - Defer until manual call-ready flow is trusted.
- [ ] **Rich native menu-bar app** - Defer settings, history, cockpit review, and visual dashboards.
- [ ] **Guarded live synthesis fallback** - Needs latency, voice-quality, approval, and failure-mode evidence beyond v1.9 MVP.
- [ ] **Automatic provider repair** - Start with instructions; defer changing live app state automatically.
- [ ] **Voice-command handbrake** - Useful later, but v1.9 should first make hotkeys/daemon/menu reliable.
- [ ] **Full autonomous meeting agent** - Outside the product safety boundary for this milestone.

## Recommended User Workflows

### Before The Call

Recommended operator path:

```bash
saymo call-ready -p personal --provider glip
```

Expected behavior:

- Creates or verifies the Obsidian daily note through the existing safe helper.
- Runs prepare for the selected profile unless a fresh prepared cache already exists.
- Builds or verifies response-cache variants.
- Validates approved cloned voice and cache metadata.
- Checks Chrome provider tab, BlackHole devices, real mic, hotkeys/control state, daemon/helper state, and profile triggers.
- Prints one result: `ready` or `not ready`.
- Writes a sanitized launch artifact for later scorecard/safety-soak use.

### If Not Ready

The report should be directly actionable:

```text
block: provider tab: Glip tab not found in Chrome
  action: Open the Glip meeting in Chrome.
  rerun: saymo call-ready -p personal --provider glip

block: response cache: 31/42 variants ready, 11 stale for f5tts_clone
  action: Rebuild response cache for this profile.
  rerun: saymo prepare -p personal
```

The user should not need to interpret stack traces, know cache paths, or guess
which older diagnostic command to run first.

### Starting The Realtime Loop

Keep `saymo auto -p personal` compatible, but make it use the same gate:

```bash
saymo auto -p personal
```

Expected behavior:

- If readiness has not passed recently, run or require the launch gate.
- If readiness fails, do not start automatic speaking.
- If readiness passes, start listening and publish live-control state.
- On trigger, route through prepared standup or response cache only when that route is safe.
- On cache miss or unsafe fallback, skip/block and record evidence instead of improvising.

An optional `saymo realtime -p personal` alias may make the new behavior clearer,
but it should share implementation with `auto` rather than splitting the live
loop.

### During The Call

Expected controls:

- Menu bar or daemon-backed status shows `listening`, `speaking`, `paused`,
  `takeover`, `hard disabled`, and last action.
- Stop, Hard Disable, Takeover, Auto Answer, Speak, Skip, and Status behave the
  same whether triggered from hotkey, terminal command, daemon/menu, or script.
- Every action appends to the existing local audit trail.
- If daemon heartbeat is stale, menu/status should show "control unavailable"
  instead of pretending an action was delivered.

### After The Call Or Rehearsal

Expected evidence:

```bash
saymo session-scorecard -p personal --rehearsal <artifact>
saymo safety-soak -p personal --scorecard-json <scorecard.json>
```

The scorecard should include launch health, daemon/control availability,
provider readiness drift, cache hit/miss counts, unsafe fallback blocks,
handbrake actions, and realtime loop stop reason. The report should remain
sanitized.

## v1.9 vs Future Boundary

| Area | v1.9 Behavior | Future Behavior |
|---|---|---|
| Launch path | One explicit call-ready command/report for a selected profile/provider. | Calendar-aware preparation and optional scheduled readiness checks. |
| Daily note | Create/verify the known daily note and standup section. | Rich note authoring, summarization, or cross-day planning. |
| Prepared speech | Fresh approved cloned-voice cache required for call output. | Multiple prepared scripts per meeting agenda or participant. |
| Realtime answers | Prepared standup and response-cache routes only by default. | Guarded live generation after separate latency/quality/safety validation. |
| Provider readiness | Chrome/provider tab and audio route checks with remediation. | Deeper provider adapters, native-app support, or automated repair actions. |
| Control daemon | Local LaunchAgent/daemon with heartbeat and action queue. | Rich native control service, notifications, and remote-safe APIs. |
| Menu bar | Minimal status and emergency controls. | Settings, history, cockpit review, and visual diagnostics. |
| Evidence | Sanitized launch/live-loop artifacts feeding scorecard/soak. | Trend dashboard across meetings and reliability baselines. |
| Autonomy | Assistant speaks only through prepared/approved paths and keeps manual takeover. | Any autonomous meeting behavior requires a separate milestone and safety model. |

## Sources

- `.planning/PROJECT.md` - current v1.9 milestone goal, existing delivered capabilities, active requirements, and explicit out-of-scope boundaries. Confidence: HIGH.
- `docs/QUICK-START.md` - current user workflows for setup, prepare/speak/auto, auto-preflight, rehearsal, safety-soak, provider latency, and takeover. Confidence: HIGH.
- `docs/LIVE-CONTROL-HANDBRAKE.md` - existing operator controls, hotkeys, safety rules, and v1.6 terminal/control-file limitations. Confidence: HIGH.
- `saymo/commands/core.py` - current `auto`, `speak`, `prepare`, live-control actions, voice selector/cache checks, realtime route behavior, and handbrake state. Confidence: HIGH.
- `saymo/commands/tests.py` - current diagnostics: `prepare-responses`, `trigger-check`, `auto-preflight`, `rehearsal`, `session-scorecard`, `safety-soak`, `hotkey-doctor`, `provider-latency`, `takeover-check`, meeting memory, and answer cockpit. Confidence: HIGH.
- `saymo/analysis/remediation.py` - existing remediation categories and rerun-command rendering to extend for v1.9. Confidence: HIGH.
- `saymo/analysis/response_cache.py` - current pre-synthesized response-cache library, cache metadata behavior, lookup, and cache readiness assumptions. Confidence: HIGH.
- Codex memory notes for the v1.8 voice-clone benchmark work - confirms `f5tts_clone` as the current approved/local direction and reinforces explicit gates for heavy downloads, training, cleanup, and voice assets. Confidence: MEDIUM because local runtime state can drift.

---

Feature research for: Saymo v1.9 Call Launch Readiness
Researched: 2026-07-08

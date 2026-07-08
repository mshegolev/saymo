# Stack Research: Saymo v1.9 Call Launch Readiness

**Domain:** Local macOS voice assistant call launch, realtime loop readiness, and local handbrake daemon/control surface
**Researched:** 2026-07-08
**Confidence:** HIGH for repo-local stack decisions; MEDIUM for macOS/pynput currentness caveats

## Summary

v1.9 should not add a new application stack. Saymo already has the right
runtime foundation for this milestone: Python 3.11+, Click commands, dataclass
YAML config, Rich terminal output, BlackHole audio routing, Chrome provider
automation through AppleScript, `pynput` global hotkeys, file-backed
live-control state, prepared standup WAVs, response-cache WAVs, voice selector
metadata, `auto-preflight`, rehearsal, scorecard, and safety-soak.

The required stack change is a small operational layer around existing
capabilities:

1. A `call-ready` orchestration command that creates/checks the daily note,
   prepares standup audio and response-cache variants, validates voice cache
   metadata, checks provider/audio/profile/readiness, and reports actionable
   blockers.
2. A strict realtime readiness gate before `saymo auto` enters the hot path.
   It should fail closed on unsafe voice/profile state and cache-miss policy
   rather than silently speaking generic fallback audio.
3. A per-user macOS LaunchAgent plus local Python daemon command that keeps
   hotkeys and live-control actions available outside a terminal window.
4. A lightweight status/control surface using the existing JSON/JSONL control
   files and CLI/TUI output. Do not build native app packaging in v1.9.

Recommendation: add no required third-party dependencies. Use stdlib
`asyncio`, `json`, `pathlib`, `datetime`, `hashlib`, `plistlib`, `subprocess`,
`shlex`, `signal`, and existing project dependencies. If a missing local package
must be resolved later, prefer the internal PyPI/Nexus mirror for developer
installs, but no package resolution is required for the recommended v1.9 stack.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | `>=3.11`; local env observed `3.12.1` | All v1.9 commands, daemon logic, launchd plist generation, readiness checks | Existing project standard in `pyproject.toml`; stdlib is sufficient for process, JSON, plist, and file-state work. |
| Click | `>=8.1.0`; local env observed `8.3.2` | New `call-ready`, daemon, LaunchAgent install/status commands | Existing CLI framework. Keeps v1.9 flows consistent with `auto-preflight`, `rehearsal`, and `live-control-action`. |
| Rich | `>=13.0.0`; local env observed `15.0.0` | Human-readable readiness/status output | Existing diagnostic output style. Use conservative Rich APIs so the repo lower bound remains valid. |
| Dataclass config + PyYAML | PyYAML `>=6.0`; local env observed `6.0.3` | Optional config additions for daemon/readiness policy | Existing `saymo/config.py` pattern. Do not introduce Pydantic or another settings layer. |
| launchd LaunchAgent | macOS built-in | Keep the local control daemon running in the user GUI session | Correct macOS primitive for GUI-session hotkeys, AppleScript/System Events, Chrome automation, and user-home logs. Use LaunchAgent, not LaunchDaemon or cron. |
| `plistlib` | Python stdlib | Generate/validate LaunchAgent plists | Avoids brittle string templates and adds no dependency. Use only fields available on Python 3.11/3.12. |
| `pynput.keyboard.GlobalHotKeys` | `>=1.7.6`; local env observed `1.8.1` | Global handbrake hotkeys in the daemon | Already used by `saymo auto` and `hotkey-doctor`. Keep it, but surface macOS Accessibility permission as an explicit readiness blocker/warning. |
| File-backed live control | Existing JSON/JSONL under `~/.saymo/live_control/<profile>/` | Local IPC between daemon, CLI, TUI, and realtime loop | Already implemented in `saymo/analysis/live_control.py`; simple, inspectable, private, and enough for one-user local control. |
| AppleScript via `osascript` | macOS built-in | Chrome tab/provider checks, activation, mute/mic actions | Existing provider abstraction is AppleScript-based. Do not add browser automation frameworks for v1.9. |
| pytest | Dev group `>=9.0.3`; local env observed `9.0.3` | Readiness, daemon, LaunchAgent plist, and fail-closed behavior tests | Existing test framework. |

### Supporting Libraries And Modules

| Library / Module | Version | Purpose | When to Use |
|------------------|---------|---------|-------------|
| `saymo.analysis.live_control` | Repo-local | Action catalog, command queue, state, audit, hotkey bindings | Reuse for daemon, status commands, menu-adjacent script output, and realtime loop control. Extend for heartbeat/daemon health instead of creating a second protocol. |
| `saymo.commands.tests._collect_auto_preflight` | Repo-local | Existing readiness checks | Reuse or move to a neutral `saymo.analysis.readiness` module if multiple commands need it. Do not duplicate checks in `call-ready`. |
| `saymo.commands.core._call_ready_cached_audio` | Repo-local | Voice selector/cache metadata gate for prepared WAVs | Use in `call-ready` and `saymo auto` startup before trusting prepared audio. |
| `saymo.analysis.response_cache` | Repo-local | Prepared response-cache variants and metadata | Keep Q&A hot path playback-only. Add stricter completeness/miss-policy reporting for realtime readiness. |
| `saymo.analysis.cache_metadata` | Repo-local | Privacy-safe voice cache sidecars | Required for validating prepared standup and response-cache WAVs against current voice/profile state. |
| `saymo.tts.selector` | Repo-local | Purpose-specific voice engine selection and live-call approval policy | Continue to block non-cloned or unapproved live-call output by default. |
| `scripts.ensure_obsidian_daily_note` | Repo-local | Daily note creation helper | Reuse the logic, preferably by importing/moving it into a package module so `call-ready` does not shell out to a script. |
| `sounddevice` / `soundfile` | Existing deps | Audio device detection, playback, WAV inspection | Reuse for BlackHole checks and cache validation. No new audio dependency. |
| `faster-whisper` | Optional `stt` extra | Realtime transcription in `saymo auto` | Keep optional. v1.9 should not download or change STT models as part of call launch. |
| `httpx` | Existing dep | Ollama health or local API checks | Reuse only for existing local Ollama checks. Do not introduce a control HTTP server. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Existing environment/dependency runner | Keep using `uv run pytest` and `uv sync`. No `uv add` needed for v1.9. |
| `launchctl` | Install, start, inspect, stop LaunchAgents | Use modern subcommands: `bootstrap`, `bootout`, `kickstart`, `print`. Avoid old `load`/`unload` flows. |
| `osascript` | Chrome/System Events provider automation | Already in provider stack. Must run in the user GUI session with Accessibility/Automation permissions. |
| `man launchd.plist`, `man launchctl` | Local macOS source of truth | Use for exact key behavior on the target macOS version. |
| `pytest` + `CliRunner` | CLI and helper tests | Add tests for plist generation, status parsing, stale daemon detection, and fail-closed response policy. |

## Stack Additions

### 1. Call-ready Orchestrator: No New Dependency

Add one package-level readiness/orchestration layer, for example:

```text
saymo/analysis/readiness.py
saymo/commands/call_ready.py
```

Use it to compose existing operations:

- ensure today's Obsidian daily note exists;
- run or prompt the user to run `prepare`/`prepare-responses` when needed;
- validate prepared standup WAV metadata through `_call_ready_cached_audio`;
- validate response-cache metadata through `ResponseCache` plus
  `build_voice_cache_metadata(..., purpose="response_cache")`;
- reuse provider readiness from `saymo.providers.factory.get_provider`;
- reuse BlackHole/input/output device checks from `saymo.audio.devices`;
- reuse hotkey bindings and live-control state from `saymo.analysis.live_control`;
- add LaunchAgent/daemon health checks;
- render one ready/not-ready result with remediation and rerun commands.

The orchestrator should return structured objects, not only printed strings,
so roadmap phases can feed the same results into CLI, rehearsal, scorecard,
and safety-soak.

Recommended internal model:

```python
@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    ok: bool
    detail: str
    blocking: bool = True
    remediation: str = ""
    rerun: str = ""
```

This mirrors existing `PreflightCheck` without making `saymo.commands.tests`
the long-term owner of production readiness logic.

### 2. Strict Realtime Miss Policy

Current `_resolve_auto_response_decision` can route cache misses to generic
standup fallback when live fallback is disabled. For v1.9 realtime loop
readiness, add an explicit policy before `saymo auto` starts.

Recommended config addition:

```yaml
responses:
  realtime_miss_policy: block  # block | standup_fallback | live_fallback
```

Default should be `block` for the realtime meeting loop. Rationale:

- `block` prevents Saymo from answering a specific question with a generic
  standup when the response cache misses.
- `standup_fallback` can remain available for explicit/manual speak or legacy
  behavior, but should not be the default for call-ready realtime Q&A.
- `live_fallback` should stay opt-in because it runs local LLM+TTS on the hot
  path and can miss latency targets.

No new LLM, TTS, or cache library is needed. This is a policy/config change
around existing `ResponseCache`, `VoiceSelector`, and `_resolve_auto_response`
behavior.

### 3. Call-control Daemon

Add a local daemon command, for example:

```bash
saymo call-control-daemon -p personal
```

The daemon should:

- register the configured `pynput` global hotkeys;
- write heartbeat/status to existing control state or a small adjacent file:
  `~/.saymo/live_control/<profile>/daemon.json`;
- append commands to `commands.jsonl` with source `daemon` or `hotkey`;
- expose status through `saymo call-control-status -p personal --json`;
- avoid speaking, transcribing, or running provider actions itself unless the
  command explicitly asks it to queue a live-control action.

Important boundary: the daemon is a control listener, not the realtime meeting
loop. `saymo auto` remains the process that captures audio, transcribes,
decides, and plays. This keeps responsibility clear and avoids two processes
fighting over BlackHole or provider state.

Use stdlib `asyncio` or a simple blocking loop. Do not add `daemonize`,
`supervisor`, `watchdog`, `psutil`, FastAPI, or a WebSocket stack.

### 4. LaunchAgent Management

Add LaunchAgent helper commands, for example:

```bash
saymo launch-agent install -p personal
saymo launch-agent status -p personal
saymo launch-agent start -p personal
saymo launch-agent stop -p personal
saymo launch-agent uninstall -p personal
```

Implementation stack:

- Generate plist with `plistlib`.
- Place per-user plists under `~/Library/LaunchAgents/`.
- Use a stable label such as `com.saymo.call-control.personal` or a configured
  prefix if this repo wants user-specific labels.
- Use absolute `ProgramArguments`, preferably:

```text
<venv-python> -m saymo.cli call-control-daemon -p personal
```

- Set explicit `EnvironmentVariables`, at minimum `HOME`, `PATH`, and
  `NO_PROXY=localhost,127.0.0.1`.
- Set `WorkingDirectory` to the repo or install root only if needed.
- Write logs under `~/.saymo/logs/`.
- Use `RunAtLoad=true`.
- Use `KeepAlive` carefully. Prefer a dictionary that restarts crashes but
  does not fight intentional clean exits, for example `SuccessfulExit=false`,
  rather than unconditional respawn if the user uses a stop command.

Readiness checks should compare:

- plist exists at expected path;
- generated plist fingerprint matches the current expected config;
- `launchctl print gui/<uid>/<label>` succeeds;
- daemon heartbeat is fresh;
- `pynput` registration status is `ok` or has a clear Accessibility blocker.

Do not use cron. Do not use LaunchDaemon. The hotkey/provider stack needs the
user GUI session, Chrome, System Events, and per-user Accessibility/Automation
permissions.

### 5. Menu-bar-adjacent Status Without Native Packaging

v1.9 should not add a native menu bar app dependency. The practical stack is:

- `saymo call-control-status -p personal` for human output;
- `saymo call-control-status -p personal --json` for machine output;
- optional `saymo call-control-status -p personal --menu` that prints a
  simple text menu format later consumable by an external menu runner;
- existing `saymo live-control -p personal` TUI for active control;
- `saymo live-control-action -p personal --action stop` for scriptable actions.

This satisfies "menu-bar-adjacent" by making state/control scriptable from the
menu bar or macOS Shortcuts without committing PyObjC, rumps, Swift, py2app,
Briefcase, Electron, or a web server. Productized native packaging remains a
separate milestone.

### 6. Post-call And Rehearsal Evidence Integration

Keep using:

- `saymo rehearsal`;
- `saymo session-scorecard`;
- `saymo safety-soak`;
- local JSON/Markdown artifacts under `~/.saymo/`.

Add v1.9 fields to the existing evidence model:

- launch path status;
- LaunchAgent label/path/fingerprint;
- daemon heartbeat age;
- hotkeys registered by daemon vs `saymo auto`;
- provider readiness at launch;
- prepared standup cache metadata result;
- response-cache variants ready/total;
- realtime miss policy;
- cache hit/miss and unsafe fallback blocks;
- handbrake action source: hotkey, daemon, CLI, panel, auto.

No database is needed. Existing JSON/JSONL is enough for local evidence and
scorecard inputs.

## Installation

No package install is recommended for v1.9.

Use existing project commands:

```bash
uv sync
uv run pytest
uv run saymo auto-preflight -p personal
uv run saymo hotkey-doctor -p personal
```

Future LaunchAgent commands should generate and manage the plist:

```bash
uv run saymo launch-agent install -p personal
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.saymo.call-control.personal.plist
launchctl kickstart -k gui/$(id -u)/com.saymo.call-control.personal
launchctl print gui/$(id -u)/com.saymo.call-control.personal
```

The CLI should run these or print exact commands; it should not require users
to hand-edit plists.

## Internal PyPI / Nexus Notes

No package resolution is required if the roadmap follows this stack.

If a later phase discovers a missing existing dependency in a developer
environment, prefer the internal Nexus/PyPI mirror for local install attempts.
Do not hardcode internal indexes in committed `pyproject.toml`, public docs,
or user config. Do not fall through to public PyPI silently if internal
resolution is expected.

There is no reason to add or resolve these packages for v1.9:

- `rumps`
- `pyobjc`
- `fastapi`
- `flask`
- `websockets`
- `watchdog`
- `psutil`
- `daemonize`
- `APScheduler`
- `selenium`
- `playwright`
- new TTS/STT packages

## Alternatives Considered

| Recommended | Alternative | Why Not / When Alternative Makes Sense |
|-------------|-------------|----------------------------------------|
| Per-user LaunchAgent | cron | cron is the wrong macOS primitive for GUI-session hotkeys, Chrome/System Events, user environment, logs, and sleep/wake behavior. |
| Per-user LaunchAgent | LaunchDaemon | LaunchDaemon runs outside the user's GUI context and is wrong for Accessibility, Chrome automation, and user-home state. |
| `plistlib` plist generation | String-template XML | `plistlib` is stdlib, structured, and testable. Templates are easier to make invalid or stale. |
| Existing JSON/JSONL live-control files | HTTP/WebSocket local server | File-backed IPC is enough for one-user local control, works offline, avoids port conflicts, and matches existing code. |
| Existing Rich CLI/TUI status | Native menu bar app | v1.9 needs reliable control availability, not productized native UI distribution. Native app packaging can follow once the control contract is stable. |
| `pynput` hotkeys | Custom Quartz event tap / PyObjC | `pynput` is already integrated and tested. Quartz/PyObjC raises dependency, packaging, and permission complexity. |
| AppleScript Chrome providers | Playwright/Selenium | Existing providers already use Chrome tab discovery and mute/mic actions. Browser automation stacks add weight and can be brittle for live calls. |
| `launchctl print` + heartbeat file | `psutil` process scanning | launchd and heartbeat state answer the real operational question without a new dependency. |
| Response cache fail-closed policy | Live LLM+TTS fallback by default | Live generation can exceed latency and can synthesize unsafe/unapproved output. Keep opt-in only. |

## What NOT To Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| New required cloud STT/TTS/voice APIs | Violates local-first product constraint and changes privacy posture | Existing local F5 voice selector, local response cache, optional existing local Ollama |
| New voice engines or model downloads | v1.9 is launch readiness, not voice research | Existing approved `f5tts_clone` path and voice profile gates |
| FastAPI/Flask/WebSocket control daemon | Adds a network surface and dependency for local one-user IPC | Existing JSON/JSONL command queue and status files |
| SQLite/TinyDB/vector store | Unneeded persistence for small local control/status records | JSON, JSONL, and existing artifacts under `~/.saymo/` |
| `watchdog` | File polling at current scale is sufficient; launchd can own process lifecycle | Existing 0.25s command polling or simple heartbeat checks |
| `psutil` | Not necessary for launchd-managed process health | `launchctl print`, PID from launchd if needed, heartbeat file |
| `rumps`, PyObjC, py2app, Briefcase, Electron | Native packaging is explicitly out of scope for v1.9 | CLI status, Rich TUI, scriptable action commands |
| `screen`, `tmux`, shell daemon loops | Harder to inspect/recover and not native to macOS service management | LaunchAgent |
| cron | Wrong environment and permission model for macOS GUI automation | LaunchAgent |
| Selenium/Playwright | Heavy and unnecessary for current Chrome provider checks | Existing AppleScript provider abstraction |
| Silent non-cloned fallback in live calls | User may believe Saymo is speaking in the approved cloned voice | Voice selector blocks and explicit fallback policy |
| Auto-speaking generated answer drafts | Violates existing approval boundary | Response cache, approved draft path, manual controls |

## Stack Patterns By Variant

**Call-ready command**

- Use Click + Rich.
- Reuse `_collect_auto_preflight`, `_call_ready_cached_audio`,
  `ResponseCache`, voice selector, provider factory, and daily-note helper.
- Return structured readiness checks.
- Add exact remediation and rerun commands.

**Realtime meeting loop**

- Start only after readiness checks pass.
- Use existing `AudioCapture`, `LocalWhisper`, `TurnDetector`,
  `ResponseCache`, and `VoiceSelector`.
- Treat cache miss as a policy decision. Default live-call policy should block,
  not generic fallback.
- Keep `responses.live_fallback` opt-in and gated through `live_call` voice
  selector policy.

**Control daemon**

- Use Python stdlib loop + `pynput.GlobalHotKeys`.
- Write heartbeat/status under existing live-control profile directory.
- Queue normalized actions with `append_control_command`.
- Do not capture audio or synthesize speech.

**LaunchAgent**

- Use `plistlib`.
- Install under `~/Library/LaunchAgents`.
- Load into `gui/<uid>`.
- Use `RunAtLoad`, careful `KeepAlive`, absolute `ProgramArguments`, explicit
  `EnvironmentVariables`, and logs under `~/.saymo/logs`.
- Verify with `launchctl print` and heartbeat freshness.

**Menu/status surface**

- Use `call-control-status` and existing `live-control` TUI.
- Make output scriptable (`--json`, possibly `--menu`).
- Defer native menu bar frameworks.

## Version Compatibility And Currentness Caveats

| Component | Current Repo / Local State | Recommendation / Caveat |
|-----------|----------------------------|--------------------------|
| Python | `pyproject.toml` requires `>=3.11`; local `uv run` uses `3.12.1` | Keep `>=3.11`. Use `plistlib` APIs available in 3.11/3.12; do not use newer stdlib-only features without raising the floor. |
| `pynput` | `pyproject.toml` `>=1.7.6`; local `1.8.1` | Keep lower bound unless tests prove a bug. macOS Accessibility permission remains an operational requirement. |
| Click | `>=8.1.0`; local `8.3.2` | Keep current bound; avoid relying on newer 8.3-only behavior in CLI tests. |
| Rich | `>=13.0.0`; local `15.0.0` | Keep current bound; use conservative table/panel/live APIs. |
| PyYAML | `>=6.0`; local `6.0.3` | Reuse existing config loader. Do not add Pydantic. |
| sounddevice | `>=0.5.0`; local `0.5.5` | Reuse for BlackHole/device checks. No change. |
| soundfile | `>=0.12.0`; local `0.13.1` | Reuse for WAV/cache inspection. No change. |
| faster-whisper | Optional `stt` extra `>=1.0.0` | Keep optional and avoid model downloads in readiness commands. |
| launchd/launchctl | macOS built-in; local manpages include `RunAtLoad`, `KeepAlive`, `StandardOutPath`, `StandardErrorPath`, `EnvironmentVariables`, `WorkingDirectory`, `bootstrap`, `bootout`, `kickstart`, `print` | Verify on target macOS during implementation. Use LaunchAgent in `gui/<uid>`, not LaunchDaemon. |
| F5 runtime | Existing approved `f5tts_clone` path; isolated runtime outside main env | Do not modify for v1.9. Readiness checks should validate, not install/download. |

## Integration Points

| Area | Files / Modules | Stack Action |
|------|-----------------|--------------|
| Config | `saymo/config.py` | Add only small dataclasses if needed: daemon label/log dirs, heartbeat stale threshold, realtime miss policy. Keep defaults safe. |
| Call-ready CLI | `saymo/commands/*` | Add command wrapper that orchestrates daily note, prepare/cache, preflight, launchd, and daemon checks. |
| Daily note | `scripts/ensure_obsidian_daily_note.py` | Reuse logic; prefer moving importable helper into package to avoid subprocess calls. |
| Preflight | `saymo/commands/tests.py` | Reuse existing checks; consider moving `_collect_auto_preflight` to `saymo.analysis.readiness`. |
| Realtime loop | `saymo/commands/core.py` | Gate `auto` startup through the stricter readiness policy and response-cache miss policy. |
| Live control | `saymo/analysis/live_control.py`, `saymo/live_control_tui.py` | Extend with daemon heartbeat/status; keep action names and command queue unchanged. |
| Provider readiness | `saymo/providers/*` | Keep AppleScript provider abstraction; add more actionable readiness detail, not a new browser stack. |
| Evidence | `saymo.analysis.rehearsal`, `session_scorecard`, `safety_soak` | Add launch/daemon/cache-miss evidence fields and warnings. |
| Tests | `tests/analysis`, `tests/test_*_cli.py` | Add unit tests for plist generation, status parsing, stale heartbeat, call-ready output, and fail-closed cache behavior. |

## Sources

- Repo source: `.planning/PROJECT.md` - v1.9 scope, existing capabilities, out-of-scope boundaries.
- Repo source: `pyproject.toml` - Python and dependency bounds.
- Repo source: `saymo/config.py` - dataclass config, voice selector, live, safety, response-cache settings.
- Repo source: `saymo/analysis/live_control.py` - action catalog, state, command queue, hotkey bindings, audit.
- Repo source: `saymo/commands/core.py` - `auto`, live-control commands, response routing, cached audio gates.
- Repo source: `saymo/commands/tests.py` - `auto-preflight`, rehearsal, scorecard, safety-soak, hotkey doctor.
- Repo source: `scripts/ensure_obsidian_daily_note.py` - daily-note creation helper.
- Local source: `man launchd.plist` - LaunchAgent keys and user LaunchAgent locations.
- Local source: `man launchctl` - `bootstrap`, `bootout`, `kickstart`, and `print` commands.
- Apple archived launchd guide: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- Python `plistlib` docs: https://docs.python.org/3/library/plistlib.html
- pynput keyboard docs: https://pynput.readthedocs.io/en/latest/keyboard.html

---
*Stack research for: Saymo v1.9 Call Launch Readiness*
*Researched: 2026-07-08*

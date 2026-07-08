# Phase 38: Local Call-Control Daemon and LaunchAgent - Research

**Researched:** 2026-07-08
**Domain:** Saymo live-control daemon, LaunchAgent lifecycle, hotkey reachability, launch-readiness diagnostics
**Confidence:** HIGH for repo-local integration points; MEDIUM for live macOS launchd/TCC behavior because it still needs manual GUI-session verification

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Approved Design Direction

Use a small local control-plane daemon that reuses the existing live-control
primitives:

- `commands.jsonl` remains the durable command queue.
- `state.json` remains the operator-facing state snapshot.
- `audit.jsonl` remains the action trail consumed by scorecards and safety
  checks.
- The daemon registers global hotkeys and writes queued commands plus heartbeat
  evidence; the realtime audio/STT/TTS/provider loop continues to own
  transcription, synthesis, playback, and provider mutation.
- LaunchAgent support installs a per-profile user LaunchAgent under
  `~/Library/LaunchAgents`, with explicit `PATH`, `HOME`, stdout/stderr logs,
  and user-session `launchctl bootstrap/kickstart/bootout` commands.

This follows the repo's current macOS rule: use launchd, not cron.

## Existing Building Blocks

- `saymo.analysis.live_control`
  - `LiveControlCommand`, `LiveControlSnapshot`
  - `append_control_command`, `read_control_commands`
  - `write_live_state`, `load_live_state`
  - `append_control_audit`
  - `effective_hotkey_bindings`, `hotkey_listener_bindings`
  - `build_hotkey_doctor_report`
- `saymo.commands.core`
  - `saymo auto` already reads the command queue and applies actions.
  - `saymo live-control-action` already queues normalized actions.
  - `saymo live-control` already opens the TUI.
- Phase 37 call-ready checks already expose provider/audio/hotkey permission
  blockers and prove default provider/audio checks are non-destructive.

## Required User-Facing Outcomes

1. CLI can install, uninstall, start, stop, restart, and inspect a per-profile
   LaunchAgent.
2. A foreground daemon command can register configured hotkeys and publish a
   fresh heartbeat/status for the selected profile.
3. Readiness/status can distinguish installed, loaded, running, stale heartbeat,
   crash-loop/log evidence, permission blockers, and plist drift.
4. Existing live-control actions can be queued through daemon/status surfaces
   with the same command semantics and audit trail as CLI/hotkeys.
5. Handbrake reachability is proven from heartbeat freshness, hotkey
   registration, command write/consume evidence, and latest applied action.

## Guardrails

- Do not create cron jobs. Use LaunchAgent plist files only.
- Default readiness/status commands must be read-only unless command names
  explicitly imply mutation: install, uninstall, start, stop, restart,
  kickstart, or action queueing.
- Do not kill Chrome, leave a meeting, switch microphones, play audio, record
  audio, transcribe, synthesize, write user config, or change macOS audio routes
  from the daemon readiness path.
- Do not move realtime audio/STT/TTS/provider ownership into the daemon.
- Keep all artifacts sanitized: no raw meeting content, transcripts, generated
  answers, audio bytes, or secrets.
- LaunchAgent labels should be stable and reverse-DNS style, e.g.
  `com.mshegolev.saymo.call-control.<profile>`.
- Treat labels and plist paths as generated from a sanitized profile only.

### Claude's Discretion

## Suggested Module Boundaries

- `saymo.analysis.control_daemon`
  - heartbeat/status dataclasses
  - daemon run loop primitives
  - command consumption/readiness helpers
- `saymo.analysis.launch_agent`
  - plist model/rendering
  - install/uninstall/status helpers
  - launchctl command wrappers with testable command construction
- CLI additions in `saymo.commands.core` or a focused command module:
  - `saymo call-control-daemon`
  - `saymo call-control-agent install|uninstall|start|stop|restart|status`
  - optional `saymo call-control-status`

## Validation Strategy

- Unit tests for plist rendering, labels, paths, env variables, and logs.
- Unit tests for daemon heartbeat and command/audit semantics without running a
  real LaunchAgent.
- CLI tests with mocked `launchctl` and hotkey probes.
- Static grep/tests proving daemon readiness does not perform audio/provider
  mutations.
- Manual macOS check remains required for actual LaunchAgent bootstrap in the
  user's GUI session.

## Open Design Questions Resolved by Assumption

- **Profile scope:** per-profile daemon and LaunchAgent, defaulting to
  `standup`, because current live-control files are profile-scoped.
- **Daemon lifetime:** long-running foreground process for tests/manual debug;
  LaunchAgent wraps the same command for background use.
- **Heartbeat cadence:** short interval suitable for readiness checks; exact
  default should be tuned in implementation plan and configurable/testable.
- **Command consumption:** daemon should consume command queue evidence for
  handbrake reachability, but actual realtime action application remains in
  `saymo auto` until Phase 39 explicitly gates realtime behavior.

### Deferred Ideas (OUT OF SCOPE)

No explicit Deferred Ideas section exists in `38-CONTEXT.md`. The out-of-scope
guardrails above are the binding scope limits for Phase 38.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CTRL-01 | User can install, start, stop, restart, and inspect a per-profile Saymo call-control LaunchAgent from CLI commands. | Add `saymo.analysis.launch_agent` for plist rendering, filesystem paths, and testable `launchctl` argv helpers. Add a focused Click command module for agent lifecycle. |
| CTRL-02 | User can run a foreground call-control daemon that registers configured global hotkeys and publishes a fresh heartbeat/status for the selected profile. | Add `saymo.analysis.control_daemon` with a foreground run loop, `pynput.GlobalHotKeys` registration through existing binding helpers, and periodic heartbeat JSON under the existing profile control dir. |
| CTRL-03 | User can see whether the call-control daemon is installed, loaded, running, stale, crash-looping, missing permissions, or using an outdated LaunchAgent plist. | Combine plist existence/hash, `plutil -lint`, best-effort `launchctl print`, daemon heartbeat freshness, daemon-reported hotkey registration status, and log paths into one read-only status/readiness result. |
| CTRL-04 | User can queue the existing live-control actions from the daemon or status surface with the same semantics and audit trail as CLI and current hotkeys. | Route daemon hotkeys and explicit action commands through `append_control_command()` plus `normalize_action()`. Keep `saymo auto` as the action applier/audit writer; add audit correlation fields if needed for probe evidence. |
| CTRL-05 | User can prove the handbrake is reachable before realtime mode by checking heartbeat freshness, hotkey registration, command write, command consumption, and latest applied action evidence. | Add an explicit reachability probe that writes a sanitized command with a probe id, waits for consumption/applied audit evidence, and reports command/audit/log paths without playing audio or touching provider state. |
</phase_requirements>

## Summary

Phase 38 should extend the existing live-control contract rather than replace it. The codebase already has durable command, state, audit, action normalization, and hotkey binding helpers in `saymo.analysis.live_control`; `saymo auto` already applies queued commands and writes the audit trail. The missing layer is a separate control-plane process that can own global hotkey registration outside an interactive terminal and publish heartbeat evidence for `call-ready` and future realtime gates.

Use two new analysis modules. `saymo.analysis.control_daemon` should own daemon heartbeat/status files, foreground daemon loop, hotkey registration, and reachability probes. `saymo.analysis.launch_agent` should own plist rendering, per-profile LaunchAgent paths, label generation, expected-plist hashing, and testable `launchctl` command construction. CLI commands should stay thin, and default status/readiness must stay read-only.

**Primary recommendation:** Build a foreground daemon first, then wrap it with a per-profile user LaunchAgent; route all daemon hotkeys/actions through the existing `commands.jsonl` queue and use heartbeat plus audit correlation as the proof that the handbrake is reachable.

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| Python | `>=3.11`; local `3.12.1` through `uv run python` | Runtime for daemon, plist generation, tests | Existing Saymo runtime and stdlib are sufficient. |
| `plistlib` | stdlib in Python `3.12.1` | Generate and parse LaunchAgent plists | Official Python API for Apple property lists; avoids hand-written XML. |
| `launchd` / `launchctl` | local `launchd 7.0.0` on macOS `14.4.1` | User LaunchAgent lifecycle and status | macOS-native process manager. Project rule explicitly says launchd, not cron. |
| `plutil` | system tool at `/usr/bin/plutil` | Validate rendered plist syntax | Built-in macOS syntax check; easy to mock by argv construction. |
| `click` | repo installed `8.3.2`; PyPI latest `8.4.2` published 2026-06-24 | CLI lifecycle commands | Existing Saymo command framework. Do not upgrade as part of Phase 38. |
| `pynput` | repo installed `1.8.1`; PyPI latest `1.8.2` published 2026-05-12 | Global hotkey listener | Existing hotkey doctor and auto-mode use `keyboard.GlobalHotKeys`. |
| `pytest` | repo installed `9.0.3`; PyPI latest `9.1.1` published 2026-06-19 | Unit and CLI regression tests | Existing project test suite. No test framework change. |

### Supporting

| Module / Tool | Purpose | When to Use |
|---------------|---------|-------------|
| `saymo.analysis.live_control` | Existing actions, command queue, state, audit, hotkey bindings | Always use for action semantics and profile-scoped file paths. |
| `saymo.analysis.launch_readiness` | Shared `LaunchReadinessCheck` / `LaunchReadinessReport` | Add daemon status rows to `call-ready` output/artifacts. |
| `saymo.analysis.provider_audio_readiness` | Hotkey permission checks from Phase 37 | Reuse or mirror its permission semantics; do not duplicate permission wording. |
| `saymo.analysis.remediation` | Grouped launch remediation | Add daemon/check categories here instead of adding another renderer. |
| `subprocess.run(..., args=list[str])` | Invoke `launchctl` / `plutil` | Use list argv only; no shell command strings. |
| Local man pages | `man launchctl`, `man launchd.plist` | Treat as the operational reference for this host. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| User LaunchAgent | cron | Forbidden by project rules; cron lacks GUI-session semantics and reliable user environment. |
| `plistlib` | Hand-written plist XML strings | XML escaping, type correctness, and drift are easy to get wrong. |
| `commands.jsonl` queue | Socket/XPC API | Queue already exists, is durable, profile-scoped, and tested; XPC would exceed phase scope. |
| `launchctl print` as primary truth | Heartbeat file | `launchctl print` output is explicitly not a stable API; use it only as best-effort loaded/last-exit detail. Heartbeat is the running proof. |
| Daemon applies realtime actions directly | `saymo auto` applies queued commands | Direct application would move realtime/provider ownership into daemon and violate context guardrails. |

**Installation:**

```bash
uv sync
```

No new dependency is required. Use system `/bin/launchctl`, `/usr/bin/plutil`, Python stdlib `plistlib`, existing `pynput`, and existing `click`.

**Version verification:**

```bash
uv pip show click pynput pytest
curl -s https://pypi.org/pypi/click/json | jq -r '.info.version'
curl -s https://pypi.org/pypi/pynput/json | jq -r '.info.version'
curl -s https://pypi.org/pypi/pytest/json | jq -r '.info.version'
launchctl version
sw_vers
```

Verified on 2026-07-08: local `click 8.3.2`, `pynput 1.8.1`, `pytest 9.0.3`; PyPI latests are newer but dependency upgrades are out of scope. Host launchd is `Darwin Bootstrapper Version 7.0.0` on macOS `14.4.1`.

## Architecture Patterns

### Recommended Project Structure

```text
saymo/
  analysis/
    control_daemon.py       # daemon heartbeat, foreground run loop, reachability probe
    launch_agent.py         # plist model/render, launchctl argv/status helpers
    launch_readiness.py     # append daemon readiness checks after provider/audio rows
    live_control.py         # existing action queue/state/audit primitives; extend only if needed
    remediation.py          # daemon remediation categories and hints
  commands/
    call_control.py         # new Click commands; imported from saymo.commands.__init__
tests/
  analysis/
    test_control_daemon.py
    test_launch_agent.py
    test_launch_readiness.py
  test_call_control_cli.py
  test_live_control_cli.py
  test_hotkey_doctor.py
  test_live_control_docs.py
docs/
  LIVE-CONTROL-HANDBRAKE.md # update existing guide instead of creating a competing doc first
```

### Pattern 1: Daemon Heartbeat Separate From Operator State

**What:** Keep `state.json` as the operator-facing auto-mode snapshot. Add a separate daemon heartbeat file, for example `daemon-heartbeat.json`, under the same `~/.saymo/live_control/<profile>/` directory.

**When to use:** Any status/readiness code that needs to decide whether the background handbrake process is alive.

**Example:**

```python
# Source: repo pattern from saymo.analysis.live_control path helpers
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from saymo.analysis.live_control import live_control_dir


@dataclass(frozen=True)
class ControlDaemonHeartbeat:
    profile: str
    pid: int
    label: str
    started_at: str
    heartbeat_at: str
    hotkeys_active: bool
    hotkey_registration_status: str
    hotkey_registration_detail: str


def daemon_heartbeat_path(profile: str, *, base_dir=None):
    return live_control_dir(profile, base_dir=base_dir) / "daemon-heartbeat.json"
```

**Notes:**
- Do not treat `LiveControlSnapshot.updated_at` as a daemon heartbeat. Current `saymo auto` updates it on state changes, not periodically.
- Heartbeat should include enough metadata for read-only status to avoid creating a new hotkey probe on every check.

### Pattern 2: Daemon Hotkeys Queue Existing Commands

**What:** The daemon registers global hotkeys and appends normalized commands to `commands.jsonl`. It does not stop playback, switch microphones, transcribe, synthesize, or call provider APIs.

**When to use:** All daemon hotkey callbacks and any explicit daemon/status action command.

**Example:**

```python
# Source: repo pattern from saymo.commands.core and saymo.analysis.live_control
from saymo.analysis.live_control import append_control_command, hotkey_listener_bindings


def _daemon_hotkey(profile: str, action: str):
    return lambda: append_control_command(
        profile,
        action,
        source="daemon_hotkey",
    )


bindings = hotkey_listener_bindings(config, {
    "toggle_auto_answer": _daemon_hotkey(profile, "toggle_auto_answer"),
    "speak": _daemon_hotkey(profile, "speak"),
    "stop": _daemon_hotkey(profile, "stop"),
    "takeover": _daemon_hotkey(profile, "takeover"),
    "approved_speak": _daemon_hotkey(profile, "approved_speak"),
    "skip_current": _daemon_hotkey(profile, "skip_current"),
    "capture_marker": _daemon_hotkey(profile, "capture_marker"),
    "status": _daemon_hotkey(profile, "status"),
    "hard_disable": _daemon_hotkey(profile, "hard_disable"),
})
```

**Important integration issue:** `saymo auto` currently also registers the same configured global hotkeys and applies them directly. Phase 38 must prevent duplicate action delivery when the daemon is healthy, either by centralizing hotkey registration in the daemon path or by adding an auto-mode option/internal branch that skips auto's local hotkey listener when daemon heartbeat is expected.

### Pattern 3: Plist Model Rendered By `plistlib`

**What:** Build a plain dictionary with required LaunchAgent keys and write it with `plistlib.dump(..., fmt=plistlib.FMT_XML)`.

**When to use:** Install/update commands and drift checks.

**Example:**

```python
# Source: Python official plistlib docs and Apple launchd.plist keys
import plistlib


def render_launch_agent_plist(spec):
    return {
        "Label": spec.label,
        "ProgramArguments": [
            spec.saymo_executable,
            "call-control-daemon",
            "--profile",
            spec.profile,
            "--heartbeat-interval",
            str(spec.heartbeat_interval_seconds),
        ],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "WorkingDirectory": spec.working_directory,
        "EnvironmentVariables": {
            "HOME": spec.home,
            "PATH": spec.path,
            "PYTHONUNBUFFERED": "1",
            "NO_PROXY": "localhost,127.0.0.1",
        },
        "StandardOutPath": spec.stdout_log_path,
        "StandardErrorPath": spec.stderr_log_path,
        "ThrottleInterval": 10,
    }
```

**Notes:**
- The first `ProgramArguments` element should be an absolute executable path where possible. Tests should pass an explicit fake executable path.
- Use a generic source label prefix such as `com.saymo.call-control.<profile>` unless a configurable local prefix is explicitly added. The context example uses `com.mshegolev...`, but source should not hardcode a personal name.
- Use sanitized profile labels through the existing live-control safe profile behavior or a shared helper with the same character policy.

### Pattern 4: Launchctl Command Construction Is Pure And Testable

**What:** Build `launchctl` argv as lists in helpers, then run them through one injectable subprocess boundary.

**When to use:** `install`, `uninstall`, `start`, `stop`, `restart`, and `status` CLI commands.

**Example:**

```python
# Source: local man launchctl on macOS 14.4.1
def bootstrap_argv(uid: int, plist_path: str) -> list[str]:
    return ["/bin/launchctl", "bootstrap", f"gui/{uid}", plist_path]


def bootout_argv(uid: int, label: str) -> list[str]:
    return ["/bin/launchctl", "bootout", f"gui/{uid}/{label}"]


def kickstart_argv(uid: int, label: str, *, restart: bool = False) -> list[str]:
    args = ["/bin/launchctl", "kickstart"]
    if restart:
        args.append("-k")
    args.append(f"gui/{uid}/{label}")
    return args


def print_argv(uid: int, label: str) -> list[str]:
    return ["/bin/launchctl", "print", f"gui/{uid}/{label}"]
```

**Notes:**
- Use the GUI domain (`gui/<uid>`) for user LaunchAgents and hotkeys, not the background user domain.
- Treat `launchctl print` output as diagnostic text, not as a stable machine contract. Loaded status can use return code; running status should prefer fresh heartbeat.

### Pattern 5: Daemon Readiness As LaunchReadinessCheck Rows

**What:** Add one or more daemon checks to `collect_launch_readiness()` after provider/audio checks.

**When to use:** `saymo call-ready` and future Phase 39 realtime gate.

**Recommended rows:**
- `call_control_agent`: installed/loaded/plist drift/log path state.
- `call_control_daemon`: heartbeat freshness, pid, label, running state.
- `call_control_hotkeys`: daemon-reported hotkey registration status and binding count.
- `call_control_reachability`: optional explicit probe result. Do not queue a probe from default `call-ready` unless a `--probe`/explicit command is provided.

**Example:**

```python
# Source: repo pattern from saymo.analysis.launch_readiness
LaunchReadinessCheck(
    key="call_control_daemon",
    label="call-control daemon",
    severity="block",
    ok=status.heartbeat_fresh and status.hotkeys_active,
    detail=status.detail,
    action=status.action,
    rerun=f"saymo call-control-agent status -p {profile}",
    metadata=status.to_metadata(),
)
```

### Anti-Patterns to Avoid

- **Cron or shell-profile-dependent background jobs:** Use LaunchAgent only, with explicit `HOME` and `PATH`.
- **Hand-written XML plist strings:** Use `plistlib` and validate with `plutil -lint`.
- **Shell-quoted launchctl commands:** Use list argv. Tests should assert exact arrays.
- **Parsing `launchctl print` as a stable API:** The local man page says its output can change without warning.
- **Daemon applying realtime actions directly:** Queue commands. Let `saymo auto` apply and audit.
- **Duplicate global hotkey listeners:** Do not let daemon and auto both register the same hotkeys during the trusted realtime path.
- **Default status that mutates state:** No `bootstrap`, `kickstart`, command append, audio, provider, or TCC-changing probes from read-only readiness.
- **Treating terminal hotkey-doctor as LaunchAgent proof:** LaunchAgent TCC identity can differ from a terminal-run process. Prefer daemon-reported registration evidence.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plist serialization | Manual XML templates | `plistlib.dump` / `plistlib.loads` | Handles plist types and escaping; easy to unit-test. |
| Agent management shell strings | `f"launchctl ..."` with shell quoting | `subprocess.run(list_argv)` through launch_agent helpers | Prevents quoting bugs and makes argv exact in tests. |
| Action aliases and validation | New action parser | `live_control.normalize_action()` and `ACTION_CATALOG` | Existing CLI/docs/hotkeys already use these semantics. |
| Command queue | Socket, HTTP server, or polling a new file | Existing `append_control_command()` / `read_control_commands()` | Durable, profile-scoped, tested, and already consumed by `saymo auto`. |
| Audit trail | A second daemon audit schema | Existing `append_control_audit()` extended only for sanitized correlation fields | Scorecards and safety checks already read the live-control audit log. |
| Hotkey config discovery | New config keys | `effective_hotkey_bindings()` / `hotkey_listener_bindings()` | Existing defaults and config.example stay authoritative. |
| Launch gate output | Separate daemon status renderer | `LaunchReadinessCheck` and `remediation.hints_from_launch_readiness()` | Keeps `call-ready`, JSON artifacts, and future realtime gate aligned. |

**Key insight:** Phase 38 is not a new control protocol. It is availability evidence for the existing handbrake. The safest design keeps action application in the realtime loop and makes the daemon prove "I can receive hotkeys and write commands" plus "the realtime loop consumed/applied a probe command."

## Common Pitfalls

### Pitfall 1: Duplicate Hotkey Registration

**What goes wrong:** Both the daemon and `saymo auto` register the same global shortcuts, so one key press queues/applies an action twice.

**Why it happens:** Current `saymo auto` owns hotkey registration inside `_auto()`; Phase 38 adds a second process that must own hotkeys outside the terminal.

**How to avoid:** Make the daemon the trusted hotkey owner when heartbeat is healthy. Add an auto-mode internal switch or startup branch to skip local hotkey registration when daemon control is enabled.

**Warning signs:** Tests show two queued commands for one hotkey; audit log has duplicate `stop` or `toggle_auto_answer` events with the same timestamp.

### Pitfall 2: Treating `launchctl print` Output As API

**What goes wrong:** Status works on one macOS release and fails on another because text fields change.

**Why it happens:** `launchctl print` is useful diagnostic output, but the local man page says it is not API.

**How to avoid:** Use `launchctl print` return code and raw excerpts as best-effort loaded/crash evidence. Use heartbeat freshness for running status and plist hash for drift.

**Warning signs:** Tests assert a long exact `launchctl print` fixture instead of return code plus a small number of robust extracted fields.

### Pitfall 3: LaunchAgent Environment Depends On Shell Profiles

**What goes wrong:** The daemon works from an activated terminal but fails under launchd because PATH, HOME, config path, or Python environment is missing.

**Why it happens:** LaunchAgents do not run inside the user's interactive shell profile.

**How to avoid:** Render explicit `ProgramArguments`, `WorkingDirectory` when needed, `EnvironmentVariables` with `HOME` and `PATH`, and stdout/stderr paths. Prefer an absolute `saymo` executable path.

**Warning signs:** Agent status shows loaded but heartbeat never appears; stderr log contains `saymo: command not found` or import errors.

### Pitfall 4: Fast Exit Becomes Crash Loop Or Throttle

**What goes wrong:** launchd throttles the job, and status reports stale heartbeat even after restart attempts.

**Why it happens:** launchd treats rapid repeated exits as unhealthy; Apple docs warn against daemons exiting too quickly after launch.

**How to avoid:** The daemon should stay alive even if hotkey registration fails, write a heartbeat with `hotkeys_active=false`, and expose permission remediation. Use `ThrottleInterval` and surface recent exit/log evidence.

**Warning signs:** Log shows repeated startup lines; `launchctl print` has recent non-zero exits; heartbeat timestamp stays stale.

### Pitfall 5: Readiness Commands Mutate Live Call State

**What goes wrong:** A "status" or "call-ready" check starts the daemon, queues a command, switches audio, or touches Chrome.

**Why it happens:** It is tempting to prove reachability by running the repair path inside status.

**How to avoid:** Default status/readiness is read-only. Mutations are explicit commands: `install`, `uninstall`, `start`, `stop`, `restart`, `action`, and `probe`.

**Warning signs:** Tests need to mock `append_control_command`, `bootstrap`, `kickstart`, provider methods, playback, or audio route mutation just to run default status.

### Pitfall 6: Probe Cannot Prove Consumption

**What goes wrong:** The CLI can prove a command was written, but not that `saymo auto` consumed and applied it.

**Why it happens:** Existing `append_control_audit()` records action/source/result but not `command_id` or payload. Existing `_apply_control_action()` ignores `LiveControlCommand.payload`.

**How to avoid:** Add backward-compatible optional audit fields such as `command_id` and sanitized `probe_id`, and have command-loop application pass those fields into the audit event. Until that exists, mark command-consumption proof as unavailable.

**Warning signs:** Reachability probe passes when `commands.jsonl` grows even though `audit.jsonl` has no matching applied event.

### Pitfall 7: Terminal Permission Probe Is Not Agent Permission Proof

**What goes wrong:** `saymo hotkey-doctor` passes in Terminal, but the LaunchAgent daemon cannot register hotkeys.

**Why it happens:** macOS TCC/Accessibility permissions can be tied to the actual process identity that requests access.

**How to avoid:** The daemon itself must record hotkey registration status/detail in heartbeat. Status should prefer daemon-reported permission status over a terminal-run probe.

**Warning signs:** `hotkey-doctor --no-probe` shows bindings, but daemon heartbeat says `blocked` or no heartbeat appears.

## Code Examples

Verified patterns from official and repo sources:

### Existing Command Queue Append

```python
# Source: saymo.analysis.live_control
path = append_control_command(profile, action, source="cli", base_dir=base_dir)
```

Use the same primitive for daemon hotkeys and explicit daemon action commands. Change `source` to `daemon_hotkey`, `daemon_cli`, or `probe`.

### Existing Auto-Mode Command Consumption

```python
# Source: saymo.commands.core
commands, control_offset = await asyncio.to_thread(
    read_control_commands,
    profile,
    offset=control_offset,
)
for command in commands:
    _apply_control_action(command.action, command.source)
```

Phase 38 should extend this seam only as needed for audit correlation. Do not move `_apply_control_action()` into the daemon.

### LaunchAgent Plist Round Trip

```python
# Source: Python official plistlib docs
import plistlib

payload = render_launch_agent_plist(spec)
with spec.plist_path.open("wb") as fh:
    plistlib.dump(payload, fh, fmt=plistlib.FMT_XML)

with spec.plist_path.open("rb") as fh:
    loaded = plistlib.load(fh)
assert loaded["Label"] == spec.label
```

### Read-Only Daemon Status Skeleton

```python
# Source: Apple launchctl docs plus repo launch readiness pattern
def collect_call_control_status(spec, *, now):
    plist_exists = spec.plist_path.exists()
    plist_current = plist_exists and expected_plist_hash(spec) == installed_plist_hash(spec)
    launchctl_result = run_launchctl(print_argv(spec.uid, spec.label), check=False)
    heartbeat = load_daemon_heartbeat(spec.profile)

    return ControlDaemonStatus(
        installed=plist_exists,
        plist_current=plist_current,
        loaded=launchctl_result.returncode == 0,
        heartbeat_fresh=heartbeat_is_fresh(heartbeat, now=now),
        hotkeys_active=bool(heartbeat and heartbeat.hotkeys_active),
        stdout_log_path=spec.stdout_log_path,
        stderr_log_path=spec.stderr_log_path,
    )
```

### Explicit Mutating Commands

```python
# Source: local man launchctl
install = write_plist(spec)                 # file mutation
start = run_launchctl(bootstrap_argv(uid, spec.plist_path))
restart = run_launchctl(kickstart_argv(uid, spec.label, restart=True))
stop = run_launchctl(bootout_argv(uid, spec.label))
```

Default `status` should not call any of these.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Terminal-owned `saymo auto` hotkeys only | Dedicated control-plane daemon plus LaunchAgent owns hotkey availability | Phase 38 | Handbrake can be checked before realtime mode relies on it. |
| `launchctl load/unload` legacy commands | `launchctl bootstrap`, `bootout`, `kickstart`, `print` against `gui/<uid>` | Current macOS man page | Use modern command construction and keep legacy commands out of new code. |
| Manual plist XML | `plistlib` generated XML plus `plutil -lint` | Python stdlib supports plist generation | Safer plist output and easy tests. |
| Process detection via `ps` for `saymo auto` | Heartbeat JSON from actual daemon | Phase 38 | Running/stale status becomes deterministic and profile-scoped. |
| Status via terminal-only hotkey doctor | Daemon-reported hotkey registration in heartbeat | Phase 38 | LaunchAgent TCC failures become visible before a live call. |

**Deprecated/outdated:**
- `cron` for macOS scheduling: project rule forbids it; use LaunchAgent.
- `launchctl load/unload` for new lifecycle code: local man page marks them legacy and recommends `bootstrap`/`bootout`/`enable`/`disable`.
- Relying on `Disabled` plist key for loaded state: launchd stores disabled state externally; use `launchctl` state plus heartbeat.

## Exact Integration Points

| File | Current Primitive | Phase 38 Use |
|------|-------------------|--------------|
| `saymo/analysis/live_control.py:14` | `PRIMARY_ACTIONS` / `OPTIONAL_ACTIONS` / `ACTION_CATALOG` | Do not define new action names for daemon lifecycle. Queue existing actions only. |
| `saymo/analysis/live_control.py:105` | `LiveControlCommand` includes `payload` and `command_id` | Use for reachability probe correlation; extend auto/audit path to preserve ids if needed. |
| `saymo/analysis/live_control.py:179` | `live_control_dir(profile)` creates `~/.saymo/live_control/<profile>` | Store daemon heartbeat/status beside existing files. |
| `saymo/analysis/live_control.py:205` | `append_control_command()` | Daemon hotkeys and explicit action commands should call this. |
| `saymo/analysis/live_control.py:225` | `read_control_commands(offset=...)` | `saymo auto` already consumes the queue; probe waits for this consumption to surface in audit/state. |
| `saymo/analysis/live_control.py:259` | `write_live_state()` / `load_live_state()` | Keep as realtime/operator state; do not overload as heartbeat. |
| `saymo/analysis/live_control.py:301` | `append_control_audit()` | Extend only if needed with optional sanitized correlation fields. |
| `saymo/analysis/live_control.py:330` | `effective_hotkey_bindings()` | Daemon should read hotkey config through this helper. |
| `saymo/analysis/live_control.py:342` | `hotkey_listener_bindings()` | Daemon should register configured actions through this helper. |
| `saymo/analysis/live_control.py:364` | `build_hotkey_doctor_report()` | Reuse for doctor/remediation, but do not treat terminal probe as daemon proof. |
| `saymo/commands/core.py:431` | `_apply_control_action()` nested inside `_auto()` | Leave action application in auto. Consider extracting only if needed for testability, not to let daemon mutate realtime state. |
| `saymo/commands/core.py:546` | Auto-mode hotkey listener | Must avoid duplicate listener when daemon is the hotkey owner. |
| `saymo/commands/core.py:585` | `_control_command_loop()` | Add command id/payload propagation for probe evidence if needed. |
| `saymo/commands/core.py:970` | `live-control-action` queues one action | New daemon action command should reuse the same semantics or delegate to this helper path. |
| `saymo/analysis/provider_audio_readiness.py:258` | Permission checks include hotkey Accessibility row | Phase 38 daemon readiness should align remediation categories and wording. |
| `saymo/analysis/launch_readiness.py:93` | `collect_launch_readiness()` | Append daemon readiness rows here so `call-ready` becomes the launch gate for Phase 39. |
| `saymo/commands/call_ready.py:18` | Thin Click wrapper | Do not create a second readiness command for launch health. Add daemon rows through the collector. |
| `docs/LIVE-CONTROL-HANDBRAKE.md:6` | Current before-call operator guide | Update in Plan 38-05 with LaunchAgent/daemon/probe flow. |

## Non-Destructive And Mutating Semantics

### Read-Only By Default

These commands/checks should only read files, validate plist syntax, inspect launchd status, and render output:

- `saymo call-control-agent status -p <profile>`
- `saymo call-control-status -p <profile>` if added
- `saymo call-ready -p <profile> --provider <provider>` daemon rows
- `saymo hotkey-doctor -p <profile> --no-probe`

Allowed read-only operations:

- Read `~/.saymo/live_control/<profile>/daemon-heartbeat.json`.
- Read `state.json`, `commands.jsonl` size/offset, and `audit.jsonl` latest event.
- Check plist existence and compare rendered expected hash.
- Run `/usr/bin/plutil -lint <plist>`.
- Run `/bin/launchctl print gui/<uid>/<label>` and capture return code/output.
- Render log paths and recent sanitized tail excerpts if needed.

### Explicit Mutations

These command names may mutate state because their names say so:

- `install`: create/update plist and log directories; optionally validate plist.
- `uninstall`: boot out loaded service if needed, then remove plist.
- `start`: bootstrap the installed plist into `gui/<uid>` and optionally kickstart.
- `stop`: bootout `gui/<uid>/<label>`.
- `restart`: `kickstart -k gui/<uid>/<label>` or bootout/bootstrap if needed.
- `action`: append a normalized action to `commands.jsonl`.
- `probe`: append a unique sanitized probe command and wait for consumption/applied audit evidence.

Explicit mutations must still avoid Chrome, meeting, audio route, playback, recording, transcription, synthesis, and config writes.

## Risks And Gaps For CTRL-01..CTRL-05

| Requirement | Risk / Gap | Recommendation |
|-------------|------------|----------------|
| CTRL-01 | No LaunchAgent helper, no plist renderer, no lifecycle CLI. | Implement `launch_agent.py` first with pure path/label/argv/plist helpers and mocked CLI tests. |
| CTRL-01 | Hardcoded personal label prefix would conflict with source rule: no personal data in source. | Use generic default label prefix such as `com.saymo.call-control`, or make the prefix configurable. Keep profile sanitized. |
| CTRL-02 | No standalone daemon; current hotkeys live inside `saymo auto`. | Add `call-control-daemon` foreground command that registers hotkeys and writes heartbeat without owning audio/provider behavior. |
| CTRL-02 | Hotkey registration failures could make the daemon exit and launchd throttle it. | Keep daemon alive and report `hotkeys_active=false` with permission detail in heartbeat. |
| CTRL-03 | `build_hotkey_doctor_report()` detects `saymo auto`, not the daemon. | Add daemon-specific status based on heartbeat and launchd label; leave hotkey doctor as a supporting permission probe. |
| CTRL-03 | `launchctl print` output is not stable. | Parse minimally; status truth comes from plist/hash/return code/heartbeat/log paths. |
| CTRL-04 | Current auto hotkeys apply actions directly; daemon hotkeys should queue commands. | Normalize command semantics around the queue and ensure auto does not double-register hotkeys in the trusted daemon mode. |
| CTRL-04 | Existing audit does not carry `command_id` or probe payload. | Add optional sanitized correlation fields to `append_control_audit()` and pass them from `_control_command_loop()`. |
| CTRL-05 | Command write can pass when auto is not consuming commands. | Probe must require matching audit/latest-action evidence, not just command file growth. |
| CTRL-05 | Actual LaunchAgent TCC behavior can differ from terminal behavior. | Manual GUI-session verification remains required after automated tests. Heartbeat must record daemon-side hotkey registration status. |

## Recommended Plan Breakdown

### 38-01: Add foreground call-control daemon lifecycle and heartbeat model

**Scope:**
- Add `saymo.analysis.control_daemon`.
- Add heartbeat dataclass/path/load/write/freshness helpers.
- Add foreground `run_control_daemon()` loop with configurable heartbeat interval.
- Register configured global hotkeys through `hotkey_listener_bindings()`.
- Hotkey callbacks append existing live-control commands with source `daemon_hotkey`.
- Keep daemon alive with `hotkeys_active=false` if registration fails.

**Tests:**
- `tests/analysis/test_control_daemon.py` for heartbeat writes/freshness/stale/future timestamps.
- Mock `pynput.keyboard.GlobalHotKeys` and assert bindings queue commands.
- Assert daemon helpers do not import/call provider/audio/TTS/STT modules.

### 38-02: Add LaunchAgent install, start, stop, restart, and status commands

**Scope:**
- Add `saymo.analysis.launch_agent`.
- Render plist with `plistlib`, explicit `HOME`, `PATH`, stdout/stderr logs, `RunAtLoad`, `KeepAlive`, and `ThrottleInterval`.
- Add pure argv builders for `bootstrap`, `bootout`, `kickstart`, `print`, and `plutil -lint`.
- Add Click commands in a focused module, imported by `saymo.commands.__init__`.

**Tests:**
- Round-trip plist through `plistlib.loads`.
- Assert exact launchctl argv lists.
- CLI tests with mocked subprocess boundary and tmp home.
- No real LaunchAgent bootstrap in automated tests.

### 38-03: Add daemon health diagnostics for stale heartbeat, crashes, permissions, and plist drift

**Scope:**
- Add status dataclass combining installed, loaded, heartbeat freshness, hotkey registration, plist hash drift, and log paths.
- Add LaunchReadinessCheck rows for daemon/agent/hotkey status.
- Extend remediation categories for `call-control` and `macos-permission`.
- Keep default `call-ready` and status read-only.

**Tests:**
- Fresh heartbeat passes; stale heartbeat blocks.
- Missing plist, loaded false, crash evidence, permission blocked, and plist drift produce exact details/actions/reruns.
- CLI and artifact tests prove daemon rows appear in `call-ready`.

### 38-04: Route daemon/status actions through existing live-control command and audit semantics

**Scope:**
- Add explicit action queue command under daemon/status CLI surface or reuse/delegate to `live-control-action`.
- Ensure daemon hotkey/action sources are sanitized and visible.
- Add optional command/audit correlation fields (`command_id`, `probe_id`) without breaking existing audit tests.
- Address duplicate hotkey listener risk by centralizing trusted hotkeys in daemon mode or adding an auto startup skip path.

**Tests:**
- `stop`, `takeover`, `hard_disable`, `speak`, `skip` queue normalized commands.
- Existing `live-control-action` tests stay green.
- Auto command-loop audit tests prove command id/probe id is preserved.
- One simulated hotkey creates one command/action, not duplicates.

### 38-05: Add handbrake reachability probe, logs, docs, and tests

**Scope:**
- Add explicit `probe` command that writes a benign sanitized command, waits for consumption/applied audit evidence, and reports heartbeat, hotkey, command, audit, and log evidence.
- Update `docs/LIVE-CONTROL-HANDBRAKE.md` with daemon/LaunchAgent flow.
- Add log path output and troubleshooting guidance.
- Add static non-destructive grep/tests for status/readiness.

**Tests:**
- Probe passes only with fresh heartbeat plus matching audit evidence.
- Probe fails with command-written-but-not-consumed.
- Docs test covers LaunchAgent, status, probe, and Accessibility guidance.
- Static CLI test proves default status/readiness does not call launchctl mutators, provider mutators, audio playback/recording, or config writers.

## Open Questions

1. **Default LaunchAgent label prefix**
   - What we know: context gives `com.mshegolev.saymo.call-control.<profile>` as an example, but project rules forbid personal data in source.
   - What's unclear: whether generated local plists should default to a user-specific prefix.
   - Recommendation: default to `com.saymo.call-control.<profile>` in source and optionally allow a config/CLI override later.

2. **How `saymo auto` should skip duplicate hotkeys**
   - What we know: auto currently registers hotkeys directly and applies actions immediately.
   - What's unclear: whether Phase 38 should add a user-visible `--no-hotkeys` flag, an internal daemon-detected branch, or leave final gating to Phase 39.
   - Recommendation: add an internal reusable option/branch in Phase 38 so tests can prove no duplicate hotkey action occurs when daemon mode is enabled.

3. **Probe action choice**
   - What we know: `status` and `capture_marker` are benign existing actions, but both still create audit entries.
   - What's unclear: whether a dedicated `probe` action should join `ACTION_CATALOG`.
   - Recommendation: do not add a new user action unless necessary. Use `status` with `source="probe"` and a sanitized `probe_id` payload, then require matching audit evidence.

4. **LaunchAgent executable resolution**
   - What we know: LaunchAgent should not depend on shell activation. `saymo` is a project script, but dev runs may use `uv run`.
   - What's unclear: whether installed users will always have an absolute `saymo` executable.
   - Recommendation: make executable path an explicit field in `LaunchAgentSpec`, defaulting to resolved `shutil.which("saymo")` and blocking install/status with clear remediation if unresolved.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest `9.0.3` local |
| Config file | none |
| Quick run command | `uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q` |
| Current safety run command | `uv run pytest tests/analysis/test_live_control.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py tests/test_auto_qa_flow.py -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CTRL-01 | LaunchAgent install/start/stop/restart/status command construction and plist rendering | unit/CLI | `uv run pytest tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q` | no - Wave 0 |
| CTRL-02 | Foreground daemon registers hotkeys and writes fresh heartbeat/status | unit | `uv run pytest tests/analysis/test_control_daemon.py -q` | no - Wave 0 |
| CTRL-03 | Status distinguishes installed, loaded, running, stale, crash-loop, permission, and plist drift | unit/CLI | `uv run pytest tests/analysis/test_launch_agent.py tests/test_call_control_cli.py tests/analysis/test_launch_readiness.py -q` | partial - extend Wave 0 |
| CTRL-04 | Daemon/status actions queue existing live-control commands and preserve audit semantics | unit/integration | `uv run pytest tests/test_live_control_cli.py tests/test_auto_qa_flow.py -q` | partial - extend Wave 0 |
| CTRL-05 | Reachability probe proves heartbeat, hotkey registration, command write/consume, and latest applied action | unit/CLI/manual | `uv run pytest tests/analysis/test_control_daemon.py tests/test_call_control_cli.py -q` | no - Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/analysis/test_control_daemon.py tests/analysis/test_launch_agent.py tests/test_call_control_cli.py -q`
- **Per wave merge:** `uv run pytest tests/analysis/test_live_control.py tests/analysis/test_launch_readiness.py tests/test_live_control_cli.py tests/test_hotkey_doctor.py tests/test_call_ready_cli.py tests/test_auto_qa_flow.py -q`
- **Phase gate:** `uv run pytest`, `git diff --check`, plus a manual macOS GUI-session LaunchAgent smoke check before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/analysis/test_control_daemon.py` - covers CTRL-02 and CTRL-05 heartbeat/hotkey/probe helpers.
- [ ] `tests/analysis/test_launch_agent.py` - covers CTRL-01 and CTRL-03 plist, label, path, hash, and launchctl argv helpers.
- [ ] `tests/test_call_control_cli.py` - covers CTRL-01 through CTRL-05 CLI status/action/probe behavior with mocked subprocess/hotkey boundaries.
- [ ] `tests/analysis/test_launch_readiness.py` - extend with daemon `LaunchReadinessCheck` rows for CTRL-03.
- [ ] `tests/test_call_ready_cli.py` - extend with daemon readiness JSON/artifact and non-destructive assertions.
- [ ] `tests/test_live_control_cli.py` - extend action queue tests for daemon/status sources and payloads.
- [ ] `tests/test_auto_qa_flow.py` - extend command-loop/audit correlation tests and duplicate-hotkey prevention.
- [ ] `tests/test_live_control_docs.py` - extend docs expectations for LaunchAgent, status, probe, and logs.

## Sources

### Primary (HIGH confidence)

- `.planning/ROADMAP.md` - Phase 38 goal, dependencies, success criteria, and five-plan roadmap.
- `.planning/REQUIREMENTS.md` - CTRL-01 through CTRL-05 requirement wording.
- `.planning/STATE.md` - current v1.9 decisions, including daemon control-plane only and non-destructive provider/audio policy.
- `.planning/phases/38-local-call-control-daemon-and-launchagent/38-CONTEXT.md` - locked design direction, guardrails, module boundaries, validation strategy.
- `.planning/phases/37-provider-and-audio-remediation/37-VERIFICATION.md` - Phase 37 verified non-destructive provider/audio and permission behavior.
- `saymo/analysis/live_control.py` - existing action catalog, command/state/audit files, hotkey helpers, hotkey doctor.
- `saymo/commands/core.py` - current auto-mode action application, hotkey registration, command-loop consumption, and CLI action queue.
- `saymo/analysis/provider_audio_readiness.py` - permission check wiring and non-destructive launch-readiness patterns.
- `saymo/analysis/launch_readiness.py` and `saymo/commands/call_ready.py` - shared launch-readiness contract and CLI wrapper.
- `tests/analysis/test_live_control.py`, `tests/test_live_control_cli.py`, `tests/test_hotkey_doctor.py`, `tests/test_auto_qa_flow.py` - existing regression surface for commands, hotkeys, and handbrake semantics.
- `docs/LIVE-CONTROL-HANDBRAKE.md` - current operator docs; `docs/live-control.md` is not present.
- Apple Support, "Script management with launchd in Terminal on Mac" - launchd is the macOS mechanism for daemons/agents and `~/Library/LaunchAgents` is the per-user agent location: https://support.apple.com/guide/terminal/script-management-with-launchd-apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac
- Apple Developer archive, "Creating Launch Daemons and Agents" - required/recommended plist keys and launchd behavior guidance: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- Local `man launchctl` on macOS 14.4.1 - `bootstrap`, `bootout`, `kickstart`, `print`, GUI domain semantics, and warning that `print` output is not API.
- Local `man launchd.plist` on macOS 14.4.1 - daemon expectations, `ProgramArguments`, `KeepAlive`, `RunAtLoad`, `EnvironmentVariables`, `WorkingDirectory`, `StandardOutPath`, `StandardErrorPath`, and `ThrottleInterval`.
- Python official `plistlib` docs - plist generation/parsing API: https://docs.python.org/3/library/plistlib.html

### Secondary (MEDIUM confidence)

- PyPI JSON API checks for current latest package versions for `click`, `pynput`, and `pytest`; used only for version awareness, not for upgrade recommendation.

### Tertiary (LOW confidence)

- None used for implementation recommendations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies; repo-local versions and system tools were verified.
- Architecture: HIGH - directly mapped to existing live-control, call-ready, and command modules.
- LaunchAgent behavior: MEDIUM - official/local docs are clear, but actual GUI-session TCC and launchd behavior must still be manually checked on the user's macOS session.
- Pitfalls: HIGH for repo-local risks; MEDIUM for TCC-specific behavior because macOS permission identity varies by launcher.

**Research date:** 2026-07-08
**Valid until:** 2026-08-07 for repo-local architecture; 2026-07-15 for macOS launchd/TCC behavior if the host OS changes.

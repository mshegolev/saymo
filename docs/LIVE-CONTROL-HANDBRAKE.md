# Saymo Live Control Handbrake

Use the handbrake controls during a live call when Saymo is listening but you
want to stay in charge.

## Before The Call

```bash
./scripts/add_hotkeys.py
saymo auto-preflight -p personal
saymo hotkey-doctor -p personal
saymo takeover-check -p personal
saymo call-control-agent status -p personal
```

Global macOS hotkeys do not require the terminal window to be focused after
`saymo auto` has registered them. They do require a running Saymo process and
macOS Accessibility permission for the terminal app that launched Saymo.

For a terminal-independent handbrake, install and start the per-profile
LaunchAgent from your macOS GUI session:

```bash
saymo call-control-agent install -p personal
saymo call-control-agent start -p personal
saymo call-control-agent status -p personal
saymo call-control probe -p personal
```

The plist is written under `~/Library/LaunchAgents/` and the daemon logs are
under `~/.saymo/live_control/<profile>/logs/`. Status output prints the plist,
stdout, stderr, heartbeat, loaded/running state, and the next action. If
hotkeys are blocked, grant Accessibility permission to the app that launchd
uses to run Saymo, then restart the agent and rerun status.

## During The Call

Start Saymo:

```bash
saymo auto -p personal
```

Open the local button-style control surface in another terminal:

```bash
saymo live-control -p personal
```

The panel writes local commands to `~/.saymo/live_control/<profile>/`.
`saymo auto` reads those commands and applies the same control actions as the
global hotkeys.

You can also queue one action from scripts or third-party macOS launchers:

```bash
saymo live-control-action -p personal --action hard-disable
saymo live-control-action -p personal --action skip
saymo call-control action -p personal --action status
```

## Primary Controls

| Control | Default hotkey | Use when |
|---|---|---|
| Auto Answer | `Cmd+Shift+M` | You want Saymo to stop answering automatically, but keep a recoverable process running. |
| Speak | `Cmd+Shift+S` | You explicitly want the prepared cached response to play. |
| Stop | `Cmd+Shift+X` | Saymo is speaking and must stop immediately. |
| Takeover | `Cmd+Shift+U` | You want to answer with your real microphone. Press again to return to Saymo. |

## Optional Controls

| Control | Default hotkey | Use when |
|---|---|---|
| Approved Draft | `Cmd+Shift+A` | You want to request playback for an already approved draft through the cockpit path. |
| Skip | `Cmd+Shift+K` | Saymo caught a phrase but should ignore the current candidate. |
| Mark Capture | `Cmd+Shift+C` | You want a local marker for later review/training. |
| Status | `Cmd+Shift+I` | You want Saymo to print the live-control state and local paths. |
| Hard Disable | `Cmd+Shift+H` | Something is wrong: stop playback and keep auto-answer disabled until re-enabled. |

## Safety Rules

- Auto Answer off blocks automatic speaking.
- Manual takeover blocks automatic speaking and stops playback.
- Hard Disable stops playback, turns Auto Answer off, and keeps Saymo paused
  until Auto Answer is explicitly re-enabled.
- Explicit buttons/hotkeys are audited locally under
  `~/.saymo/live_control/<profile>/audit.jsonl`.
- The call-control daemon is control-plane only. It queues existing actions and
  writes heartbeat evidence; it does not transcribe, synthesize, play audio,
  switch microphones, change provider state, or own the realtime loop.

## LaunchAgent Smoke Check

Run this from the user's macOS GUI session before relying on the background
handbrake:

```bash
saymo call-control-agent install -p personal
saymo call-control-agent start -p personal
saymo call-control-agent status -p personal
saymo call-ready -p personal --provider glip
launchctl print gui/$(id -u)/com.saymo.call-control.personal
saymo call-control probe -p personal
```

Expected result:

- The LaunchAgent is loaded from `~/Library/LaunchAgents/`.
- `daemon-heartbeat.json` is fresh.
- Hotkey registration is `ok`, or status explains the Accessibility blocker.
- `saymo call-control probe -p personal` reports heartbeat, command, audit,
  stdout, and stderr paths.
- Logs are available in `~/.saymo/live_control/<profile>/logs/`.

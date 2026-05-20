# Phase 7 Context: Provider Latency Probe

## Goal

Measure end-to-end latency for active Chrome call providers so the user can
distinguish audio/STT delays from provider mute/playback delays.

## Baseline

- `saymo auto` already prints catch and playback latency during live use.
- Provider automation already exposes `check_ready`, `activate_meeting`,
  `toggle_mute`, `switch_mic`, `get_previous_app`, and `activate_app`.
- `auto-preflight` verifies provider readiness before a call, but it does not
  run a timed mute/playback probe or persist latency history.

## Decisions

- Add a dedicated `provider-latency` diagnostic command instead of changing
  `saymo auto`.
- Reuse the existing provider abstraction and BlackHole playback route.
- Keep blocked provider steps explicit in the report so the user knows whether
  tab discovery, unmute, playback, or mute recovery failed.
- Persist both JSON and Markdown history under profile/provider directories.

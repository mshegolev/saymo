# Phase 21 Context: Approved Draft Playback

## Goal

Let the user send only explicitly approved generated draft text into the live
call through existing local TTS and playback safety paths.

## Requirements

- COCK-03: route an explicitly approved answer draft through local TTS and
  playback devices.
- COCK-04: support preview/monitor, timeout, and max-duration controls.
- AUD-03: record playback audit events with draft id, route, TTS engine,
  timing, and blocked reasons.
- SAFE-01: refuse unapproved or empty generated text before synthesis/playback.

## Existing System

- v1.4 answer cockpit stores drafts as `pending`.
- `answer-cockpit action --action speak` previously recorded approval only.
- Existing TTS engines expose `synthesize(text) -> bytes`.
- Existing playback helpers can route bytes to one output or monitor devices.

## Design Decisions

- Keep `apply_cockpit_action` as a pure approval state transition.
- Wire playback only in the explicit CLI action path after `--action speak`.
- Keep `--no-playback` available for approval-only review.
- Block before TTS when approved text is empty or estimated duration exceeds
  `safety.max_speech_duration` / `--max-duration`.


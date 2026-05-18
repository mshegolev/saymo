# Summary 07-02: Segmented Provider/Playback Timings

## Completed

- Reported capture, transcription, trigger, provider check, mic switch,
  provider unmute, playback start, playback duration, and mute recovery.
- Measured playback start relative to the trigger decision.
- Reported blocked steps for provider tab, output device, unmute, playback, and
  mute recovery failures.

## Files

- `saymo/commands/tests.py`
- `tests/test_provider_latency.py`

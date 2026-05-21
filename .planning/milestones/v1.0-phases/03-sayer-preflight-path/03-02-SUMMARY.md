# Summary 03-02: Forced-Playback Blocked Reasons

## Completed

- `_play_cached_audio()` now returns `PlaybackResult`.
- Missing audio file, missing provider output, and missing provider tab have
  explicit reasons.
- Existing provider mute fallback tests still pass.

## Tests

- `test_play_cached_audio_returns_blocked_reason_for_missing_file`
- `test_play_cached_audio_falls_back_to_blackhole_when_provider_flow_fails`
- `test_play_cached_audio_does_not_replay_when_provider_fails_after_playback`


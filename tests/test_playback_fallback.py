"""Playback fallback tests for provider-controlled speaking."""

import asyncio
from types import SimpleNamespace

from saymo.commands import _play_cached_audio
from saymo.config import SaymoConfig


def _run(coro):
    return asyncio.run(coro)


def test_play_cached_audio_falls_back_to_blackhole_when_provider_flow_fails(
    tmp_path,
    monkeypatch,
):
    audio_path = tmp_path / "cached.wav"
    audio_path.write_bytes(b"wav-bytes")

    config = SaymoConfig()
    config.audio.monitor_device = ""

    class FailingProvider:
        name = "FailMeet"

        def check_ready(self):
            return SimpleNamespace(meeting_found=True)

        def switch_mic(self, device_name):
            return True

        async def unmute_speak_mute(self, speak_fn, *args, **kwargs):
            raise RuntimeError("mute automation failed")

    played = []

    async def fake_play_audio_bytes(audio_bytes, device_name):
        played.append((audio_bytes, device_name))

    monkeypatch.setattr(
        "saymo.providers.factory.get_provider",
        lambda provider_name: FailingProvider(),
    )
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda device_name, kind=None: object(),
    )
    monkeypatch.setattr(
        "saymo.audio.playback.play_audio_bytes",
        fake_play_audio_bytes,
    )

    _run(_play_cached_audio(config, audio_path, provider_name="failmeet"))

    assert played == [(b"wav-bytes", "BlackHole 2ch")]


def test_play_cached_audio_does_not_replay_when_provider_fails_after_playback(
    tmp_path,
    monkeypatch,
):
    audio_path = tmp_path / "cached.wav"
    audio_path.write_bytes(b"wav-bytes")

    config = SaymoConfig()
    config.audio.monitor_device = ""

    class LateFailingProvider:
        name = "LateFailMeet"

        def check_ready(self):
            return SimpleNamespace(meeting_found=True)

        def switch_mic(self, device_name):
            return True

        async def unmute_speak_mute(self, speak_fn, *args, **kwargs):
            await speak_fn(*args, **kwargs)
            raise RuntimeError("mute-back failed")

    played = []

    async def fake_play_audio_bytes(audio_bytes, device_name):
        played.append((audio_bytes, device_name))

    monkeypatch.setattr(
        "saymo.providers.factory.get_provider",
        lambda provider_name: LateFailingProvider(),
    )
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda device_name, kind=None: object(),
    )
    monkeypatch.setattr(
        "saymo.audio.playback.play_audio_bytes",
        fake_play_audio_bytes,
    )

    _run(_play_cached_audio(config, audio_path, provider_name="latefail"))

    assert played == [(b"wav-bytes", "BlackHole 2ch")]

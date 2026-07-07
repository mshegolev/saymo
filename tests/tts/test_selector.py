"""Tests for call-ready voice selector decisions."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import soundfile as sf

from saymo.analysis.voice_profile import (
    build_voice_profile_manifest,
    write_voice_profile_manifest,
)
from saymo.config import SaymoConfig


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, [0.0, 0.1, -0.1, 0.0], 16000)


def _write_profile(tmp_path: Path, *, approved: bool) -> None:
    voice_sample = tmp_path / "voice_sample.wav"
    transcript = tmp_path / "voice_sample.txt"
    _write_wav(voice_sample)
    transcript.write_text("reference transcript", encoding="utf-8")
    manifest = build_voice_profile_manifest(
        profile="personal",
        voice_sample=voice_sample,
        ref_text_file=transcript,
        engine="f5tts_clone",
        language="ru",
    )
    manifest = replace(
        manifest,
        approved_for_calls=approved,
        approved_benchmark_run="run-001" if approved else "",
    )
    write_voice_profile_manifest(manifest, profiles_dir=tmp_path / "profiles")


def _config(tmp_path: Path, engine: str) -> SaymoConfig:
    config = SaymoConfig()
    config.tts.engine = engine
    config.voice_selector.default_profile = "personal"
    config.voice_selector.profiles_dir = str(tmp_path / "profiles")
    return config


def test_live_call_selector_blocks_missing_profile(tmp_path):
    from saymo.tts.selector import resolve_voice_selector

    decision = resolve_voice_selector(_config(tmp_path, "f5tts_clone"), purpose="live_call")

    assert decision.allowed is False
    assert decision.blocked_reason == "voice_profile_missing"
    assert decision.selected_engine == "f5tts_clone"
    assert decision.is_voice_clone is True


def test_live_call_selector_blocks_unapproved_profile(tmp_path):
    from saymo.tts.selector import resolve_voice_selector

    _write_profile(tmp_path, approved=False)
    decision = resolve_voice_selector(_config(tmp_path, "f5tts_clone"), purpose="live_call")

    assert decision.allowed is False
    assert decision.blocked_reason == "voice_profile_unapproved"


def test_live_call_selector_allows_approved_cloned_engine(tmp_path):
    from saymo.tts.selector import resolve_voice_selector

    _write_profile(tmp_path, approved=True)
    decision = resolve_voice_selector(_config(tmp_path, "f5tts_clone"), purpose="live_call")

    assert decision.allowed is True
    assert decision.blocked_reason == ""
    assert decision.selected_engine == "f5tts_clone"
    assert decision.reference_audio_sha256
    assert decision.profile_approved is True


def test_live_call_selector_blocks_non_cloned_fallback_by_default(tmp_path):
    from saymo.tts.selector import resolve_voice_selector

    _write_profile(tmp_path, approved=True)
    decision = resolve_voice_selector(_config(tmp_path, "macos_say"), purpose="live_call")

    assert decision.allowed is False
    assert decision.blocked_reason == "engine_not_voice_clone"
    assert decision.is_voice_clone is False


def test_explicit_live_call_non_cloned_fallback_is_visible(tmp_path):
    from saymo.tts.selector import resolve_voice_selector

    _write_profile(tmp_path, approved=True)
    config = _config(tmp_path, "macos_say")
    config.voice_selector.live_call.allow_non_cloned = True

    decision = resolve_voice_selector(config, purpose="live_call")

    assert decision.allowed is True
    assert decision.selected_engine == "macos_say"
    assert decision.is_voice_clone is False
    assert decision.non_cloned_allowed is True


def test_realtime_selector_uses_explicit_fallback_chain(tmp_path):
    from saymo.tts.selector import resolve_voice_selector

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.tts.realtime_engine = "unknown_engine"
    config.voice_selector.realtime.fallbacks = ["macos_say"]

    decision = resolve_voice_selector(config, purpose="realtime")

    assert decision.allowed is True
    assert decision.requested_engine == "unknown_engine"
    assert decision.selected_engine == "macos_say"
    assert decision.attempted_engines == ("unknown_engine", "macos_say")
    assert decision.fallback_engine == "macos_say"

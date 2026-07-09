"""Tests for read-only cache regeneration advice."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from saymo.config import SaymoConfig


def test_prepared_audio_cache_advice_reports_ready_without_regeneration(tmp_path: Path):
    from saymo.analysis.cache_advice import prepared_audio_cache_advice
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        write_voice_cache_metadata,
    )

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.meetings = {
        "standup": {
            "voice": {
                "f5_pause_preset": "crisp",
                "f5_pause_presets": {"prepared": "calm"},
            }
        }
    }
    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFF")
    write_voice_cache_metadata(
        audio,
        build_voice_cache_metadata(
            config,
            purpose="prepare",
            profile="standup",
            source_type="prepared",
        ),
    )

    advice = prepared_audio_cache_advice(config, audio, profile="standup")

    assert advice.status == "ready"
    assert advice.expensive is False
    assert advice.action == "No regeneration needed; prepared audio is current."
    assert advice.metadata["source_type"] == "prepared"
    assert advice.metadata["purpose"] == "prepare"
    assert advice.metadata["profile_preset_id"] == "crisp"
    assert advice.metadata["source_override_preset_id"] == "calm"
    assert advice.metadata["resolved_preset_id"] == "calm"


def test_prepared_audio_cache_advice_warns_for_stale_f5_metadata(tmp_path: Path):
    from saymo.analysis.cache_advice import prepared_audio_cache_advice
    from saymo.analysis.cache_metadata import VoiceCacheMetadata, write_voice_cache_metadata

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFF")
    write_voice_cache_metadata(
        audio,
        VoiceCacheMetadata(
            purpose="prepare",
            selected_engine="f5tts_clone",
            attempted_engines=("f5tts_clone",),
            fingerprint="old",
            source_sha256="PRIVATE_SOURCE_HASH_ONLY",
        ),
    )

    advice = prepared_audio_cache_advice(config, audio, profile="standup")

    assert advice.status == "stale"
    assert advice.reason == "voice_metadata_stale"
    assert advice.expensive is True
    assert "F5" in advice.warning
    assert advice.action == "Run saymo prepare -p standup to rebuild prepared audio only."
    assert advice.metadata["source_type"] == "prepared"
    assert advice.metadata["resolved_preset_id"] == "approved"
    assert "PRIVATE_" not in json.dumps(advice.to_dict(), ensure_ascii=False)


def test_response_cache_advice_warns_for_stale_or_missing_variants(tmp_path: Path):
    from saymo.analysis.cache_advice import response_cache_advice
    from saymo.analysis.cache_metadata import VoiceCacheMetadata, write_voice_cache_metadata
    from saymo.analysis.response_cache import ResponseCache, ResponseEntry

    library = {
        "blockers_none": ResponseEntry(
            key="blockers_none",
            triggers=["есть блокеры"],
            variants=["PRIVATE RESPONSE TEXT"],
        )
    }
    expected = VoiceCacheMetadata(
        purpose="response_cache",
        selected_engine="f5tts_clone",
        attempted_engines=("f5tts_clone",),
        fingerprint="current",
    )
    stale = VoiceCacheMetadata(
        purpose="response_cache",
        selected_engine="f5tts_clone",
        attempted_engines=("f5tts_clone",),
        fingerprint="old",
    )
    cache = ResponseCache(library=library, cache_dir=tmp_path, voice_metadata=expected)
    path = cache.variant_path("blockers_none", 0, "PRIVATE RESPONSE TEXT")
    path.write_bytes(b"RIFF")
    write_voice_cache_metadata(path, stale)

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.responses.cache_dir = str(tmp_path)
    config.responses.library = {
        "blockers_none": {
            "triggers": ["есть блокеры"],
            "variants": ["PRIVATE RESPONSE TEXT"],
        }
    }
    config.meetings = {
        "standup": {
            "voice": {
                "f5_pause_preset": "crisp",
                "f5_pause_presets": {"response_cache": "deliberate"},
            }
        }
    }
    advice = response_cache_advice(config, profile="standup")

    assert advice.status in {"stale", "partial"}
    assert advice.expensive is True
    assert advice.action == (
        "Run saymo prepare-responses -p standup to rebuild only missing or stale variants."
    )
    assert "prepare-responses --force" in advice.warning
    assert advice.metadata["source_type"] == "response_cache"
    assert advice.metadata["purpose"] == "response_cache"
    assert advice.metadata["profile_preset_id"] == "crisp"
    assert advice.metadata["source_override_preset_id"] == "deliberate"
    assert advice.metadata["resolved_preset_id"] == "deliberate"
    assert any("voice_metadata_stale" in item for item in advice.metadata["stale_examples"])
    assert "PRIVATE RESPONSE TEXT" not in json.dumps(advice.to_dict(), ensure_ascii=False)


def test_response_cache_advice_reports_ready_without_force(tmp_path: Path):
    from saymo.analysis.cache_advice import response_cache_advice
    from saymo.analysis.cache_metadata import build_voice_cache_metadata
    from saymo.analysis.response_cache import ResponseCache, build_library

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.responses.cache_dir = str(tmp_path)
    config.responses.library = {
        "blockers_none": {
            "triggers": ["есть блокеры"],
            "variants": ["Блокеров нет."],
        }
    }
    config.meetings = {
        "standup": {
            "voice": {
                "f5_pause_preset": "crisp",
                "f5_pause_presets": {"response_cache": "calm"},
            }
        }
    }
    library = build_library(config.responses.library)
    metadata = build_voice_cache_metadata(
        config,
        purpose="response_cache",
        profile="standup",
        source_type="response_cache",
    )
    cache = ResponseCache(library=library, cache_dir=tmp_path, voice_metadata=metadata)

    async def synth(_text: str) -> bytes:
        return b"RIFF"

    asyncio.run(cache.build(synth, voice_metadata=metadata))

    advice = response_cache_advice(config, profile="standup")

    assert advice.status == "ready"
    assert advice.expensive is False
    assert advice.action == "No regeneration needed; response cache is current."
    assert advice.metadata["source_type"] == "response_cache"
    assert advice.metadata["profile_preset_id"] == "crisp"
    assert advice.metadata["source_override_preset_id"] == "calm"
    assert advice.metadata["resolved_preset_id"] == "calm"

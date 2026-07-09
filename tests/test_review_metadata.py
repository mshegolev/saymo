"""Tests for preserving prepared-audio metadata after review saves."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np

from saymo.config import SaymoConfig


def test_write_reviewed_audio_cache_writes_current_sidecar_without_text(tmp_path: Path):
    from saymo.analysis.cache_metadata import read_voice_cache_metadata
    from saymo.commands.core import _write_reviewed_audio_cache

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

    _write_reviewed_audio_cache(
        config,
        audio,
        np.zeros(160, dtype=np.float32),
        sample_rate=16000,
        normalized_text="PRIVATE REVIEWED TEXT",
        profile_name="standup",
    )

    metadata = read_voice_cache_metadata(audio)
    payload = json.loads((tmp_path / "prepared.wav.meta.json").read_text(encoding="utf-8"))
    assert metadata.purpose == "prepare"
    assert metadata.selected_engine == "f5tts_clone"
    assert metadata.source_profile == "standup"
    assert metadata.source_type == "prepared"
    assert metadata.source_preset_id == "calm"
    assert metadata.profile_preset_id == "crisp"
    assert metadata.source_override_preset_id == "calm"
    assert "PRIVATE REVIEWED TEXT" not in json.dumps(payload, ensure_ascii=False)


def test_write_reviewed_audio_cache_preserves_existing_source_fields(tmp_path: Path):
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        read_voice_cache_metadata,
        write_voice_cache_metadata,
    )
    from saymo.commands.core import _write_reviewed_audio_cache

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
    existing = build_voice_cache_metadata(
        config,
        purpose="prepare",
        source_kind="obsidian",
        source_profile="standup",
        source_sha256="source-hash-only",
        profile="standup",
        source_type="prepared",
    )
    write_voice_cache_metadata(audio, existing)

    _write_reviewed_audio_cache(
        config,
        audio,
        np.zeros(160, dtype=np.float32),
        sample_rate=16000,
        normalized_text="PRIVATE UPDATED REVIEW TEXT",
        profile_name="fallback",
    )

    metadata = read_voice_cache_metadata(audio)
    assert metadata.fingerprint == existing.fingerprint
    assert metadata.source_kind == "obsidian"
    assert metadata.source_profile == "standup"
    assert metadata.source_sha256 == "source-hash-only"
    assert metadata.source_type == "prepared"
    assert metadata.source_preset_id == "calm"


def test_prepare_writes_prepared_source_type_metadata(tmp_path: Path, monkeypatch):
    from saymo.analysis.cache_metadata import read_voice_cache_metadata
    from saymo.commands import core

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.meetings = {
        "scrum": {
            "voice": {
                "f5_pause_preset": "crisp",
                "f5_pause_presets": {"prepared": "deliberate"},
            }
        }
    }
    audio = tmp_path / "prepared.wav"

    async def fake_get_standup_content(_config):
        return {"today": "PRIVATE TODAY", "yesterday": "", "blockers": ""}

    async def fake_compose_text(_config, _notes):
        return "PRIVATE PREPARED TEXT"

    async def fake_synthesize(_config, text, *, purpose="prepare"):
        assert purpose == "prepare"
        assert "PRIVATE PREPARED TEXT" in text
        return b"RIFF prepared"

    monkeypatch.setattr(core, "_rotate_audio_cache", lambda: None)
    monkeypatch.setattr(core, "_get_standup_content", fake_get_standup_content)
    monkeypatch.setattr(core, "_compose_text", fake_compose_text)
    monkeypatch.setattr(core, "_synthesize", fake_synthesize)
    monkeypatch.setattr(core, "_get_cached_audio_path", lambda team=False: audio)

    asyncio.run(core._prepare(config, save=False, profile_name="scrum"))

    metadata = read_voice_cache_metadata(audio)
    assert metadata.source_profile == "scrum"
    assert metadata.source_type == "prepared"
    assert metadata.source_preset_id == "deliberate"
    assert metadata.profile_preset_id == "crisp"
    assert metadata.source_override_preset_id == "deliberate"

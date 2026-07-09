"""Tests for preserving prepared-audio metadata after review saves."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from saymo.config import SaymoConfig


def test_write_reviewed_audio_cache_writes_current_sidecar_without_text(tmp_path: Path):
    from saymo.analysis.cache_metadata import read_voice_cache_metadata
    from saymo.commands.core import _write_reviewed_audio_cache

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
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
    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFF")
    existing = build_voice_cache_metadata(
        config,
        purpose="prepare",
        source_kind="obsidian",
        source_profile="standup",
        source_sha256="source-hash-only",
    )
    write_voice_cache_metadata(audio, existing)
    config.tts.f5tts.pause_preset = "calm"

    _write_reviewed_audio_cache(
        config,
        audio,
        np.zeros(160, dtype=np.float32),
        sample_rate=16000,
        normalized_text="PRIVATE UPDATED REVIEW TEXT",
        profile_name="fallback",
    )

    metadata = read_voice_cache_metadata(audio)
    assert metadata.fingerprint != existing.fingerprint
    assert metadata.source_kind == "obsidian"
    assert metadata.source_profile == "standup"
    assert metadata.source_sha256 == "source-hash-only"

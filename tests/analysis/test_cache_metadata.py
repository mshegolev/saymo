"""Tests for voice cache metadata sidecars."""

from __future__ import annotations

import json

from saymo.config import SaymoConfig


def test_voice_cache_metadata_writes_privacy_safe_sidecar(tmp_path):
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        read_voice_cache_metadata,
        write_voice_cache_metadata,
    )

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFFfake")

    metadata = build_voice_cache_metadata(config, purpose="prepare", text="PRIVATE TEXT")
    out = write_voice_cache_metadata(audio, metadata)

    assert out == tmp_path / "prepared.wav.meta.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["purpose"] == "prepare"
    assert payload["selected_engine"] == "f5tts_clone"
    assert payload["fingerprint"]
    assert "PRIVATE TEXT" not in out.read_text(encoding="utf-8")
    assert read_voice_cache_metadata(audio).fingerprint == metadata.fingerprint


def test_voice_cache_metadata_check_rejects_missing_and_stale_sidecars(tmp_path):
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        check_voice_cache_metadata,
        write_voice_cache_metadata,
    )

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFFfake")
    expected = build_voice_cache_metadata(config, purpose="prepare")

    missing = check_voice_cache_metadata(audio, expected)
    assert missing.valid is False
    assert missing.blocked_reason == "voice_metadata_missing"

    write_voice_cache_metadata(audio, expected)
    ok = check_voice_cache_metadata(audio, expected)
    assert ok.valid is True
    assert ok.blocked_reason == ""

    config.tts.engine = "qwen3_clone"
    stale_expected = build_voice_cache_metadata(config, purpose="prepare")
    stale = check_voice_cache_metadata(audio, stale_expected)
    assert stale.valid is False
    assert stale.blocked_reason == "voice_metadata_stale"


def test_voice_cache_metadata_records_source_digest_without_text(tmp_path):
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        check_voice_cache_metadata,
        write_voice_cache_metadata,
    )

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFFfake")

    metadata = build_voice_cache_metadata(
        config,
        purpose="prepare",
        text="PRIVATE_DAILY_NOTE",
    )
    changed = build_voice_cache_metadata(
        config,
        purpose="prepare",
        text="PRIVATE_DAILY_NOTE changed",
    )
    out = write_voice_cache_metadata(audio, metadata)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["source_sha256"]
    assert metadata.source_sha256 != changed.source_sha256
    source_stale = check_voice_cache_metadata(audio, changed)
    assert source_stale.valid is False
    assert source_stale.blocked_reason == "source_metadata_stale"
    assert "PRIVATE_DAILY_NOTE" not in out.read_text(encoding="utf-8")

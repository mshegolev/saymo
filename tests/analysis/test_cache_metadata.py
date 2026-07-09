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


def test_prepare_metadata_goes_stale_when_f5_pacing_changes(tmp_path):
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
        text="PRIVATE_PREPARED_TEXT",
        source_kind="obsidian",
        source_profile="standup",
    )
    out = write_voice_cache_metadata(audio, metadata)

    config.tts.f5tts.silent_breath_pause_seconds = 0.9
    config.tts.f5tts.sentence_pause_seconds = 0.5
    config.tts.f5tts.clause_pause_seconds = 0.25
    config.tts.f5tts.breath_interval_sentences = 3
    changed = build_voice_cache_metadata(
        config,
        purpose="prepare",
        text="PRIVATE_PREPARED_TEXT",
        source_kind="obsidian",
        source_profile="standup",
    )

    stale = check_voice_cache_metadata(audio, changed)
    sidecar_text = out.read_text(encoding="utf-8")

    assert stale.valid is False
    assert stale.blocked_reason == "voice_metadata_stale"
    assert "PRIVATE_PREPARED_TEXT" not in sidecar_text
    assert "audio_bytes" not in sidecar_text


def test_prepared_metadata_goes_stale_when_source_preset_changes(tmp_path):
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        check_voice_cache_metadata,
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
    audio.write_bytes(b"RIFFfake")

    metadata = build_voice_cache_metadata(
        config,
        purpose="prepare",
        text="PRIVATE_PREPARED_TEXT",
        profile="standup",
        source_type="prepared",
    )
    out = write_voice_cache_metadata(audio, metadata)

    config.meetings["standup"]["voice"]["f5_pause_presets"]["prepared"] = "deliberate"
    changed = build_voice_cache_metadata(
        config,
        purpose="prepare",
        text="PRIVATE_PREPARED_TEXT",
        profile="standup",
        source_type="prepared",
    )
    stale = check_voice_cache_metadata(audio, changed)
    sidecar_text = out.read_text(encoding="utf-8")
    payload = json.loads(sidecar_text)

    assert metadata.fingerprint != changed.fingerprint
    assert stale.valid is False
    assert stale.blocked_reason == "voice_metadata_stale"
    assert payload["source_type"] == "prepared"
    assert payload["source_preset_id"] == "calm"
    assert payload["profile_preset_id"] == "crisp"
    assert payload["source_override_preset_id"] == "calm"
    assert "PRIVATE_PREPARED_TEXT" not in sidecar_text
    assert "prompt_text" not in sidecar_text
    assert "response_text" not in sidecar_text
    assert "audio_bytes" not in sidecar_text
    assert "secret" not in sidecar_text.lower()


def test_response_cache_metadata_goes_stale_when_source_preset_changes(tmp_path):
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        check_voice_cache_metadata,
        write_voice_cache_metadata,
    )

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.meetings = {
        "standup": {
            "voice": {
                "f5_pause_preset": "crisp",
                "f5_pause_presets": {"response_cache": "calm"},
            }
        }
    }
    audio = tmp_path / "response.wav"
    audio.write_bytes(b"RIFFfake")

    metadata = build_voice_cache_metadata(
        config,
        purpose="response_cache",
        profile="standup",
        source_type="response_cache",
    )
    write_voice_cache_metadata(audio, metadata)

    config.meetings["standup"]["voice"]["f5_pause_presets"][
        "response_cache"
    ] = "deliberate"
    changed = build_voice_cache_metadata(
        config,
        purpose="response_cache",
        profile="standup",
        source_type="response_cache",
    )
    stale = check_voice_cache_metadata(audio, changed)

    assert metadata.source_type == "response_cache"
    assert metadata.source_preset_id == "calm"
    assert metadata.profile_preset_id == "crisp"
    assert metadata.source_override_preset_id == "calm"
    assert metadata.fingerprint != changed.fingerprint
    assert stale.valid is False
    assert stale.blocked_reason == "voice_metadata_stale"


def test_old_voice_cache_sidecars_remain_readable_without_source_fields(tmp_path):
    from saymo.analysis.cache_metadata import read_voice_cache_metadata

    audio = tmp_path / "prepared.wav"
    audio.write_bytes(b"RIFFfake")
    sidecar = tmp_path / "prepared.wav.meta.json"
    sidecar.write_text(
        json.dumps(
            {
                "purpose": "prepare",
                "selected_engine": "f5tts_clone",
                "attempted_engines": ["f5tts_clone"],
                "fingerprint": "old",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    metadata = read_voice_cache_metadata(audio)

    assert metadata.source_type == ""
    assert metadata.source_preset_id == ""
    assert metadata.profile_preset_id == ""
    assert metadata.source_override_preset_id == ""

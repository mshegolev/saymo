"""Tests for protected voice profile manifests."""

from __future__ import annotations

import json
from pathlib import Path

import soundfile as sf


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, [0.0, 0.2, -0.2, 0.0], 16000)


def test_voice_profile_manifest_references_assets_without_copying_or_leaking_text(tmp_path):
    from saymo.analysis.voice_profile import (
        build_voice_profile_manifest,
        voice_profile_to_json,
        write_voice_profile_manifest,
    )

    voice_sample = tmp_path / "voice_samples" / "voice_sample.wav"
    transcript = voice_sample.with_suffix(".txt")
    profiles_dir = tmp_path / "voice_profiles"
    _write_wav(voice_sample)
    transcript.write_text("PRIVATE PROFILE TRANSCRIPT", encoding="utf-8")
    before = {
        path: (path.stat().st_mtime_ns, path.read_bytes())
        for path in (voice_sample, transcript)
    }

    manifest = build_voice_profile_manifest(
        profile="personal",
        voice_sample=voice_sample,
        ref_text_file=transcript,
        engine="f5tts_clone",
        language="ru",
    )

    assert manifest.profile == "personal"
    assert manifest.engine == "f5tts_clone"
    assert manifest.approved_for_calls is False
    assert manifest.reference_audio.path == str(voice_sample)
    assert manifest.reference_audio.sha256
    assert manifest.reference_audio.sample_rate == 16000
    assert manifest.reference_text.path == str(transcript)
    assert manifest.reference_text.chars == len("PRIVATE PROFILE TRANSCRIPT")
    assert manifest.reference_text.preview is None

    payload = voice_profile_to_json(manifest)
    assert "PRIVATE PROFILE TRANSCRIPT" not in json.dumps(payload, ensure_ascii=False)

    out = write_voice_profile_manifest(manifest, profiles_dir=profiles_dir)
    assert out == profiles_dir / "personal" / "profile.json"
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["profile"] == "personal"
    assert written["approved_for_calls"] is False

    for path, (mtime, content) in before.items():
        assert path.stat().st_mtime_ns == mtime
        assert path.read_bytes() == content


def test_voice_profile_check_detects_missing_and_stale_references(tmp_path):
    from saymo.analysis.voice_profile import (
        build_voice_profile_manifest,
        check_voice_profile,
    )

    voice_sample = tmp_path / "voice_sample.wav"
    transcript = tmp_path / "voice_sample.txt"
    _write_wav(voice_sample)
    transcript.write_text("short transcript", encoding="utf-8")

    manifest = build_voice_profile_manifest(
        profile="personal",
        voice_sample=voice_sample,
        ref_text_file=transcript,
        engine="f5tts_clone",
        language="ru",
    )

    ok = check_voice_profile(manifest)
    assert ok.status == "ready"
    assert ok.blockers == ()

    voice_sample.write_bytes(b"changed")
    stale = check_voice_profile(manifest)
    assert stale.status == "blocked"
    assert any("reference audio hash changed" in item for item in stale.blockers)

    voice_sample.unlink()
    missing = check_voice_profile(manifest)
    assert missing.status == "blocked"
    assert any("reference audio missing" in item for item in missing.blockers)

"""Tests for voice profile approval and preview audit."""

from __future__ import annotations

import json
from pathlib import Path

import soundfile as sf

from saymo.analysis.voice_profile import (
    build_voice_profile_manifest,
    load_voice_profile_manifest,
    write_voice_profile_manifest,
)


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, [0.0, 0.1, -0.1, 0.0], 16000)


def _write_profile(tmp_path: Path) -> tuple[Path, Path]:
    profiles_dir = tmp_path / "profiles"
    sample = tmp_path / "voice_sample.wav"
    transcript = tmp_path / "voice_sample.txt"
    _write_wav(sample)
    transcript.write_text("PRIVATE TRANSCRIPT", encoding="utf-8")
    manifest = build_voice_profile_manifest(
        profile="personal",
        voice_sample=sample,
        ref_text_file=transcript,
        engine="f5tts_clone",
        language="ru",
    )
    write_voice_profile_manifest(manifest, profiles_dir=profiles_dir)
    return profiles_dir, sample


def _write_score_report(tmp_path: Path) -> Path:
    report = tmp_path / "score-report.md"
    report.write_text(
        "\n".join(
            [
                "# Voice Benchmark Score Report",
                "",
                "run status: complete",
                "score status: scored",
                "decision: approved",
                "promotion ready: yes",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def test_approve_voice_profile_requires_gates_or_override(tmp_path):
    from saymo.analysis.voice_approval import approve_voice_profile

    profiles_dir, _sample = _write_profile(tmp_path)
    score_report = _write_score_report(tmp_path)

    try:
        approve_voice_profile(
            profile="personal",
            profiles_dir=profiles_dir,
            score_report=score_report,
            similarity=6,
            artifacts=8,
            call_readiness=8,
        )
    except ValueError as exc:
        assert "similarity" in str(exc)
    else:
        raise AssertionError("low similarity should require override")

    approved = approve_voice_profile(
        profile="personal",
        profiles_dir=profiles_dir,
        score_report=score_report,
        similarity=7,
        artifacts=8,
        call_readiness=8,
    )

    assert approved.approved_for_calls is True
    assert approved.approved_benchmark_run == str(score_report)
    assert "PRIVATE TRANSCRIPT" not in (
        profiles_dir / "personal" / "profile.json"
    ).read_text(encoding="utf-8")


def test_reject_voice_profile_clears_call_approval(tmp_path):
    from saymo.analysis.voice_approval import approve_voice_profile, reject_voice_profile

    profiles_dir, _sample = _write_profile(tmp_path)
    score_report = _write_score_report(tmp_path)
    approve_voice_profile(
        profile="personal",
        profiles_dir=profiles_dir,
        score_report=score_report,
        similarity=9,
        artifacts=9,
        call_readiness=9,
    )

    rejected = reject_voice_profile(
        profile="personal",
        profiles_dir=profiles_dir,
        score_report=score_report,
        reason="artifacts in consonants",
    )

    assert rejected.approved_for_calls is False
    assert rejected.fallback_policy == "rejected: artifacts in consonants"
    saved = load_voice_profile_manifest("personal", profiles_dir=profiles_dir)
    assert saved.approved_for_calls is False


def test_preview_audit_is_preview_only_and_text_safe(tmp_path):
    from saymo.analysis.voice_approval import write_voice_preview_audit
    from saymo.config import SaymoConfig

    profiles_dir, _sample = _write_profile(tmp_path)
    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.voice_selector.default_profile = "personal"
    config.voice_selector.profiles_dir = str(profiles_dir)

    out = write_voice_preview_audit(
        config,
        profile="personal",
        text="PRIVATE PREVIEW TEXT",
        profiles_dir=profiles_dir,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["preview_only"] is True
    assert payload["profile"] == "personal"
    assert payload["selector"]["selected_engine"] == "f5tts_clone"
    assert payload["text_sha256"]
    assert "PRIVATE PREVIEW TEXT" not in out.read_text(encoding="utf-8")

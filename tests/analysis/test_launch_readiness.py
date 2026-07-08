"""Tests for shared launch-readiness contracts."""

from __future__ import annotations

import json
import hashlib
import textwrap
from datetime import date
from pathlib import Path

from saymo.config import load_config


PRIVATE_STRINGS = (
    "PRIVATE_DAILY_NOTE",
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_GENERATED_ANSWER",
    "SECRET_TOKEN",
)


def _write_config(tmp_path, *, vault_path: Path | None = None) -> Path:
    config_path = tmp_path / "config.yaml"
    vault = vault_path or (tmp_path / "Vault")
    config_path.write_text(
        textwrap.dedent(
            f"""
            user:
              name: "John"
              name_variants:
                - "John"
            speech:
              source: obsidian
            obsidian:
              vault_path: "{vault}"
              subfolder: ""
              date_format: "%Y-%m-%d"
            meetings:
              standup:
                description: "Standup"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
            responses:
              enabled: true
              cache_dir: "{tmp_path / 'responses'}"
              library: {{}}
            """
        ),
        encoding="utf-8",
    )
    return config_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_voice_profile(tmp_path, *, approved: bool) -> Path:
    profiles_dir = tmp_path / "profiles"
    profile_dir = profiles_dir / "personal"
    profile_dir.mkdir(parents=True)
    audio = tmp_path / "reference.wav"
    transcript = tmp_path / "reference.txt"
    audio.write_bytes(b"reference audio bytes")
    transcript.write_text("PRIVATE_REFERENCE_TEXT SECRET_TOKEN", encoding="utf-8")
    payload = {
        "profile": "personal",
        "engine": "f5tts_clone",
        "language": "ru",
        "reference_audio": {
            "path": str(audio),
            "exists": True,
            "size_bytes": audio.stat().st_size,
            "sha256": _sha256_file(audio),
            "duration_seconds": None,
            "sample_rate": None,
            "channels": None,
        },
        "reference_text": {
            "path": str(transcript),
            "exists": True,
            "size_bytes": transcript.stat().st_size,
            "sha256": _sha256_file(transcript),
            "chars": len(transcript.read_text(encoding="utf-8")),
            "preview": None,
        },
        "approved_for_calls": approved,
        "approved_benchmark_run": "run-001" if approved else "",
        "fallback_policy": "blocked_until_approved",
    }
    (profile_dir / "profile.json").write_text(
        json.dumps(payload, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return profiles_dir


def _assert_private_absent(text: str) -> None:
    for value in PRIVATE_STRINGS:
        assert value not in text


def _check_by_key(report, key: str):
    matches = [check for check in report.checks if check.key == key]
    assert matches, f"missing launch readiness check: {key}"
    return matches[0]


def test_report_ready_false_when_blocking_check_fails():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    warning_only = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="response_cache_partial",
                label="response cache",
                severity="warn",
                ok=False,
                detail="ready_count=1 total_count=2",
            ),
        ),
    )
    blocked = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source",
                label="daily note source",
                severity="block",
                ok=False,
                detail="placeholder_only",
            ),
        ),
    )

    assert warning_only.ready is True
    assert blocked.ready is False


def test_report_serializes_without_private_text():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    unsafe_blob = " ".join(PRIVATE_STRINGS)
    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source",
                label="daily note source",
                severity="block",
                ok=False,
                detail=unsafe_blob,
                action=unsafe_blob,
                metadata={
                    "source_sha256": "abc123",
                    "ready_count": 0,
                    "raw_source": unsafe_blob,
                },
            ),
        ),
    )

    serialized = json.dumps(report.to_dict(), ensure_ascii=False)

    assert "daily_note_source" in serialized
    assert "source_sha256" in serialized
    assert "ready_count" in serialized
    _assert_private_absent(serialized)


def test_placeholder_daily_note_blocks_source_readiness(tmp_path):
    from saymo.analysis.launch_readiness import collect_launch_readiness

    vault = tmp_path / "Vault"
    vault.mkdir()
    today = date.today().strftime("%Y-%m-%d")
    (vault / f"{today}.md").write_text(
        textwrap.dedent(
            f"""
            # {today}
            ## Standup
            ### Yesterday
            -
            ### Today
            -
            ### Blockers
            -
            """
        ),
        encoding="utf-8",
    )
    config = load_config(config_path=str(_write_config(tmp_path, vault_path=vault)))

    report = collect_launch_readiness(config, profile="standup", provider_name="glip")
    source = _check_by_key(report, "daily_note_source_ready")

    assert source.severity == "block"
    assert source.ok is False
    assert source.detail == "placeholder_only"
    assert source.metadata["note_path"].endswith(f"{today}.md")
    assert source.metadata["source_sha256"]
    _assert_private_absent(json.dumps(report.to_dict(), ensure_ascii=False))


def test_prepared_audio_requires_current_metadata_and_source_digest(tmp_path):
    from saymo.analysis.launch_readiness import collect_launch_readiness

    vault = tmp_path / "Vault"
    vault.mkdir()
    today = date.today().strftime("%Y-%m-%d")
    (vault / f"{today}.md").write_text(
        "# Standup\n\nPRIVATE_DAILY_NOTE\n",
        encoding="utf-8",
    )
    config = load_config(config_path=str(_write_config(tmp_path, vault_path=vault)))

    report = collect_launch_readiness(config, profile="standup", provider_name="glip")
    prepared = _check_by_key(report, "prepared_audio")

    assert prepared.severity == "block"
    assert prepared.ok is False
    assert prepared.metadata["source_sha256"]
    assert prepared.metadata["stale_reason"] in {
        "audio_missing",
        "voice_metadata_missing",
        "voice_metadata_stale",
        "source_digest_stale",
    }
    _assert_private_absent(json.dumps(report.to_dict(), ensure_ascii=False))


def test_voice_metadata_is_sanitized_and_actionable(tmp_path):
    from saymo.analysis.launch_cache import collect_voice_metadata_check

    config = load_config(config_path=str(_write_config(tmp_path)))
    config.tts.engine = "f5tts_clone"
    config.voice_selector.profiles_dir = str(_write_voice_profile(tmp_path, approved=False))

    voice = collect_voice_metadata_check(config, profile="standup", provider_name="glip")

    assert voice.key == "cloned_voice_metadata"
    assert voice.severity == "block"
    assert voice.ok is False
    assert voice.action
    assert voice.rerun == "saymo call-ready -p standup --provider glip --prepare"
    assert "selected_engine" in voice.metadata
    assert "voice_profile" in voice.metadata
    assert "profile_approved" in voice.metadata
    assert "reference_audio_sha256" in voice.metadata
    assert "reference_text_sha256" in voice.metadata
    assert "reference_fingerprint" in voice.metadata
    assert voice.metadata["selected_engine"] == "f5tts_clone"
    assert voice.metadata["voice_profile"] == "personal"
    assert voice.metadata["profile_approved"] is False
    assert voice.metadata["reference_audio_sha256"]
    assert voice.metadata["reference_text_sha256"]
    assert voice.metadata["reference_fingerprint"]
    assert voice.metadata["blocked_reason"] == "voice_profile_unapproved"
    serialized = json.dumps(voice.to_dict(), ensure_ascii=False)
    _assert_private_absent(serialized)
    assert "PRIVATE_REFERENCE_TEXT" not in serialized


def test_response_cache_launch_check_blocks_disabled_and_partial_coverage(tmp_path):
    from saymo.analysis.launch_cache import collect_response_cache_check

    config = load_config(config_path=str(_write_config(tmp_path)))

    partial = collect_response_cache_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert partial.key == "response_cache_coverage"
    assert partial.severity == "block"
    assert partial.ok is False
    assert partial.detail.endswith("variants ready")
    assert partial.metadata["ready"] == 0
    assert partial.metadata["total"] > 0
    assert partial.metadata["missing_examples"]
    assert partial.metadata["cache_dir"] == str(tmp_path / "responses")
    _assert_private_absent(json.dumps(partial.to_dict(), ensure_ascii=False))

    config.responses.enabled = False
    disabled = collect_response_cache_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert disabled.ok is False
    assert disabled.detail == "response_cache_disabled"
    assert disabled.action == "Set responses.enabled=true and run saymo prepare-responses"
    assert disabled.rerun == "saymo call-ready -p standup --provider glip --prepare"

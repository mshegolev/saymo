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
    assert source.action == (
        f"Add usable standup content to {source.metadata['note_path']}, "
        "then run saymo prepare -p standup"
    )
    assert source.rerun == "saymo call-ready -p standup --provider glip"
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
    prepared = _check_by_key(report, "prepared_standup_audio")

    assert prepared.severity == "block"
    assert prepared.ok is False
    assert prepared.metadata["source_sha256"]
    assert prepared.metadata["stale_reason"] in {
        "audio_missing",
        "voice_metadata_missing",
        "voice_metadata_stale",
        "source_metadata_stale",
    }
    assert prepared.action == "Run saymo prepare -p standup"
    assert prepared.rerun == "saymo call-ready -p standup --provider glip"
    _assert_private_absent(json.dumps(report.to_dict(), ensure_ascii=False))


def test_collect_launch_readiness_wires_full_phase36_order(tmp_path, monkeypatch):
    from saymo.analysis import launch_cache, launch_sources, provider_audio_readiness
    import saymo.analysis.launch_readiness as launch_readiness
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        collect_launch_readiness,
    )

    config = load_config(config_path=str(_write_config(tmp_path)))

    def fake_daily_checks(config, profile, *, provider_name, prepare):
        assert profile == "standup"
        assert provider_name == "glip"
        assert prepare is False
        return (
            LaunchReadinessCheck(
                key="daily_note_present",
                label="daily note present",
                severity="block",
                ok=True,
                metadata={"source_sha256": "ignored"},
            ),
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="block",
                ok=True,
                metadata={"source_sha256": "abc123"},
            ),
        )

    def fake_prepared_check(config, profile, *, provider_name, team_mode, source_sha256):
        assert profile == "standup"
        assert provider_name == "glip"
        assert team_mode is False
        assert source_sha256 == "abc123"
        return LaunchReadinessCheck(
            key="prepared_standup_audio",
            label="prepared standup audio",
            severity="block",
            ok=True,
        )

    monkeypatch.setattr(launch_sources, "collect_daily_note_checks", fake_daily_checks)
    monkeypatch.setattr(launch_sources, "collect_prepared_audio_check", fake_prepared_check)
    monkeypatch.setattr(
        launch_cache,
        "collect_response_cache_check",
        lambda config, *, profile, provider_name: LaunchReadinessCheck(
            key="response_cache_coverage",
            label="response cache coverage",
            severity="block",
            ok=True,
        ),
    )
    monkeypatch.setattr(
        launch_cache,
        "collect_voice_metadata_check",
        lambda config, *, profile, provider_name: LaunchReadinessCheck(
            key="cloned_voice_metadata",
            label="cloned voice metadata",
            severity="block",
            ok=True,
        ),
    )
    monkeypatch.setattr(
        provider_audio_readiness,
        "collect_provider_audio_checks",
        lambda config, *, profile, provider_name: (
            LaunchReadinessCheck(
                key="provider_meeting_tab",
                label="provider meeting tab",
                severity="block",
                ok=True,
                detail="meeting_found",
            ),
            LaunchReadinessCheck(
                key="capture_input_device",
                label="capture input device",
                severity="block",
                ok=True,
            ),
            LaunchReadinessCheck(
                key="playback_output_device",
                label="playback output device",
                severity="block",
                ok=True,
            ),
            LaunchReadinessCheck(
                key="provider_output_blackhole",
                label="provider output BlackHole",
                severity="block",
                ok=True,
            ),
            LaunchReadinessCheck(
                key="capture_route_blackhole",
                label="capture route BlackHole",
                severity="block",
                ok=True,
            ),
            LaunchReadinessCheck(
                key="recording_microphone_input",
                label="recording microphone input",
                severity="block",
                ok=True,
            ),
            LaunchReadinessCheck(
                key="provider_capabilities",
                label="provider capabilities",
                severity="info",
                ok=True,
            ),
            LaunchReadinessCheck(
                key="hotkey_accessibility_permission",
                label="hotkey Accessibility permission",
                severity="block",
                ok=True,
            ),
        ),
    )

    report = collect_launch_readiness(config, profile="standup", provider_name=None)

    assert report.provider == "glip"
    expected_base_order = [
        "daily_note_present",
        "daily_note_source_ready",
        "prepared_standup_audio",
        "response_cache_coverage",
        "cloned_voice_metadata",
        "provider_meeting_tab",
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
        "recording_microphone_input",
        "provider_capabilities",
    ]
    expected_order = [*expected_base_order, "hotkey_accessibility_permission"]
    assert [check.key for check in report.checks] == expected_order
    assert launch_readiness._LAUNCH_CHECK_ORDER == tuple(expected_base_order)
    old_placeholder_key = "provider" + "_audio_basic_scope"
    assert old_placeholder_key not in expected_order
    provider_tab = _check_by_key(report, "provider_meeting_tab")
    assert provider_tab.severity == "block"
    assert provider_tab.ok is True
    assert provider_tab.detail == "meeting_found"


def test_write_launch_readiness_artifact_writes_sorted_sanitized_json(tmp_path):
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
        write_launch_readiness_artifact,
    )

    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="block",
                ok=False,
                detail="PRIVATE_DAILY_NOTE SECRET_TOKEN",
                metadata={"source_sha256": "abc123"},
            ),
        ),
    )
    output_path = tmp_path / "call-ready.json"

    written = write_launch_readiness_artifact(report, output_path)

    assert written == output_path
    raw = output_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert raw.index('"block_count"') < raw.index('"profile"')
    payload = json.loads(raw)
    assert payload["checks"][0]["key"] == "daily_note_source_ready"
    assert payload["checks"][0]["metadata"]["source_sha256"] == "abc123"
    _assert_private_absent(raw)


def test_launch_readiness_remediation_groups_by_severity():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
        render_grouped_launch_remediation,
    )
    from saymo.analysis.remediation import hints_from_launch_readiness

    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="block",
                ok=False,
                detail="placeholder_only",
                action="Add usable standup content to /tmp/daily.md, then run saymo prepare -p standup",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="cloned_voice_metadata",
                label="cloned voice metadata",
                severity="warn",
                ok=False,
                detail="voice_profile_unapproved",
                action="Approve a cloned voice profile for live calls",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="provider_meeting_tab",
                label="provider meeting tab",
                severity="info",
                ok=False,
                detail="meeting_tab_not_found",
                action="Open the glip meeting in Chrome",
                rerun="saymo call-ready -p standup --provider glip",
            ),
        ),
    )

    hints = hints_from_launch_readiness(report)

    assert [(hint.category, hint.title) for hint in hints] == [
        ("source-data", "daily note source ready"),
        ("voice-cache", "cloned voice metadata"),
        ("provider", "provider meeting tab"),
    ]
    assert render_grouped_launch_remediation(report).splitlines() == [
        "remediation:",
        "block:",
        "- [source-data] daily note source ready",
        "  why: placeholder_only",
        "  action: Add usable standup content to /tmp/daily.md, then run saymo prepare -p standup",
        "  rerun: saymo call-ready -p standup --provider glip",
        "warn:",
        "- [voice-cache] cloned voice metadata",
        "  why: voice_profile_unapproved",
        "  action: Approve a cloned voice profile for live calls",
        "  rerun: saymo call-ready -p standup --provider glip",
        "info:",
        "- [provider] provider meeting tab",
        "  why: meeting_tab_not_found",
        "  action: Open the glip meeting in Chrome",
        "  rerun: saymo call-ready -p standup --provider glip",
    ]


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
    assert voice.rerun == "saymo call-ready -p standup --provider glip"
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
    assert disabled.action == "Set responses.enabled=true, then run saymo prepare-responses"
    assert disabled.rerun == "saymo call-ready -p standup --provider glip"

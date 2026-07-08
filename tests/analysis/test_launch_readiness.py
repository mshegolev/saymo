"""Tests for shared launch-readiness contracts."""

from __future__ import annotations

import json
import hashlib
import asyncio
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


def _rich_launch_evidence_report():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="response_cache_coverage",
                label="response cache coverage",
                severity="block",
                ok=False,
                detail="1/3 variants ready",
                action="Run saymo prepare-responses",
                rerun="saymo call-ready -p standup --provider glip",
                metadata={
                    "category": "source-data",
                    "ready": 1,
                    "total": 3,
                    "missing_examples": ["daily_summary", "handoff_answer"],
                    "cache_dir": "/tmp/saymo/responses",
                },
            ),
            LaunchReadinessCheck(
                key="cloned_voice_metadata",
                label="cloned voice metadata",
                severity="block",
                ok=False,
                detail="voice_profile_unapproved",
                action="Approve a cloned voice profile for live calls",
                rerun="saymo voice-profile approve personal",
                metadata={
                    "selected_engine": "f5tts_clone",
                    "voice_profile": "personal",
                    "profile_approved": False,
                    "reference_fingerprint": "voicefp_123",
                    "reference_audio_sha256": "audio_sha_123",
                    "reference_text_sha256": "text_sha_123",
                    "blocked_reason": "voice_profile_unapproved",
                },
            ),
            LaunchReadinessCheck(
                key="provider_meeting_tab",
                label="provider meeting tab",
                severity="block",
                ok=False,
                detail="meeting_tab_not_found",
                action="Open the glip meeting in Chrome",
                rerun="saymo call-ready -p standup --provider glip",
                metadata={
                    "category": "provider",
                    "provider": "glip",
                    "meeting_found": False,
                    "app_running": True,
                    "tab_info": None,
                },
            ),
            LaunchReadinessCheck(
                key="provider_capabilities",
                label="provider capabilities",
                severity="warn",
                ok=False,
                detail="mic_switch_unsupported",
                action="Use saymo takeover-check before relying on mic switching.",
                rerun="saymo takeover-check -p standup",
                metadata={
                    "category": "provider",
                    "provider": "glip",
                    "activation": "supported",
                    "mic_switch": "unsupported",
                    "mute_recovery": "supported",
                },
            ),
            LaunchReadinessCheck(
                key="call_control_agent",
                label="call-control agent",
                severity="block",
                ok=True,
                detail="LaunchAgent loaded",
                rerun="saymo call-control-agent status -p standup",
                metadata={
                    "category": "call-control",
                    "classification": "running",
                    "stdout_log_path": "/tmp/standup/out.log",
                    "stderr_log_path": "/tmp/standup/err.log",
                    "loaded": True,
                    "heartbeat_fresh": False,
                    "running": False,
                    "hotkeys_active": False,
                },
            ),
            LaunchReadinessCheck(
                key="call_control_daemon",
                label="call-control daemon",
                severity="block",
                ok=False,
                detail="heartbeat stale",
                action="saymo call-control-agent restart -p standup",
                rerun="saymo call-control probe -p standup",
                metadata={
                    "category": "call-control",
                    "classification": "stale_heartbeat",
                    "stdout_log_path": "/tmp/standup/out.log",
                    "stderr_log_path": "/tmp/standup/err.log",
                    "heartbeat_fresh": False,
                    "running": False,
                    "hotkeys_active": False,
                },
            ),
            LaunchReadinessCheck(
                key="call_control_hotkeys",
                label="call-control hotkeys",
                severity="block",
                ok=False,
                detail="Accessibility denied",
                action="grant Accessibility permission",
                rerun="saymo call-control-agent status -p standup",
                metadata={
                    "category": "macos-permission",
                    "stdout_log_path": "/tmp/standup/out.log",
                    "stderr_log_path": "/tmp/standup/err.log",
                    "heartbeat_fresh": False,
                    "running": False,
                    "hotkeys_active": False,
                },
            ),
        ),
    )


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


def test_prepare_saved_standup_metadata_matches_daily_note_hash(tmp_path, monkeypatch):
    import saymo.commands.core as core
    from saymo.analysis.cache_metadata import read_voice_cache_metadata
    from saymo.analysis.launch_sources import prepared_audio_status
    from saymo.obsidian.daily_notes import daily_note_path, inspect_standup_source

    vault = tmp_path / "Vault"
    vault.mkdir()
    config = load_config(config_path=str(_write_config(tmp_path, vault_path=vault)))
    config.tts.engine = "f5tts_clone"
    config.voice_selector.profiles_dir = str(_write_voice_profile(tmp_path, approved=True))
    audio_path = tmp_path / "cache" / "standup.wav"

    async def fake_get_standup_content(_config):
        return {
            "yesterday": "Finished the launch gate.",
            "today": "Close the integration gap.",
            "today_date": date.today().isoformat(),
        }

    async def fake_compose_text(_config, notes):
        assert notes["today"] == "Close the integration gap."
        return "Prepared launch summary."

    async def fake_synthesize(_config, text, *, purpose="prepare"):
        assert purpose == "prepare"
        assert "Prepared launch summary" in text
        return b"RIFF prepared audio"

    monkeypatch.setattr(core, "_rotate_audio_cache", lambda: None)
    monkeypatch.setattr(core, "_get_standup_content", fake_get_standup_content)
    monkeypatch.setattr(core, "_compose_text", fake_compose_text)
    monkeypatch.setattr(core, "_synthesize", fake_synthesize)
    monkeypatch.setattr(core, "_get_cached_audio_path", lambda team=False: audio_path)

    asyncio.run(core._prepare(config, save=True, profile_name="standup"))

    note_path = daily_note_path(config.obsidian)
    daily_hash = inspect_standup_source(note_path).source_sha256
    metadata = read_voice_cache_metadata(audio_path)
    status = prepared_audio_status(
        config,
        profile="standup",
        team_mode=False,
        source_sha256=daily_hash,
    )

    assert metadata.source_sha256 == daily_hash
    assert status.ok is True
    assert status.reason == ""


def test_collect_launch_readiness_wires_full_phase36_order(tmp_path, monkeypatch):
    from saymo.analysis import launch_agent, launch_cache, launch_sources, provider_audio_readiness
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
    monkeypatch.setattr(
        launch_agent,
        "build_launch_agent_spec",
        lambda profile: "fake-spec",
    )
    monkeypatch.setattr(
        launch_agent,
        "collect_call_control_agent_status",
        lambda spec: type(
            "Status",
            (),
            {
                "profile": "standup",
                "label": "com.saymo.call-control.standup",
                "plist_path": "/tmp/com.saymo.call-control.standup.plist",
                "stdout_log_path": "/tmp/standup/logs/com.saymo.call-control.standup.out.log",
                "stderr_log_path": "/tmp/standup/logs/com.saymo.call-control.standup.err.log",
                "installed": True,
                "plist_current": True,
                "loaded": True,
                "heartbeat_fresh": True,
                "running": True,
                "hotkeys_active": True,
                "hotkey_registration_status": "ok",
                "classification": "running",
                "detail": "LaunchAgent is loaded and daemon heartbeat is fresh.",
                "action": "none",
                "rerun": "saymo call-control-agent status -p standup",
                "metadata": {"bindings_count": 3},
            },
        )(),
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
    expected_daemon_order = [
        "call_control_agent",
        "call_control_daemon",
        "call_control_hotkeys",
    ]
    expected_order = [
        *expected_base_order,
        "hotkey_accessibility_permission",
        *expected_daemon_order,
    ]
    assert [check.key for check in report.checks] == expected_order
    assert launch_readiness._LAUNCH_CHECK_ORDER == tuple(
        [*expected_base_order, *expected_daemon_order]
    )
    old_placeholder_key = "provider" + "_audio_basic_scope"
    assert old_placeholder_key not in expected_order
    provider_tab = _check_by_key(report, "provider_meeting_tab")
    assert provider_tab.severity == "block"
    assert provider_tab.ok is True
    assert provider_tab.detail == "meeting_found"
    for key in expected_daemon_order:
        check = _check_by_key(report, key)
        assert check.severity == "block"
        assert check.ok is True
        assert check.metadata["category"] == "call-control"
        assert check.metadata["stdout_log_path"].endswith(".out.log")
        assert check.metadata["stderr_log_path"].endswith(".err.log")
    assert _check_by_key(report, "call_control_agent").rerun == (
        "saymo call-control-agent status -p standup"
    )
    assert _check_by_key(report, "call_control_daemon").rerun == (
        "saymo call-control probe -p standup"
    )


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


def test_call_control_hotkey_readiness_uses_permission_category(tmp_path, monkeypatch):
    from saymo.analysis import launch_agent, launch_cache, launch_sources, provider_audio_readiness
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        collect_launch_readiness,
    )

    config = load_config(config_path=str(_write_config(tmp_path)))
    monkeypatch.setattr(
        launch_sources,
        "collect_daily_note_checks",
        lambda config, profile, *, provider_name, prepare: (),
    )
    monkeypatch.setattr(
        launch_sources,
        "collect_prepared_audio_check",
        lambda config, profile, *, provider_name, team_mode, source_sha256: LaunchReadinessCheck(
            key="prepared_standup_audio",
            label="prepared standup audio",
            severity="block",
            ok=True,
        ),
    )
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
        lambda config, *, profile, provider_name: (),
    )
    monkeypatch.setattr(
        launch_agent,
        "build_launch_agent_spec",
        lambda profile: "fake-spec",
    )
    monkeypatch.setattr(
        launch_agent,
        "collect_call_control_agent_status",
        lambda spec: type(
            "Status",
            (),
            {
                "profile": "standup",
                "label": "com.saymo.call-control.standup",
                "plist_path": "/tmp/com.saymo.call-control.standup.plist",
                "stdout_log_path": "/tmp/standup/logs/com.saymo.call-control.standup.out.log",
                "stderr_log_path": "/tmp/standup/logs/com.saymo.call-control.standup.err.log",
                "installed": True,
                "plist_current": True,
                "loaded": True,
                "heartbeat_fresh": True,
                "running": True,
                "hotkeys_active": False,
                "hotkey_registration_status": "blocked",
                "classification": "hotkey_permission_blocked",
                "detail": "Daemon heartbeat reports hotkey registration blocked: Accessibility denied",
                "action": "grant Accessibility permission, then saymo call-control-agent restart -p standup",
                "rerun": "saymo call-control-agent status -p standup",
                "metadata": {"bindings_count": 3},
            },
        )(),
    )

    report = collect_launch_readiness(config, profile="standup", provider_name="glip")
    hotkeys = _check_by_key(report, "call_control_hotkeys")

    assert hotkeys.ok is False
    assert hotkeys.metadata["category"] == "macos-permission"
    assert "Accessibility" in hotkeys.action
    assert hotkeys.rerun == "saymo call-control-agent status -p standup"


def test_write_launch_readiness_artifact_adds_phase40_metadata_without_wrapping(
    tmp_path,
):
    from saymo.analysis.launch_evidence import load_launch_evidence
    from saymo.analysis.launch_readiness import write_launch_readiness_artifact

    report = _rich_launch_evidence_report()
    output_path = tmp_path / "call-ready.json"

    written = write_launch_readiness_artifact(report, output_path)

    assert written == output_path
    raw = output_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    payload = json.loads(raw)
    assert set(payload) == {
        "artifact_path",
        "block_count",
        "check_count",
        "checks",
        "created_at",
        "evidence_kind",
        "mode",
        "profile",
        "provider",
        "ready",
        "ready_count",
        "schema_version",
        "warn_count",
    }
    assert payload["profile"] == "standup"
    assert payload["provider"] == "glip"
    assert payload["ready"] is False
    assert payload["check_count"] == len(report.checks)
    assert payload["ready_count"] == 1
    assert payload["block_count"] == 5
    assert payload["warn_count"] == 1
    assert payload["schema_version"] == "1.0"
    assert payload["evidence_kind"] == "launch-readiness"
    assert payload["mode"] == "call-ready"
    assert payload["artifact_path"] == str(output_path)
    assert payload["created_at"]
    assert payload["checks"][0]["key"] == "response_cache_coverage"
    evidence = load_launch_evidence(output_path)
    assert evidence.schema_version == "1.0"
    assert evidence.path == str(output_path)
    _assert_private_absent(raw)


def test_launch_evidence_loads_enriched_artifact_summary(tmp_path):
    from saymo.analysis.launch_evidence import load_launch_evidence
    from saymo.analysis.launch_readiness import write_launch_readiness_artifact

    output_path = tmp_path / "call-ready.json"
    write_launch_readiness_artifact(_rich_launch_evidence_report(), output_path)

    evidence = load_launch_evidence(output_path)

    assert evidence.evidence_kind == "launch-readiness"
    assert evidence.mode == "call-ready"
    assert evidence.profile == "standup"
    assert evidence.provider == "glip"
    assert evidence.failed_labels == (
        "response cache coverage",
        "cloned voice metadata",
        "provider meeting tab",
        "provider capabilities",
        "call-control daemon",
        "call-control hotkeys",
    )
    assert evidence.blocker_categories == {
        "call-control": 1,
        "macos-permission": 1,
        "provider": 1,
        "source-data": 1,
        "voice-cache": 1,
    }
    assert evidence.cache_counts == {
        "ready": 1,
        "total": 3,
        "missing": 2,
    }
    assert evidence.voice_metadata == {
        "selected_engine": "f5tts_clone",
        "voice_profile": "personal",
        "profile_approved": False,
        "reference_fingerprint": "voicefp_123",
        "reference_audio_sha256": "audio_sha_123",
        "reference_text_sha256": "text_sha_123",
        "blocked_reason": "voice_profile_unapproved",
    }
    assert evidence.provider_status == {
        "meeting_tab_ok": False,
        "meeting_tab_detail": "meeting_tab_not_found",
        "meeting_found": False,
        "app_running": True,
        "capabilities_ok": False,
        "capabilities_detail": "mic_switch_unsupported",
        "activation": "supported",
        "mic_switch": "unsupported",
        "mute_recovery": "supported",
    }
    assert evidence.daemon_status == {
        "agent_ok": True,
        "daemon_ok": False,
        "hotkeys_ok": False,
        "heartbeat_fresh": False,
        "running": False,
        "hotkeys_active": False,
        "stdout_log_path": "/tmp/standup/out.log",
        "stderr_log_path": "/tmp/standup/err.log",
        "classification": "stale_heartbeat",
    }
    assert evidence.artifact_paths == (
        str(output_path),
        "/tmp/standup/out.log",
        "/tmp/standup/err.log",
    )
    assert evidence.rerun_commands == (
        "saymo call-ready -p standup --provider glip",
        "saymo voice-profile approve personal",
        "saymo takeover-check -p standup",
        "saymo call-control-agent status -p standup",
        "saymo call-control probe -p standup",
    )
    assert len(evidence.checks) == len(_rich_launch_evidence_report().checks)
    _assert_private_absent(repr(evidence))


def test_launch_evidence_loads_legacy_report_dict_and_skips_bad_check_rows(
    tmp_path,
):
    from saymo.analysis.launch_evidence import load_launch_evidence

    payload = _rich_launch_evidence_report().to_dict()
    payload["checks"].append("not a check")
    legacy_path = tmp_path / "legacy-call-ready.json"
    legacy_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    evidence = load_launch_evidence(legacy_path)

    assert evidence.schema_version == "legacy"
    assert evidence.evidence_kind == "launch-readiness"
    assert evidence.mode == "call-ready"
    assert evidence.path == str(legacy_path)
    assert evidence.check_count == len(_rich_launch_evidence_report().checks)
    assert len(evidence.checks) == len(_rich_launch_evidence_report().checks)
    assert evidence.artifact_paths == (
        str(legacy_path),
        "/tmp/standup/out.log",
        "/tmp/standup/err.log",
    )
    assert evidence.failed_labels[0] == "response cache coverage"


def test_launch_evidence_redacts_sensitive_metadata_names_and_values(tmp_path):
    from saymo.analysis.launch_evidence import load_launch_evidence
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
                action="PRIVATE_TRANSCRIPT",
                rerun="saymo call-ready -p standup --provider glip",
                metadata={
                    "raw_transcript": "PRIVATE_TRANSCRIPT",
                    "generated_answer": "PRIVATE_GENERATED_ANSWER",
                    "answer_text": "SECRET_TOKEN",
                    "audio_bytes": "PRIVATE_DAILY_NOTE",
                    "daily_note_body": "PRIVATE_DAILY_NOTE",
                    "safe_hash": "abc123",
                },
            ),
        ),
    )
    output_path = tmp_path / "call-ready.json"

    write_launch_readiness_artifact(report, output_path)
    raw = output_path.read_text(encoding="utf-8")
    evidence = load_launch_evidence(output_path)
    serialized = json.dumps(evidence.checks, ensure_ascii=False)

    for forbidden in (
        "raw_transcript",
        "generated_answer",
        "answer_text",
        "audio_bytes",
        "daily_note_body",
        *PRIVATE_STRINGS,
    ):
        assert forbidden not in raw
        assert forbidden not in serialized
    assert "safe_hash" in raw
    assert "safe_hash" in serialized

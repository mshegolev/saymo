"""CLI tests for `saymo call-ready`."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from saymo.commands import main


PRIVATE_STRINGS = (
    "PRIVATE_DAILY_NOTE",
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_GENERATED_ANSWER",
    "SECRET_TOKEN",
)

EXPECTED_GROUPED_REMEDIATION = """
remediation:
block:
- [source-data] daily note source ready
  why: placeholder_only
  action: Add usable standup content to daily note, then run saymo prepare -p standup
  rerun: saymo call-ready -p standup --provider glip
- [source-data] response cache coverage
  why: 0/2 variants ready
  action: Run saymo prepare-responses
  rerun: saymo call-ready -p standup --provider glip
- [provider] provider meeting tab
  why: meeting_tab_not_found
  action: Open the glip meeting in Chrome
  rerun: saymo call-ready -p standup --provider glip
- [audio-device] provider output BlackHole
  why: device_not_found
  action: Run saymo test-devices and install BlackHole 2ch/16ch if missing
  rerun: saymo call-ready -p standup --provider glip
- [macos-permission] Chrome automation permission
  why: chrome_automation_blocked
  action: Allow Google Chrome automation and terminal Accessibility permissions, then rerun call-ready.
  rerun: saymo call-ready -p standup --provider glip
warn:
- [voice-cache] cloned voice metadata
  why: voice_profile_unapproved
  action: Approve a cloned voice profile for live calls
  rerun: saymo call-ready -p standup --provider glip
- [provider] provider capabilities
  why: mic_switch_unsupported
  action: Use saymo takeover-check before relying on automated microphone switching for this provider.
  rerun: saymo call-ready -p standup --provider glip
info:
- none
""".strip()


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
            audio:
              capture_device: "BlackHole 16ch"
              playback_device: "BlackHole 2ch"
              recording_device: "MacBook Pro Microphone"
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


def _report(*, ready: bool):
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    check = LaunchReadinessCheck(
        key="daily_note_source",
        label="daily note source",
        severity="info" if ready else "block",
        ok=ready,
        detail="source_sha256=abc123 ready_count=1",
        action="saymo call-ready -p standup --provider glip --prepare",
        rerun="saymo call-ready -p standup --provider glip",
        metadata={"source_sha256": "abc123", "ready_count": 1 if ready else 0},
    )
    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(check,),
    )


def _assert_no_private_text(output: str) -> None:
    for value in PRIVATE_STRINGS:
        assert value not in output


def _top_level_result_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("call-ready: ")]


def _patch_ready_phase36(monkeypatch):
    from saymo.analysis import launch_cache, launch_sources
    from saymo.analysis.launch_readiness import LaunchReadinessCheck

    monkeypatch.setattr(
        launch_sources,
        "collect_daily_note_checks",
        lambda config, profile, *, provider_name, prepare: (
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
        ),
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


def _audio_device(name: str):
    from saymo.audio.devices import AudioDevice

    return AudioDevice(
        index=1,
        name=name,
        max_input_channels=2,
        max_output_channels=2,
        default_samplerate=48000.0,
    )


def test_call_ready_prints_top_level_result(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module

    config_path = _write_config(tmp_path)
    reports = iter((_report(ready=True), _report(ready=False)))

    def fake_collect(config, *, profile: str, provider_name: str | None, prepare: bool):
        assert profile == "standup"
        assert provider_name == "glip"
        assert prepare is False
        return next(reports)

    monkeypatch.setattr(call_ready_module, "collect_launch_readiness", fake_collect)
    runner = CliRunner()

    ready = runner.invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )
    not_ready = runner.invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )

    assert ready.exit_code == 0
    assert not_ready.exit_code == 1
    assert _top_level_result_lines(ready.output) == ["call-ready: ready"]
    assert _top_level_result_lines(not_ready.output) == ["call-ready: not ready"]
    _assert_no_private_text(ready.output)
    _assert_no_private_text(not_ready.output)


def test_call_ready_json_is_sanitized(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module

    config_path = _write_config(tmp_path)
    monkeypatch.setattr(
        call_ready_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare: _report(ready=True),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ready"] is True
    assert payload["profile"] == "standup"
    assert payload["provider"] == "glip"
    assert payload["checks"][0]["key"] == "daily_note_source"
    _assert_no_private_text(result.output)


def test_call_ready_includes_provider_tab_readiness(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    from saymo.analysis import launch_cache, launch_sources
    from saymo.analysis.launch_readiness import LaunchReadinessCheck
    from saymo.audio.devices import AudioDevice
    import saymo.audio.devices as audio_devices
    import saymo.providers.factory as provider_factory
    import sounddevice as sd
    from saymo.providers.base import MeetingStatus

    config_path = _write_config(tmp_path)
    provider = MagicMock()
    provider.name = "glip"
    provider.url_pattern = "app.glip.com"
    provider.check_ready.return_value = MeetingStatus(
        app_running=True,
        meeting_found=True,
        tab_info=(1, 2),
    )
    audio_device = AudioDevice(
        index=1,
        name="available test device",
        max_input_channels=2,
        max_output_channels=2,
        default_samplerate=48000.0,
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    monkeypatch.setattr(audio_devices, "find_device", lambda name, kind="input": audio_device)
    monkeypatch.setattr(sd, "check_input_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "check_output_settings", lambda **kwargs: None)
    monkeypatch.setattr(
        launch_sources,
        "collect_daily_note_checks",
        lambda config, profile, *, provider_name, prepare: (
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
        ),
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

    json_result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--json",
        ],
    )
    human_result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )

    assert json_result.exit_code == 0
    payload = json.loads(json_result.output)
    checks = {check["key"]: check for check in payload["checks"]}
    assert checks["provider_meeting_tab"]["detail"] == "meeting_found"
    assert checks["provider_meeting_tab"]["metadata"]["tab_info"] == [1, 2]
    assert human_result.exit_code == 0
    assert "provider_meeting_tab" in human_result.output
    _assert_no_private_text(json_result.output)
    _assert_no_private_text(human_result.output)


def test_call_ready_provider_audio_checks_are_non_destructive(tmp_path, monkeypatch):
    from saymo.analysis.live_control import HotkeyDoctorReport
    import saymo.analysis.live_control as live_control
    import saymo.audio.devices as audio_devices
    import saymo.audio.macos_audio as macos_audio
    import saymo.audio.multi_play as multi_play
    import saymo.audio.playback as playback
    import saymo.commands.tests as command_tests
    import saymo.providers.factory as provider_factory
    import sounddevice as sd
    import subprocess
    from saymo.providers.base import MeetingStatus

    config_path = _write_config(tmp_path)
    _patch_ready_phase36(monkeypatch)
    provider = MagicMock()
    provider.name = "glip"
    provider.url_pattern = "app.glip.com"
    provider.check_ready.return_value = MeetingStatus(
        app_running=True,
        meeting_found=True,
        tab_info=(1, 2),
    )
    forbidden = MagicMock(
        side_effect=AssertionError("call-ready provider/audio checks must be read-only")
    )
    subprocess_run = MagicMock(
        side_effect=AssertionError("call-ready must not run Chrome kill commands")
    )
    find_calls = []

    def fake_find_device(name, kind="input"):
        find_calls.append((name, kind))
        return _audio_device(name)

    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    monkeypatch.setattr(audio_devices, "find_device", fake_find_device)
    monkeypatch.setattr(
        live_control,
        "build_hotkey_doctor_report",
        lambda config, profile, *, probe=True: HotkeyDoctorReport(
            profile=profile,
            bindings={},
            process_running=False,
            registration_status="no_bindings",
            registration_detail="",
        ),
    )
    monkeypatch.setattr(playback, "play_audio_bytes", forbidden)
    monkeypatch.setattr(multi_play, "play_bytes_to_devices", forbidden)
    monkeypatch.setattr(sd, "check_input_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "check_output_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "rec", forbidden)
    monkeypatch.setattr(macos_audio, "set_input_volume", forbidden)
    monkeypatch.setattr(macos_audio, "bump_input_volume", forbidden)
    monkeypatch.setattr(command_tests, "_write_audio_settings_to_user_config", forbidden)
    monkeypatch.setattr(subprocess, "run", subprocess_run)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
        ],
    )

    assert result.exit_code == 0
    assert _top_level_result_lines(result.output) == ["call-ready: ready"]
    provider.check_ready.assert_called_once_with()
    provider.activate_meeting.assert_not_called()
    provider.toggle_mute.assert_not_called()
    provider.switch_mic.assert_not_called()
    provider.get_previous_app.assert_not_called()
    provider.activate_app.assert_not_called()
    provider.leave_meeting.assert_not_called()
    forbidden.assert_not_called()
    subprocess_run.assert_not_called()
    assert find_calls == [
        ("BlackHole 16ch", "input"),
        ("BlackHole 2ch", "output"),
        ("BlackHole 2ch", "output"),
        ("BlackHole 16ch", "input"),
        ("MacBook Pro Microphone", "input"),
    ]
    _assert_no_private_text(result.output)


def test_call_ready_output_artifact_includes_provider_audio_checks(
    tmp_path,
    monkeypatch,
):
    from saymo.analysis.live_control import HotkeyDoctorReport
    from saymo.analysis import launch_agent
    import saymo.analysis.launch_readiness as launch_readiness
    import saymo.analysis.live_control as live_control
    import saymo.audio.devices as audio_devices
    import saymo.providers.factory as provider_factory
    import sounddevice as sd

    config_path = _write_config(tmp_path)
    output_path = tmp_path / "call-ready.json"
    _patch_ready_phase36(monkeypatch)
    provider = MagicMock()
    provider.name = "glip"
    provider.url_pattern = "PRIVATE_TRANSCRIPT.example"
    provider.check_ready.side_effect = RuntimeError(
        "Google Chrome Automation denied PRIVATE_DAILY_NOTE SECRET_TOKEN"
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    monkeypatch.setattr(
        audio_devices,
        "find_device",
        lambda name, kind="input": _audio_device(name),
    )
    monkeypatch.setattr(sd, "check_input_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "check_output_settings", lambda **kwargs: None)
    monkeypatch.setattr(
        live_control,
        "build_hotkey_doctor_report",
        lambda config, profile, *, probe=True: HotkeyDoctorReport(
            profile=profile,
            bindings={},
            process_running=False,
            registration_status="no_bindings",
            registration_detail="",
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

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1
    assert _top_level_result_lines(result.output) == ["call-ready: not ready"]
    assert f"artifact: {output_path}" in result.output
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    keys = [check["key"] for check in payload["checks"]]
    assert {
        "provider_meeting_tab",
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "recording_microphone_input",
        "provider_capabilities",
        "call_control_agent",
        "call_control_daemon",
        "call_control_hotkeys",
    }.issubset(keys)
    old_placeholder_key = "provider" + "_audio_basic_scope"
    assert old_placeholder_key not in keys
    assert any(key.endswith("_permission") for key in keys)
    assert payload == json.loads(output_path.read_text(encoding="utf-8"))
    expected_phase37_order = (
        "provider_meeting_tab",
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
        "recording_microphone_input",
        "provider_capabilities",
    )
    cloned_voice_index = keys.index("cloned_voice_metadata")
    assert tuple(keys[cloned_voice_index + 1 : cloned_voice_index + 8]) == (
        expected_phase37_order
    )
    assert expected_phase37_order == launch_readiness._LAUNCH_CHECK_ORDER[5:12]
    assert tuple(keys[cloned_voice_index + 8 : cloned_voice_index + 11]) == (
        "call_control_agent",
        "call_control_daemon",
        "call_control_hotkeys",
    )
    daemon = {check["key"]: check for check in payload["checks"]}["call_control_daemon"]
    assert daemon["metadata"]["stdout_log_path"].endswith(".out.log")
    assert daemon["metadata"]["stderr_log_path"].endswith(".err.log")
    _assert_no_private_text(result.output)
    _assert_no_private_text(json.dumps(payload, ensure_ascii=False))


def test_call_ready_daemon_rows_are_read_only_and_do_not_run_probe(
    tmp_path,
    monkeypatch,
):
    from saymo.analysis.live_control import HotkeyDoctorReport
    from saymo.analysis import control_daemon, launch_agent
    import saymo.analysis.live_control as live_control
    import saymo.audio.devices as audio_devices
    import saymo.providers.factory as provider_factory
    import sounddevice as sd
    from saymo.providers.base import MeetingStatus

    config_path = _write_config(tmp_path)
    _patch_ready_phase36(monkeypatch)
    provider = MagicMock()
    provider.name = "glip"
    provider.url_pattern = "app.glip.com"
    provider.check_ready.return_value = MeetingStatus(
        app_running=True,
        meeting_found=True,
        tab_info=(1, 2),
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    monkeypatch.setattr(
        audio_devices,
        "find_device",
        lambda name, kind="input": _audio_device(name),
    )
    monkeypatch.setattr(sd, "check_input_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "check_output_settings", lambda **kwargs: None)
    monkeypatch.setattr(
        live_control,
        "build_hotkey_doctor_report",
        lambda config, profile, *, probe=True: HotkeyDoctorReport(
            profile=profile,
            bindings={},
            process_running=False,
            registration_status="no_bindings",
            registration_detail="",
        ),
    )
    monkeypatch.setattr(
        control_daemon,
        "run_handbrake_reachability_probe",
        MagicMock(side_effect=AssertionError("call-ready must not run probe")),
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
                "heartbeat_fresh": False,
                "running": False,
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

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--json",
        ],
    )

    payload = json.loads(result.output)
    checks = {check["key"]: check for check in payload["checks"]}
    assert result.exit_code == 1
    assert checks["call_control_agent"]["metadata"]["category"] == "call-control"
    assert checks["call_control_daemon"]["ok"] is False
    assert checks["call_control_daemon"]["rerun"] == "saymo call-control probe -p standup"
    assert checks["call_control_hotkeys"]["metadata"]["category"] == "macos-permission"
    assert checks["call_control_hotkeys"]["metadata"]["stdout_log_path"].endswith(".out.log")
    assert not (tmp_path / "standup" / "commands.jsonl").exists()


def test_call_ready_output_artifact_does_not_pollute_json_stdout(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module

    config_path = _write_config(tmp_path)
    output_path = tmp_path / "call-ready.json"
    monkeypatch.setattr(
        call_ready_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare: _report(ready=True),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--output",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert "artifact:" not in result.output
    payload = json.loads(result.output)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ready"] is True
    assert artifact["ready"] is True
    _assert_no_private_text(result.output)


def test_call_ready_prepare_creates_note_without_overwrite(tmp_path):
    from datetime import date

    vault = tmp_path / "Vault"
    vault.mkdir()
    today = vault / f"{date.today().strftime('%Y-%m-%d')}.md"
    existing = "already written\n"
    today.write_text(existing, encoding="utf-8")
    config_path = _write_config(tmp_path, vault_path=vault)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--prepare",
        ],
    )

    assert today.read_text(encoding="utf-8") == existing
    assert "call-ready:" in result.output
    _assert_no_private_text(result.output)

    today.unlink()
    created = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--prepare",
        ],
    )

    assert today.exists()
    assert "## Standup" in today.read_text(encoding="utf-8")
    assert "call-ready:" in created.output
    _assert_no_private_text(created.output)


def test_call_ready_groups_remediation_with_rerun_commands(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module
    from saymo.analysis.launch_readiness import LaunchReadinessCheck, LaunchReadinessReport

    config_path = _write_config(tmp_path)
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
                action="Add usable standup content to daily note, then run saymo prepare -p standup",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="response_cache_coverage",
                label="response cache coverage",
                severity="block",
                ok=False,
                detail="0/2 variants ready",
                action="Run saymo prepare-responses",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="provider_meeting_tab",
                label="provider meeting tab",
                severity="block",
                ok=False,
                detail="meeting_tab_not_found",
                action="Open the glip meeting in Chrome",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="provider_output_blackhole",
                label="provider output BlackHole",
                severity="block",
                ok=False,
                detail="device_not_found",
                action="Run saymo test-devices and install BlackHole 2ch/16ch if missing",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="chrome_automation_permission",
                label="Chrome automation permission",
                severity="block",
                ok=False,
                detail="chrome_automation_blocked",
                action=(
                    "Allow Google Chrome automation and terminal Accessibility "
                    "permissions, then rerun call-ready."
                ),
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
                key="provider_capabilities",
                label="provider capabilities",
                severity="warn",
                ok=False,
                detail="mic_switch_unsupported",
                action=(
                    "Use saymo takeover-check before relying on automated "
                    "microphone switching for this provider."
                ),
                rerun="saymo call-ready -p standup --provider glip",
            ),
        ),
    )
    monkeypatch.setattr(
        call_ready_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare: report,
    )

    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )

    assert result.exit_code == 1
    assert _top_level_result_lines(result.output) == ["call-ready: not ready"]
    for line in EXPECTED_GROUPED_REMEDIATION.splitlines():
        assert line in result.output
    _assert_no_private_text(result.output)

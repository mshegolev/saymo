"""Tests for provider/audio launch-readiness checks."""

from __future__ import annotations

import json
import textwrap
from unittest.mock import MagicMock

from saymo.audio.devices import AudioDevice
from saymo.config import load_config
from saymo.providers.base import MeetingStatus


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            user:
              name: "John"
              name_variants:
                - "John"
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


def _config(tmp_path):
    return load_config(config_path=str(_write_config(tmp_path)))


def _provider(*, status: MeetingStatus | None = None):
    provider = MagicMock()
    provider.name = "glip"
    provider.url_pattern = "app.glip.com"
    provider.check_ready.return_value = status or MeetingStatus(
        app_running=True,
        meeting_found=True,
        tab_info=(1, 2),
    )
    return provider


def _assert_provider_mutators_not_called(provider):
    provider.activate_meeting.assert_not_called()
    provider.toggle_mute.assert_not_called()
    provider.switch_mic.assert_not_called()
    provider.get_previous_app.assert_not_called()
    provider.activate_app.assert_not_called()


def _device(index: int, name: str) -> AudioDevice:
    return AudioDevice(
        index=index,
        name=name,
        max_input_channels=2,
        max_output_channels=2,
        default_samplerate=48000.0,
    )


def test_provider_tab_readiness_reports_found_missing_and_errors(tmp_path, monkeypatch):
    from saymo.analysis.provider_audio_readiness import collect_provider_tab_check
    import saymo.providers.factory as provider_factory

    config = _config(tmp_path)
    found_provider = _provider()
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: found_provider)

    found = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert found.key == "provider_meeting_tab"
    assert found.label == "provider meeting tab"
    assert found.severity == "block"
    assert found.ok is True
    assert found.detail == "meeting_found"
    assert found.metadata["category"] == "provider"
    assert found.metadata["provider_name"] == "glip"
    assert found.metadata["configured_provider"] == "glip"
    assert found.metadata["url_pattern"] == "app.glip.com"
    assert found.metadata["meeting_found"] is True
    assert found.metadata["app_running"] is True
    assert found.metadata["tab_info"] == [1, 2]

    missing_provider = _provider(
        status=MeetingStatus(
            app_running=True,
            meeting_found=False,
            tab_info=None,
        )
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: missing_provider)

    missing = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert missing.key == "provider_meeting_tab"
    assert missing.severity == "block"
    assert missing.ok is False
    assert missing.detail == "meeting_tab_not_found"
    assert missing.action == "Open the glip meeting in Chrome"
    assert missing.rerun == "saymo call-ready -p standup --provider glip"
    assert missing.metadata["meeting_found"] is False
    assert missing.metadata["tab_info"] is None

    def raise_unknown(name):
        raise ValueError("Unknown provider: unknown. Available: glip")

    monkeypatch.setattr(provider_factory, "get_provider", raise_unknown)

    unknown = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="unknown",
    )

    assert unknown.key == "provider_meeting_tab"
    assert unknown.severity == "block"
    assert unknown.ok is False
    assert unknown.detail == "unknown_provider"
    assert unknown.action == "Use a supported provider name, then rerun saymo call-ready"
    assert unknown.rerun == "saymo call-ready -p standup --provider unknown"
    assert unknown.metadata["configured_provider"] == "unknown"
    assert unknown.metadata["provider_name"] == "unknown"
    assert unknown.metadata["error_type"] == "ValueError"

    def raise_factory_error(name):
        raise RuntimeError("SECRET_TOKEN factory denied")

    monkeypatch.setattr(provider_factory, "get_provider", raise_factory_error)

    factory_error = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert factory_error.key == "provider_meeting_tab"
    assert factory_error.severity == "block"
    assert factory_error.ok is False
    assert factory_error.detail == "provider_check_error"
    assert factory_error.action == (
        "Open Chrome, allow provider automation permissions, then rerun saymo call-ready"
    )
    assert factory_error.rerun == "saymo call-ready -p standup --provider glip"
    assert factory_error.metadata["error_type"] == "RuntimeError"
    assert "SECRET_TOKEN" not in json.dumps(factory_error.to_dict(), ensure_ascii=False)

    check_error_provider = _provider()
    check_error_provider.check_ready.side_effect = RuntimeError(
        "SECRET_TOKEN check denied"
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: check_error_provider)

    check_error = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert check_error.key == "provider_meeting_tab"
    assert check_error.severity == "block"
    assert check_error.ok is False
    assert check_error.detail == "provider_check_error"
    assert check_error.rerun == "saymo call-ready -p standup --provider glip"
    assert check_error.metadata["error_type"] == "RuntimeError"
    assert "SECRET_TOKEN" not in json.dumps(check_error.to_dict(), ensure_ascii=False)


def test_audio_route_checks_validate_expected_devices_and_kinds(tmp_path, monkeypatch):
    from saymo.analysis.provider_audio_readiness import collect_audio_route_checks
    import saymo.audio.devices as audio_devices

    config = _config(tmp_path)
    config.audio.capture_device = "Call Capture Device"
    config.audio.playback_device = "Conference Headphones"
    config.audio.recording_device = "MacBook Pro Microphone"
    found_devices = {
        ("Call Capture Device", "input"): _device(1, "Call Capture Device"),
        ("Conference Headphones", "output"): _device(2, "Conference Headphones"),
        ("BlackHole 2ch", "output"): _device(3, "BlackHole 2ch"),
        ("MacBook Pro Microphone", "input"): _device(4, "MacBook Pro Microphone"),
    }
    calls = []

    def fake_find_device(name, kind="input"):
        calls.append((name, kind))
        return found_devices.get((name, kind))

    monkeypatch.setattr(audio_devices, "find_device", fake_find_device)

    checks = collect_audio_route_checks(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert calls == [
        ("Call Capture Device", "input"),
        ("Conference Headphones", "output"),
        ("BlackHole 2ch", "output"),
        ("BlackHole 16ch", "input"),
        ("MacBook Pro Microphone", "input"),
    ]
    assert [check.key for check in checks] == [
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
        "recording_microphone_input",
    ]
    by_key = {check.key: check for check in checks}
    capture = by_key["capture_input_device"]
    assert capture.ok is True
    assert capture.severity == "block"
    assert capture.metadata == {
        "category": "audio-device",
        "device_name": "Call Capture Device",
        "kind": "input",
        "required": True,
        "found": True,
        "device": {
            "index": 1,
            "name": "Call Capture Device",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48000.0,
        },
    }

    missing_blackhole = by_key["capture_route_blackhole"]
    assert missing_blackhole.ok is False
    assert missing_blackhole.severity == "block"
    assert missing_blackhole.detail == "device_not_found"
    assert "saymo test-devices" in missing_blackhole.action
    assert "install BlackHole" in missing_blackhole.action
    assert "switch" not in missing_blackhole.action.lower()
    assert missing_blackhole.rerun == "saymo call-ready -p standup --provider glip"
    assert missing_blackhole.metadata == {
        "category": "audio-device",
        "device_name": "BlackHole 16ch",
        "kind": "input",
        "required": True,
        "found": False,
    }


def test_provider_capabilities_are_reported_without_actions(tmp_path):
    from saymo.analysis.provider_audio_readiness import collect_provider_capability_checks
    from saymo.providers._chrome_base import ChromeCallProvider
    from saymo.providers.glip import GlipProvider
    from saymo.providers.mts_link import MTSLinkProvider

    class GenericChromeProvider(ChromeCallProvider):
        name = "generic"
        url_pattern = "generic.example"

    config = _config(tmp_path)
    generic = GenericChromeProvider()
    generic.check_ready = MagicMock()
    generic.activate_meeting = MagicMock()
    generic.toggle_mute = MagicMock()
    generic.switch_mic = MagicMock()
    generic.get_previous_app = MagicMock()
    generic.activate_app = MagicMock()

    generic_checks = collect_provider_capability_checks(
        config,
        profile="standup",
        provider_name="generic",
        provider=generic,
    )

    assert len(generic_checks) == 1
    generic_check = generic_checks[0]
    assert generic_check.key == "provider_capabilities"
    assert generic_check.label == "provider capabilities"
    assert generic_check.severity == "warn"
    assert generic_check.ok is False
    assert generic_check.detail == "mic_switch_unsupported"
    assert generic_check.rerun == "saymo call-ready -p standup --provider generic"
    assert generic_check.metadata["category"] == "provider"
    assert generic_check.metadata["provider_name"] == "generic"
    assert generic_check.metadata["configured_provider"] == "generic"
    assert generic_check.metadata["tab_activation_supported"] is True
    assert generic_check.metadata["mute_recovery_supported"] is True
    assert generic_check.metadata["mic_switch_supported"] is False
    assert generic_check.metadata["mic_switch_status"] == "mic_switch_unsupported"
    assert generic_check.metadata["capability_limitations"] == [
        "mic_switch_unsupported"
    ]
    generic.check_ready.assert_not_called()
    _assert_provider_mutators_not_called(generic)

    for provider in (GlipProvider(), MTSLinkProvider()):
        provider.check_ready = MagicMock()
        provider.activate_meeting = MagicMock()
        provider.toggle_mute = MagicMock()
        provider.switch_mic = MagicMock()
        provider.get_previous_app = MagicMock()
        provider.activate_app = MagicMock()

        checks = collect_provider_capability_checks(
            config,
            profile="standup",
            provider_name=provider.name,
            provider=provider,
        )

        assert len(checks) == 1
        check = checks[0]
        assert check.key == "provider_capabilities"
        assert check.severity == "info"
        assert check.ok is True
        assert check.detail == "provider_capabilities_supported"
        assert check.metadata["tab_activation_supported"] is True
        assert check.metadata["mute_recovery_supported"] is True
        assert check.metadata["mic_switch_supported"] is True
        assert check.metadata["mic_switch_status"] == "mic_switch_supported"
        assert check.metadata["capability_limitations"] == []
        provider.check_ready.assert_not_called()
        _assert_provider_mutators_not_called(provider)


def test_permission_blockers_are_actionable(tmp_path, monkeypatch):
    from saymo.analysis.live_control import HotkeyDoctorReport
    from saymo.analysis.provider_audio_readiness import collect_permission_checks
    import saymo.analysis.live_control as live_control
    import saymo.audio.macos_audio as macos_audio
    import saymo.commands.tests as command_tests
    import sounddevice

    config = _config(tmp_path)
    doctor_calls = []

    def fake_hotkey_report(config_arg, profile, *, probe=True):
        doctor_calls.append((config_arg, profile, probe))
        return HotkeyDoctorReport(
            profile=profile,
            bindings={"toggle_auto_answer": "<cmd>+<shift>+m"},
            process_running=False,
            registration_status="blocked",
            registration_detail="Accessibility denied",
        )

    def forbidden(*args, **kwargs):
        raise AssertionError("permission checks must not mutate audio/provider state")

    provider = _provider()
    monkeypatch.setattr(live_control, "build_hotkey_doctor_report", fake_hotkey_report)
    monkeypatch.setattr("saymo.audio.playback.play_audio_bytes", forbidden)
    monkeypatch.setattr("saymo.audio.multi_play.play_bytes_to_devices", forbidden)
    monkeypatch.setattr("sounddevice.rec", forbidden)
    monkeypatch.setattr(macos_audio, "set_input_volume", forbidden)
    monkeypatch.setattr(macos_audio, "bump_input_volume", forbidden)
    monkeypatch.setattr(
        command_tests,
        "_write_audio_settings_to_user_config",
        forbidden,
    )

    checks = collect_permission_checks(
        config,
        profile="standup",
        provider_name="glip",
        provider_error="osascript: Not authorized to send Apple events to Google Chrome",
        microphone_permission_blocked=True,
        audio_routing_permission_blocked=True,
    )

    assert doctor_calls == [(config, "standup", True)]
    assert sounddevice.rec is forbidden
    assert [check.key for check in checks] == [
        "chrome_automation_permission",
        "hotkey_accessibility_permission",
        "microphone_capture_permission",
        "audio_routing_permission",
    ]
    by_key = {check.key: check for check in checks}
    assert by_key["chrome_automation_permission"].metadata["category"] == (
        "macos-permission"
    )
    assert by_key["chrome_automation_permission"].detail == "chrome_automation_blocked"
    assert by_key["chrome_automation_permission"].action == (
        "Allow Google Chrome automation and terminal Accessibility permissions, "
        "then rerun call-ready."
    )
    assert by_key["chrome_automation_permission"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    assert by_key["hotkey_accessibility_permission"].metadata["category"] == (
        "macos-permission"
    )
    assert by_key["hotkey_accessibility_permission"].detail == (
        "hotkey_accessibility_blocked"
    )
    assert by_key["hotkey_accessibility_permission"].action == (
        "Allow the terminal app running Saymo in macOS Accessibility settings."
    )
    assert by_key["hotkey_accessibility_permission"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    assert by_key["microphone_capture_permission"].metadata["category"] == (
        "macos-permission"
    )
    assert by_key["microphone_capture_permission"].detail == (
        "microphone_capture_permission_blocked"
    )
    assert by_key["microphone_capture_permission"].action == (
        "Allow microphone access for the terminal app running Saymo, "
        "then rerun call-ready."
    )
    assert by_key["microphone_capture_permission"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    assert by_key["audio_routing_permission"].metadata["category"] == (
        "macos-permission"
    )
    assert by_key["audio_routing_permission"].detail == (
        "audio_routing_permission_blocked"
    )
    assert by_key["audio_routing_permission"].action == (
        "Verify BlackHole permissions/routes in macOS Audio MIDI Setup and allow "
        "required audio access, then rerun call-ready."
    )
    assert by_key["audio_routing_permission"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    _assert_provider_mutators_not_called(provider)


def test_collect_provider_audio_checks_detects_default_permission_blockers(
    tmp_path,
    monkeypatch,
):
    from saymo.analysis.live_control import HotkeyDoctorReport
    from saymo.analysis.provider_audio_readiness import collect_provider_audio_checks
    import saymo.analysis.live_control as live_control
    import saymo.audio.devices as audio_devices
    import saymo.providers.factory as provider_factory
    import sounddevice as sd

    config = _config(tmp_path)
    config.audio.recording_device = "MacBook Pro Microphone"
    provider = _provider()
    provider.check_ready.side_effect = RuntimeError(
        "osascript: Not authorized to send Apple events to Google Chrome"
    )
    devices = {
        ("BlackHole 16ch", "input"): _device(1, "BlackHole 16ch"),
        ("BlackHole 2ch", "output"): _device(2, "BlackHole 2ch"),
        ("MacBook Pro Microphone", "input"): _device(3, "MacBook Pro Microphone"),
    }
    input_checks = []
    output_checks = []

    def fake_find_device(name, kind="input"):
        return devices.get((name, kind))

    def fake_check_input_settings(*, device=None, samplerate=None):
        input_checks.append((device, samplerate))
        if device == 3:
            raise RuntimeError("Input device unavailable: permission denied")

    def fake_check_output_settings(*, device=None, samplerate=None):
        output_checks.append((device, samplerate))
        if device == 2:
            raise RuntimeError("Output route unavailable: permission denied")

    def forbidden(*args, **kwargs):
        raise AssertionError("permission probes must not record or play audio")

    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    monkeypatch.setattr(audio_devices, "find_device", fake_find_device)
    monkeypatch.setattr(
        live_control,
        "build_hotkey_doctor_report",
        lambda config, profile, *, probe=True: HotkeyDoctorReport(
            profile=profile,
            bindings={},
            process_running=False,
            registration_status="skipped",
            registration_detail="",
        ),
    )
    monkeypatch.setattr(sd, "check_input_settings", fake_check_input_settings)
    monkeypatch.setattr(sd, "check_output_settings", fake_check_output_settings)
    monkeypatch.setattr(sd, "rec", forbidden)

    checks = collect_provider_audio_checks(
        config,
        profile="standup",
        provider_name="glip",
    )

    by_key = {check.key: check for check in checks}
    assert by_key["provider_meeting_tab"].detail == "provider_check_error"
    assert by_key["chrome_automation_permission"].detail == "chrome_automation_blocked"
    assert by_key["microphone_capture_permission"].detail == (
        "microphone_capture_permission_blocked"
    )
    assert by_key["audio_routing_permission"].detail == (
        "audio_routing_permission_blocked"
    )
    assert input_checks == [(1, 48000.0), (1, 48000.0), (3, 48000.0)]
    assert output_checks == [(2, 48000.0), (2, 48000.0)]
    provider.check_ready.assert_called_once_with()
    _assert_provider_mutators_not_called(provider)


def test_provider_audio_checks_accept_dry_run_context_without_breaking_call_ready(
    tmp_path,
    monkeypatch,
):
    from saymo.analysis.live_control import HotkeyDoctorReport
    from saymo.analysis.provider_audio_readiness import (
        collect_provider_audio_checks,
        collect_provider_tab_check,
    )
    import saymo.analysis.live_control as live_control
    import saymo.audio.devices as audio_devices
    import saymo.providers.factory as provider_factory
    import sounddevice as sd

    config = _config(tmp_path)
    config.audio.capture_device = "Call Capture Device"
    config.audio.playback_device = "Conference Headphones"
    config.audio.recording_device = "MacBook Pro Microphone"
    provider = _provider(
        status=MeetingStatus(
            app_running=True,
            meeting_found=False,
            tab_info=None,
        )
    )
    found_devices = {
        ("BlackHole 16ch", "input"): _device(16, "BlackHole 16ch"),
        ("MacBook Pro Microphone", "input"): _device(
            4,
            "MacBook Pro Microphone",
        ),
    }
    input_checks = []
    output_checks = []

    def fake_find_device(name, kind="input"):
        return found_devices.get((name, kind))

    def fake_hotkey_report(config_arg, profile, *, probe=True):
        assert config_arg is config
        assert profile == "standup"
        assert probe is True
        return HotkeyDoctorReport(
            profile=profile,
            bindings={"toggle_auto_answer": "<cmd>+<shift>+m"},
            process_running=False,
            registration_status="blocked",
            registration_detail="Accessibility denied",
        )

    def fake_check_input_settings(*, device=None, samplerate=None):
        input_checks.append((device, samplerate))
        if device in {4, 16}:
            raise RuntimeError("SECRET_TOKEN input permission denied")

    def fake_check_output_settings(*, device=None, samplerate=None):
        output_checks.append((device, samplerate))

    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    monkeypatch.setattr(audio_devices, "find_device", fake_find_device)
    monkeypatch.setattr(live_control, "build_hotkey_doctor_report", fake_hotkey_report)
    monkeypatch.setattr(sd, "check_input_settings", fake_check_input_settings)
    monkeypatch.setattr(sd, "check_output_settings", fake_check_output_settings)

    dry_run_rerun = "saymo dry-run -p standup --provider glip"
    dry_run_checks = collect_provider_audio_checks(
        config,
        profile="standup",
        provider_name="glip",
        rerun_command=dry_run_rerun,
        mode="dry-run",
    )
    by_key = {check.key: check for check in dry_run_checks}

    assert [check.key for check in dry_run_checks] == [
        "provider_meeting_tab",
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
        "recording_microphone_input",
        "provider_capabilities",
        "hotkey_accessibility_permission",
        "microphone_capture_permission",
        "audio_routing_permission",
    ]
    assert by_key["provider_meeting_tab"].action == (
        "Open the glip meeting in Chrome"
    )
    assert by_key["provider_meeting_tab"].rerun == dry_run_rerun
    assert by_key["provider_meeting_tab"].metadata == {
        "category": "provider",
        "provider_name": "glip",
        "configured_provider": "glip",
        "url_pattern": "app.glip.com",
        "meeting_found": False,
        "app_running": True,
        "tab_info": None,
    }

    for key in (
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
    ):
        check = by_key[key]
        assert check.ok is False
        assert check.rerun == dry_run_rerun
        assert "saymo test-devices" in check.action
        assert "switch" not in check.action.lower()
        assert check.metadata["category"] == "audio-device"
        assert check.metadata["device_name"]
        assert check.metadata["kind"] in {"input", "output"}
        assert check.metadata["required"] is True
        assert check.metadata["found"] is False

    capture_route = by_key["capture_route_blackhole"]
    assert capture_route.ok is True
    assert capture_route.metadata == {
        "category": "audio-device",
        "device_name": "BlackHole 16ch",
        "kind": "input",
        "required": True,
        "found": True,
        "device": {
            "index": 16,
            "name": "BlackHole 16ch",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48000.0,
        },
    }
    recording = by_key["recording_microphone_input"]
    assert recording.ok is True
    assert recording.metadata["device"]["index"] == 4

    capabilities = by_key["provider_capabilities"]
    assert capabilities.metadata["category"] == "provider"
    assert capabilities.metadata["provider_name"] == "glip"
    assert capabilities.metadata["configured_provider"] == "glip"
    assert capabilities.rerun == dry_run_rerun
    assert "switch" in capabilities.action.lower()

    for key in (
        "hotkey_accessibility_permission",
        "microphone_capture_permission",
        "audio_routing_permission",
    ):
        check = by_key[key]
        assert check.metadata["category"] == "macos-permission"
        assert check.rerun == dry_run_rerun
        assert "automatically" not in check.action.lower()
        assert "switch" not in check.action.lower()
        assert "call-ready" not in check.action

    assert input_checks == [(16, 48000.0), (4, 48000.0)]
    assert output_checks == []
    assert "SECRET_TOKEN" not in json.dumps(
        [check.to_dict() for check in dry_run_checks],
        ensure_ascii=False,
    )

    error_provider = _provider()
    error_provider.check_ready.side_effect = RuntimeError(
        "SECRET_TOKEN provider denied"
    )
    monkeypatch.setattr(
        provider_factory,
        "get_provider",
        lambda name: error_provider,
    )

    provider_error = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
        rerun_command=dry_run_rerun,
        mode="dry-run",
    )

    assert provider_error.detail == "provider_check_error"
    assert provider_error.metadata["error_type"] == "RuntimeError"
    assert provider_error.rerun == dry_run_rerun
    assert "dry-run" in provider_error.action
    assert "call-ready" not in provider_error.action
    assert "SECRET_TOKEN" not in json.dumps(provider_error.to_dict(), ensure_ascii=False)

    def raise_unknown(name):
        raise ValueError("Unknown provider: unknown. SECRET_TOKEN")

    monkeypatch.setattr(provider_factory, "get_provider", raise_unknown)

    unknown = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="unknown",
        rerun_command="saymo dry-run -p standup --provider unknown",
        mode="dry-run",
    )

    assert unknown.detail == "unknown_provider"
    assert unknown.metadata["error_type"] == "ValueError"
    assert unknown.rerun == "saymo dry-run -p standup --provider unknown"
    assert "dry-run" in unknown.action
    assert "call-ready" not in unknown.action
    assert "SECRET_TOKEN" not in json.dumps(unknown.to_dict(), ensure_ascii=False)

    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    call_ready_checks = collect_provider_audio_checks(
        config,
        profile="standup",
        provider_name="glip",
    )
    call_ready = {check.key: check for check in call_ready_checks}

    assert call_ready["provider_meeting_tab"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    assert call_ready["capture_input_device"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    assert call_ready["hotkey_accessibility_permission"].rerun == (
        "saymo call-ready -p standup --provider glip"
    )
    _assert_provider_mutators_not_called(provider)


def test_collect_provider_audio_checks_is_non_destructive(tmp_path, monkeypatch):
    from saymo.analysis.provider_audio_readiness import collect_provider_audio_checks
    import saymo.audio.devices as audio_devices
    import saymo.audio.macos_audio as macos_audio
    import saymo.audio.multi_play as multi_play
    import saymo.audio.playback as playback
    import saymo.commands.tests as command_tests
    import saymo.providers.factory as provider_factory
    import sounddevice as sd

    provider = _provider()
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)
    config = _config(tmp_path)
    config.audio.recording_device = "MacBook Pro Microphone"
    find_calls = []

    def fake_find_device(name, kind="input"):
        find_calls.append((name, kind))
        return _device(len(find_calls), name)

    def forbidden(*args, **kwargs):
        raise AssertionError("call-ready provider/audio checks must be read-only")

    monkeypatch.setattr(audio_devices, "find_device", fake_find_device)
    monkeypatch.setattr(playback, "play_audio_bytes", forbidden)
    monkeypatch.setattr(multi_play, "play_bytes_to_devices", forbidden)
    monkeypatch.setattr(sd, "check_input_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "check_output_settings", lambda **kwargs: None)
    monkeypatch.setattr(sd, "rec", forbidden)
    monkeypatch.setattr(macos_audio, "set_input_volume", forbidden)
    monkeypatch.setattr(macos_audio, "bump_input_volume", forbidden)
    monkeypatch.setattr(
        command_tests,
        "_write_audio_settings_to_user_config",
        forbidden,
    )

    checks = collect_provider_audio_checks(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert isinstance(checks, tuple)
    assert checks[0].key == "provider_meeting_tab"
    assert [check.key for check in checks[1:]] == [
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
        "recording_microphone_input",
        "provider_capabilities",
    ]
    assert find_calls == [
        ("BlackHole 16ch", "input"),
        ("BlackHole 2ch", "output"),
        ("BlackHole 2ch", "output"),
        ("BlackHole 16ch", "input"),
        ("MacBook Pro Microphone", "input"),
    ]
    provider.check_ready.assert_called_once_with()
    _assert_provider_mutators_not_called(provider)

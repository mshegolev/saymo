"""CLI tests for `saymo takeover-check` diagnostics."""

import textwrap
from unittest.mock import MagicMock

from click.testing import CliRunner

from saymo.commands import main
from saymo.providers.base import MeetingStatus


def _write_config(tmp_path, *, recording_device: str = "MacBook Pro Microphone"):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            audio:
              recording_device: "{recording_device}"
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "Миша"
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_takeover_check_switches_to_recording_mic_and_back(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    provider = MagicMock()
    provider.name = "glip"
    provider.check_ready.return_value = MeetingStatus(
        app_running=True,
        meeting_found=True,
        tab_info=(1, 2),
    )
    provider.switch_mic.return_value = True
    monkeypatch.setattr("saymo.providers.factory.get_provider", lambda name: provider)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "takeover-check",
            "--profile",
            "personal",
        ],
    )

    assert result.exit_code == 0
    assert "provider: glip" in result.output
    assert "meeting: yes" in result.output
    assert "switch to recording mic: yes" in result.output
    assert "switch back to Saymo mic: yes" in result.output
    assert "takeover: ready" in result.output
    assert provider.switch_mic.call_args_list[0].args == ("MacBook Pro Microphone",)
    assert provider.switch_mic.call_args_list[1].args == ("BlackHole 2ch",)


def test_takeover_check_reports_missing_recording_device(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path, recording_device="")
    get_provider = MagicMock()
    monkeypatch.setattr("saymo.providers.factory.get_provider", get_provider)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "takeover-check",
            "--profile",
            "personal",
        ],
    )

    assert result.exit_code == 0
    assert "recording mic: (not configured)" in result.output
    assert "takeover: not ready" in result.output
    get_provider.assert_not_called()


def test_takeover_check_reports_missing_meeting_tab(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    provider = MagicMock()
    provider.name = "glip"
    provider.check_ready.return_value = MeetingStatus(
        app_running=True,
        meeting_found=False,
        tab_info=None,
    )
    monkeypatch.setattr("saymo.providers.factory.get_provider", lambda name: provider)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "takeover-check",
            "--profile",
            "personal",
        ],
    )

    assert result.exit_code == 0
    assert "meeting: no" in result.output
    assert "takeover: not ready" in result.output
    provider.switch_mic.assert_not_called()

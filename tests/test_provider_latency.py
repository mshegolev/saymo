"""CLI tests for provider latency probe diagnostics."""

from types import SimpleNamespace
import json
import textwrap

from click.testing import CliRunner

from saymo.commands import main
from saymo.providers.base import MeetingStatus


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            user:
              name: "John"
              name_variants:
                - "John"
              language: ru
            audio:
              capture_device: "BlackHole 16ch"
              playback_device: "BlackHole 2ch"
              monitor_device: ""
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_provider_latency_probe_exports_json_and_markdown(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    audio_path = tmp_path / "probe.wav"
    audio_path.write_bytes(b"probe-audio")
    history_dir = tmp_path / "history"
    calls = []

    class Provider:
        name = "glip"

        def check_ready(self):
            calls.append("check_ready")
            return MeetingStatus(
                app_running=True,
                meeting_found=True,
                tab_info=(1, 2),
            )

        def switch_mic(self, device_name):
            calls.append(("switch_mic", device_name))
            return True

        def get_previous_app(self):
            calls.append("get_previous_app")
            return "Terminal"

        def activate_meeting(self):
            calls.append("activate_meeting")
            return True

        def toggle_mute(self):
            calls.append("toggle_mute")

        def activate_app(self, app_name):
            calls.append(("activate_app", app_name))

    async def fake_play_audio_bytes(audio_bytes, playback):
        calls.append(("play", playback, audio_bytes))

    monkeypatch.setattr("saymo.providers.factory.get_provider", lambda name: Provider())
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda name, kind=None: SimpleNamespace(index=1) if name else None,
    )
    monkeypatch.setattr("saymo.audio.playback.play_audio_bytes", fake_play_audio_bytes)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "provider-latency",
            "--profile",
            "personal",
            "--text",
            "John, что по статусу?",
            "--audio",
            str(audio_path),
            "--output-dir",
            str(history_dir),
            "--settle-seconds",
            "0",
        ],
    )

    assert result.exit_code == 0
    assert "provider latency: profile=personal provider=glip" in result.output
    assert "capture:" in result.output
    assert "transcription:" in result.output
    assert "trigger:" in result.output
    assert "provider unmute:" in result.output
    assert "playback start:" in result.output
    assert "playback duration:" in result.output
    assert "mute recovery:" in result.output
    assert "probe: ok" in result.output
    assert "history json:" in result.output
    assert "history markdown:" in result.output
    assert ("switch_mic", "BlackHole 2ch") in calls
    assert "toggle_mute" in calls
    assert ("play", "BlackHole 2ch", b"probe-audio") in calls

    json_files = sorted((history_dir / "personal" / "glip").glob("*.json"))
    markdown_files = sorted((history_dir / "personal" / "glip").glob("*.md"))
    assert len(json_files) == 1
    assert len(markdown_files) == 1
    data = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert data["status"] == "ok"
    assert data["profile"] == "personal"
    assert data["provider"] == "glip"
    assert {segment["name"] for segment in data["segments"]} >= {
        "capture",
        "transcription",
        "trigger",
        "provider_unmute",
        "playback_start",
        "playback_duration",
        "mute_recovery",
    }
    assert "probe: ok" in markdown_files[0].read_text(encoding="utf-8")


def test_provider_latency_probe_reports_blocked_provider_step(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    audio_path = tmp_path / "probe.wav"
    audio_path.write_bytes(b"probe-audio")

    class Provider:
        name = "glip"

        def check_ready(self):
            return MeetingStatus(
                app_running=True,
                meeting_found=False,
                tab_info=None,
            )

    monkeypatch.setattr("saymo.providers.factory.get_provider", lambda name: Provider())

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "provider-latency",
            "--profile",
            "personal",
            "--text",
            "John, что по статусу?",
            "--audio",
            str(audio_path),
            "--output-dir",
            str(tmp_path / "history"),
        ],
    )

    assert result.exit_code == 0
    assert "provider latency: profile=personal provider=glip" in result.output
    assert "probe: blocked" in result.output
    assert "blocked: provider_tab:" in result.output
    assert "history json:" in result.output

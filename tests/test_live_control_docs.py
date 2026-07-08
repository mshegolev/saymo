"""Docs checks for live-control operator guidance."""

from pathlib import Path


def test_live_control_guide_explains_terminal_focus_and_accessibility():
    text = Path("docs/LIVE-CONTROL-HANDBRAKE.md").read_text(encoding="utf-8")

    assert "terminal window to be focused" in text
    assert "running Saymo process" in text
    assert "Accessibility permission" in text
    assert "saymo live-control -p personal" in text
    assert "Hard Disable" in text


def test_live_control_guide_explains_launchagent_probe_logs_and_guardrails():
    text = Path("docs/LIVE-CONTROL-HANDBRAKE.md").read_text(encoding="utf-8")

    assert "call-control-agent install" in text
    assert "call-control-agent start" in text
    assert "call-control-agent status" in text
    assert "call-control probe" in text
    assert "LaunchAgents" in text
    assert "~/.saymo/live_control/<profile>/logs/" in text
    assert "GUI session" in text
    assert "control-plane only" in text
    assert "cron" not in text.lower()


def test_call_control_sources_keep_non_destructive_static_guard():
    forbidden = (
        "activate_meeting(",
        "toggle_mute(",
        "switch_mic(",
        "get_previous_app(",
        "activate_app(",
        "leave_meeting(",
        "play_audio_bytes",
        "play_bytes_to_devices",
        "sd.rec",
        "sounddevice.rec",
        "_write_audio_settings_to_user_config",
        "set_input_volume",
        "bump_input_volume",
        "killall",
        "pkill",
    )
    paths = (
        Path("saymo/analysis/control_daemon.py"),
        Path("saymo/analysis/launch_agent.py"),
        Path("saymo/analysis/launch_readiness.py"),
        Path("saymo/commands/call_control.py"),
        Path("saymo/commands/call_ready.py"),
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    for token in forbidden:
        assert token not in combined

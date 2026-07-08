"""CLI tests for call-control daemon commands."""

from __future__ import annotations

import json
import textwrap

from click.testing import CliRunner

from saymo.commands import main


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            safety:
              hotkey_speak: ""
              hotkey_stop: ""
              hotkey_toggle: ""
              hotkey_takeover: ""
              hotkey_approved_speak: ""
              hotkey_skip: ""
              hotkey_capture_marker: ""
              hotkey_status: ""
              hotkey_hard_disable: ""
            meetings:
              daily:
                description: "Daily"
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


def test_call_control_daemon_once_writes_heartbeat(tmp_path):
    config_path = _write_config(tmp_path)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-control-daemon",
            "-p",
            "daily",
            "--base-dir",
            str(tmp_path),
            "--once",
        ],
    )

    assert result.exit_code == 0
    heartbeat_path = tmp_path / "daily" / "daemon-heartbeat.json"
    payload = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    assert payload["profile"] == "daily"
    assert payload["hotkey_registration_status"] == "no_bindings"
    assert payload["command_log_offset"] == 0
    assert payload["daemon_version"]

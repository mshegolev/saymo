"""CLI tests for call-control daemon commands."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone

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


def test_call_control_action_queues_normalized_existing_command(tmp_path):
    # Contract: `saymo call-control action` queues existing live-control actions.
    result = CliRunner().invoke(
        main,
        [
            "call-control",
            "action",
            "-p",
            "daily",
            "--action",
            "hard-disable",
            "--probe-id",
            "probe-123",
            "--base-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "queued: hard_disable" in result.output
    assert "commands:" in result.output
    command_log = tmp_path / "daily" / "commands.jsonl"
    payload = json.loads(command_log.read_text(encoding="utf-8").strip())
    assert payload["action"] == "hard_disable"
    assert payload["source"] == "daemon_cli"
    assert payload["command_id"]
    assert payload["payload"] == {"probe_id": "probe-123"}


def _invoke_agent(tmp_path, monkeypatch, args):
    from saymo.analysis import launch_agent

    config_path = _write_config(tmp_path)
    home = tmp_path / "home"
    recorded: list[list[str]] = []

    def fake_run(argv, *, check=False):
        recorded.append(list(argv))
        return launch_agent.CommandResult(
            argv=list(argv),
            returncode=0,
            stdout="state = running\npid = 123\n",
            stderr="",
        )

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(launch_agent.shutil, "which", lambda name: "/tmp/fake-saymo")
    monkeypatch.setattr(launch_agent.os, "getuid", lambda: 501)
    monkeypatch.setattr(launch_agent, "run_command", fake_run)

    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "call-control-agent", *args],
    )
    return result, recorded, home


def test_call_control_agent_install_writes_plist_and_lints(tmp_path, monkeypatch):
    result, recorded, home = _invoke_agent(
        tmp_path,
        monkeypatch,
        ["install", "-p", "daily"],
    )

    plist_path = (
        home
        / "Library"
        / "LaunchAgents"
        / "com.saymo.call-control.daily.plist"
    )
    stdout_path = (
        home
        / ".saymo"
        / "live_control"
        / "daily"
        / "logs"
        / "com.saymo.call-control.daily.out.log"
    )
    stderr_path = stdout_path.with_name("com.saymo.call-control.daily.err.log")

    assert result.exit_code == 0, result.output
    assert plist_path.exists()
    assert recorded == [["/usr/bin/plutil", "-lint", str(plist_path)]]
    assert "installed: com.saymo.call-control.daily" in result.output
    assert f"plist: {plist_path}" in result.output
    assert f"stdout: {stdout_path}" in result.output
    assert f"stderr: {stderr_path}" in result.output


def test_call_control_agent_lifecycle_commands_use_launchctl(tmp_path, monkeypatch):
    expected = {
        "start": [
            "/bin/launchctl",
            "bootstrap",
            "gui/501",
            str(
                tmp_path
                / "home"
                / "Library"
                / "LaunchAgents"
                / "com.saymo.call-control.daily.plist"
            ),
        ],
        "stop": [
            "/bin/launchctl",
            "bootout",
            "gui/501/com.saymo.call-control.daily",
        ],
        "restart": [
            "/bin/launchctl",
            "kickstart",
            "-k",
            "gui/501/com.saymo.call-control.daily",
        ],
        "uninstall": [
            "/bin/launchctl",
            "bootout",
            "gui/501/com.saymo.call-control.daily",
        ],
    }

    for command, argv in expected.items():
        result, recorded, _ = _invoke_agent(
            tmp_path,
            monkeypatch,
            [command, "-p", "daily"],
        )

        assert result.exit_code == 0, result.output
        assert recorded == [argv]
        assert f"{command}: com.saymo.call-control.daily" in result.output


def test_call_control_agent_status_is_read_only(tmp_path, monkeypatch):
    install_result, _, home = _invoke_agent(
        tmp_path,
        monkeypatch,
        ["install", "-p", "daily"],
    )
    assert install_result.exit_code == 0, install_result.output

    result, recorded, _ = _invoke_agent(
        tmp_path,
        monkeypatch,
        ["status", "-p", "daily"],
    )

    plist_path = (
        home
        / "Library"
        / "LaunchAgents"
        / "com.saymo.call-control.daily.plist"
    )
    assert result.exit_code == 0, result.output
    assert recorded == [
        ["/usr/bin/plutil", "-lint", str(plist_path)],
        [
            "/bin/launchctl",
            "print",
            "gui/501/com.saymo.call-control.daily",
        ],
    ]
    assert not any(
        token in argv for argv in recorded for token in {"bootstrap", "bootout", "kickstart"}
    )
    assert "status: com.saymo.call-control.daily" in result.output
    assert "classification: stale_heartbeat" in result.output
    assert "loaded: yes" in result.output
    assert "heartbeat fresh: no" in result.output
    assert "running: no" in result.output


def test_call_control_agent_status_json_is_read_only(tmp_path, monkeypatch):
    from saymo.analysis import launch_agent
    from saymo.analysis.control_daemon import ControlDaemonHeartbeat, write_daemon_heartbeat
    from saymo.commands import call_control

    config_path = _write_config(tmp_path)
    home = tmp_path / "home"
    recorded: list[list[str]] = []

    def forbidden_mutation(*args, **kwargs):
        raise AssertionError("status must not call lifecycle mutators")

    def fake_run(argv, *, check=False):
        recorded.append(list(argv))
        return launch_agent.CommandResult(
            argv=list(argv),
            returncode=0,
            stdout="state = running\nlast exit status = 0\n",
            stderr="",
        )

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(launch_agent.shutil, "which", lambda name: "/tmp/fake-saymo")
    monkeypatch.setattr(launch_agent.os, "getuid", lambda: 501)
    monkeypatch.setattr(launch_agent, "run_command", fake_run)
    monkeypatch.setattr(call_control, "install_launch_agent", forbidden_mutation)
    monkeypatch.setattr(call_control, "uninstall_launch_agent", forbidden_mutation)
    monkeypatch.setattr(call_control, "start_launch_agent", forbidden_mutation)
    monkeypatch.setattr(call_control, "stop_launch_agent", forbidden_mutation)
    monkeypatch.setattr(call_control, "restart_launch_agent", forbidden_mutation)

    spec = launch_agent.build_launch_agent_spec(
        "daily",
        saymo_executable="/tmp/fake-saymo",
        home=home,
        uid=501,
    )
    spec.plist_path.parent.mkdir(parents=True, exist_ok=True)
    spec.plist_path.write_bytes(launch_agent.expected_plist_bytes(spec))
    write_daemon_heartbeat(
        ControlDaemonHeartbeat(
            profile="daily",
            pid=1234,
            label=spec.label,
            started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            heartbeat_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            hotkeys_active=True,
            hotkey_registration_status="ok",
            hotkey_registration_detail="registered global hotkeys",
            bindings_count=3,
            command_log_offset=0,
            daemon_version="test",
        )
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-control-agent",
            "status",
            "-p",
            "daily",
            "--json",
        ],
    )

    payload = json.loads(result.output)
    assert result.exit_code == 0, result.output
    assert payload["profile"] == "daily"
    assert payload["label"] == "com.saymo.call-control.daily"
    assert payload["classification"] == "running"
    assert payload["action"] == "none"
    assert payload["rerun"] == "saymo call-control-agent status -p daily"
    assert payload["plist_path"] == str(spec.plist_path)
    assert payload["stdout_log_path"] == str(spec.stdout_log_path)
    assert payload["stderr_log_path"] == str(spec.stderr_log_path)
    assert payload["metadata"]["heartbeat"]["pid"] == 1234
    assert recorded == [
        ["/usr/bin/plutil", "-lint", str(spec.plist_path)],
        [
            "/bin/launchctl",
            "print",
            "gui/501/com.saymo.call-control.daily",
        ],
    ]
    assert not any(
        token in argv
        for argv in recorded
        for token in {"bootstrap", "bootout", "kickstart"}
    )
    assert not (home / ".saymo" / "live_control" / "daily" / "commands.jsonl").exists()

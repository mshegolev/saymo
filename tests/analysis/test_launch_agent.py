"""Tests for per-profile LaunchAgent rendering and launchctl argv helpers."""

from __future__ import annotations

import plistlib
from datetime import datetime, timedelta, timezone

from saymo.analysis.control_daemon import ControlDaemonHeartbeat, write_daemon_heartbeat
from saymo.analysis.launch_agent import (
    CommandResult,
    bootstrap_argv,
    bootout_argv,
    build_launch_agent_spec,
    collect_call_control_agent_status,
    expected_plist_bytes,
    kickstart_argv,
    plutil_lint_argv,
    print_argv,
    render_launch_agent_plist,
)


def test_render_launch_agent_plist_round_trips_with_plistlib(tmp_path):
    spec = build_launch_agent_spec(
        "daily",
        saymo_executable="/tmp/fake-saymo",
        home=tmp_path,
        uid=501,
        heartbeat_interval_seconds=2.0,
    )

    payload = render_launch_agent_plist(spec)
    loaded = plistlib.loads(expected_plist_bytes(spec))

    assert loaded == payload
    assert payload["Label"] == "com.saymo.call-control.daily"
    assert payload["ProgramArguments"] == [
        "/tmp/fake-saymo",
        "call-control-daemon",
        "--profile",
        "daily",
        "--heartbeat-interval",
        "2.0",
    ]
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] == {"SuccessfulExit": False}
    assert payload["WorkingDirectory"] == spec.working_directory
    assert payload["EnvironmentVariables"] == {
        "HOME": str(tmp_path),
        "PATH": spec.path,
        "PYTHONUNBUFFERED": "1",
        "NO_PROXY": "localhost,127.0.0.1",
    }
    assert payload["StandardOutPath"] == str(spec.stdout_log_path)
    assert payload["StandardErrorPath"] == str(spec.stderr_log_path)
    assert payload["ThrottleInterval"] == 10


def test_launch_agent_paths_and_label_are_profile_safe(tmp_path):
    spec = build_launch_agent_spec(
        "Daily/Profile?!",
        saymo_executable="/tmp/fake-saymo",
        home=tmp_path,
        uid=501,
    )

    assert spec.label == "com.saymo.call-control.daily-profile"
    assert "mshegolev" not in spec.label
    assert spec.plist_path == (
        tmp_path
        / "Library"
        / "LaunchAgents"
        / "com.saymo.call-control.daily-profile.plist"
    )
    assert spec.stdout_log_path == (
        tmp_path
        / ".saymo"
        / "live_control"
        / "daily-profile"
        / "logs"
        / "com.saymo.call-control.daily-profile.out.log"
    )
    assert spec.stderr_log_path == (
        tmp_path
        / ".saymo"
        / "live_control"
        / "daily-profile"
        / "logs"
        / "com.saymo.call-control.daily-profile.err.log"
    )


def test_launchctl_argv_builders_use_gui_domain(tmp_path):
    spec = build_launch_agent_spec(
        "daily",
        saymo_executable="/tmp/fake-saymo",
        home=tmp_path,
        uid=501,
    )

    assert bootstrap_argv(spec) == [
        "/bin/launchctl",
        "bootstrap",
        "gui/501",
        str(spec.plist_path),
    ]
    assert bootout_argv(spec) == [
        "/bin/launchctl",
        "bootout",
        "gui/501/com.saymo.call-control.daily",
    ]
    assert kickstart_argv(spec) == [
        "/bin/launchctl",
        "kickstart",
        "gui/501/com.saymo.call-control.daily",
    ]
    assert kickstart_argv(spec, restart=True) == [
        "/bin/launchctl",
        "kickstart",
        "-k",
        "gui/501/com.saymo.call-control.daily",
    ]
    assert print_argv(spec) == [
        "/bin/launchctl",
        "print",
        "gui/501/com.saymo.call-control.daily",
    ]
    assert plutil_lint_argv(spec) == [
        "/usr/bin/plutil",
        "-lint",
        str(spec.plist_path),
    ]


def test_status_classifies_missing_install_and_unloaded_agent(tmp_path):
    spec = _status_spec(tmp_path)

    missing_status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=_status_now(),
        runner=_runner(
            CommandResult(
                argv=print_argv(spec),
                returncode=113,
                stderr="Could not find service",
            )
        ),
    )

    assert missing_status.classification == "not_installed"
    assert missing_status.installed is False
    assert missing_status.plist_current is False
    assert missing_status.loaded is False
    assert missing_status.heartbeat_fresh is False
    assert missing_status.running is False
    assert "install" in missing_status.action
    assert missing_status.rerun == "saymo call-control-agent status -p daily"

    _install_expected_plist(spec)
    unloaded_status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=_status_now(),
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(
                argv=print_argv(spec),
                returncode=113,
                stderr="Could not find service",
            ),
        ),
    )

    assert unloaded_status.classification == "installed_not_loaded"
    assert unloaded_status.installed is True
    assert unloaded_status.plist_current is True
    assert unloaded_status.loaded is False
    assert unloaded_status.running is False
    assert "start" in unloaded_status.action


def test_status_classifies_running_from_fresh_heartbeat(tmp_path):
    spec = _status_spec(tmp_path)
    now = _status_now()
    _install_expected_plist(spec)
    write_daemon_heartbeat(_heartbeat(spec, now), base_dir=tmp_path / "live")

    status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now + timedelta(seconds=1),
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(
                argv=print_argv(spec),
                returncode=0,
                stdout="state = running\nno pid is parsed from this diagnostic\n",
            ),
        ),
    )

    assert status.classification == "running"
    assert status.loaded is True
    assert status.heartbeat_fresh is True
    assert status.running is True
    assert status.hotkeys_active is True
    assert status.hotkey_registration_status == "ok"
    assert status.action == "none"
    assert status.metadata["heartbeat"]["pid"] == 1234


def test_status_classifies_stale_heartbeat_and_plist_drift(tmp_path):
    spec = _status_spec(tmp_path)
    now = _status_now()
    _install_expected_plist(spec)
    write_daemon_heartbeat(
        _heartbeat(spec, now - timedelta(seconds=30)),
        base_dir=tmp_path / "live",
    )

    stale_status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert stale_status.classification == "stale_heartbeat"
    assert stale_status.heartbeat_fresh is False
    assert stale_status.running is False
    assert "restart" in stale_status.action

    spec.plist_path.write_bytes(b"outdated plist")
    write_daemon_heartbeat(_heartbeat(spec, now), base_dir=tmp_path / "live")
    drift_status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert drift_status.classification == "plist_drift"
    assert drift_status.plist_current is False
    assert drift_status.metadata["expected_plist_hash"]
    assert drift_status.metadata["installed_plist_hash"]
    assert "install" in drift_status.action


def test_status_classifies_crash_and_hotkey_permission(tmp_path):
    spec = _status_spec(tmp_path)
    now = _status_now()
    _install_expected_plist(spec)

    crash_status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(
                argv=print_argv(spec),
                returncode=0,
                stdout="last exit status = 78\nservice throttled by launchd\n",
            ),
        ),
    )

    assert crash_status.classification == "crash_loop"
    assert crash_status.loaded is True
    assert crash_status.running is False
    assert crash_status.metadata["last_exit_status"] == "78"
    assert crash_status.metadata["throttle_hint"]
    assert "logs" in crash_status.action

    write_daemon_heartbeat(
        _heartbeat(
            spec,
            now,
            hotkeys_active=False,
            hotkey_registration_status="blocked",
            hotkey_registration_detail="Accessibility permission denied",
        ),
        base_dir=tmp_path / "live",
    )
    blocked_status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert blocked_status.classification == "hotkey_permission_blocked"
    assert blocked_status.heartbeat_fresh is True
    assert blocked_status.running is True
    assert blocked_status.hotkeys_active is False
    assert blocked_status.hotkey_registration_status == "blocked"
    assert "Accessibility" in blocked_status.detail


def test_status_classifies_status_unavailable_when_diagnostics_error(tmp_path):
    spec = _status_spec(tmp_path)
    _install_expected_plist(spec)

    def failing_runner(argv, *, check=False):
        raise OSError("launchctl unavailable")

    status = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=_status_now(),
        runner=failing_runner,
    )

    assert status.classification == "status_unavailable"
    assert status.loaded is False
    assert status.running is False
    assert status.metadata["error_type"] == "OSError"
    assert "launchctl unavailable" in status.detail


def test_status_actions_are_exact_operator_commands(tmp_path):
    spec = _status_spec(tmp_path)
    now = _status_now()

    missing = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(
                argv=print_argv(spec),
                returncode=113,
                stderr="Could not find service",
            )
        ),
    )

    assert missing.classification == "not_installed"
    assert missing.action == "saymo call-control-agent install -p daily"
    assert missing.rerun == "saymo call-control-agent status -p daily"

    _install_expected_plist(spec)
    installed_not_loaded = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(
                argv=print_argv(spec),
                returncode=113,
                stderr="Could not find service",
            ),
        ),
    )

    assert installed_not_loaded.classification == "installed_not_loaded"
    assert installed_not_loaded.action == "saymo call-control-agent start -p daily"
    assert installed_not_loaded.rerun == "saymo call-control-agent status -p daily"

    spec.plist_path.write_bytes(b"outdated plist")
    drift = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert drift.classification == "plist_drift"
    assert drift.action == "saymo call-control-agent install -p daily"
    assert drift.rerun == "saymo call-control-agent status -p daily"

    _install_expected_plist(spec)
    write_daemon_heartbeat(
        _heartbeat(spec, now - timedelta(seconds=30)),
        base_dir=tmp_path / "live",
    )
    stale = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert stale.classification == "stale_heartbeat"
    assert stale.action == "saymo call-control-agent restart -p daily"
    assert stale.rerun == "saymo call-control-agent status -p daily"

    crash = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(
                argv=print_argv(spec),
                returncode=0,
                stdout="last exit status = 78\nservice throttled by launchd\n",
            ),
        ),
    )

    assert crash.classification == "crash_loop"
    assert crash.action == (
        "inspect logs and restart: "
        f"{spec.stdout_log_path} {spec.stderr_log_path}; "
        "saymo call-control-agent restart -p daily"
    )
    assert crash.rerun == "saymo call-control-agent status -p daily"

    write_daemon_heartbeat(
        _heartbeat(
            spec,
            now,
            hotkeys_active=False,
            hotkey_registration_status="blocked",
            hotkey_registration_detail="Accessibility permission denied",
        ),
        base_dir=tmp_path / "live",
    )
    blocked = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert blocked.classification == "hotkey_permission_blocked"
    assert blocked.action == (
        "grant Accessibility permission, then "
        "saymo call-control-agent restart -p daily"
    )
    assert blocked.rerun == "saymo call-control-agent status -p daily"

    write_daemon_heartbeat(_heartbeat(spec, now), base_dir=tmp_path / "live")
    running = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now + timedelta(seconds=1),
        runner=_runner(
            CommandResult(argv=plutil_lint_argv(spec), returncode=0),
            CommandResult(argv=print_argv(spec), returncode=0),
        ),
    )

    assert running.classification == "running"
    assert running.action == "none"
    assert running.rerun == "saymo call-control-agent status -p daily"

    def failing_runner(argv, *, check=False):
        raise OSError("launchctl unavailable")

    unavailable = collect_call_control_agent_status(
        spec,
        base_dir=tmp_path / "live",
        now=now,
        runner=failing_runner,
    )

    assert unavailable.classification == "status_unavailable"
    assert unavailable.action == (
        "rerun status after diagnostics are available: "
        "saymo call-control-agent status -p daily"
    )
    assert unavailable.rerun == "saymo call-control-agent status -p daily"


def _status_spec(tmp_path):
    return build_launch_agent_spec(
        "daily",
        saymo_executable="/tmp/fake-saymo",
        home=tmp_path,
        uid=501,
    )


def _status_now() -> datetime:
    return datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)


def _install_expected_plist(spec) -> None:
    spec.plist_path.parent.mkdir(parents=True, exist_ok=True)
    spec.plist_path.write_bytes(expected_plist_bytes(spec))


def _heartbeat(
    spec,
    heartbeat_at: datetime,
    *,
    hotkeys_active: bool = True,
    hotkey_registration_status: str = "ok",
    hotkey_registration_detail: str = "registered global hotkeys",
) -> ControlDaemonHeartbeat:
    return ControlDaemonHeartbeat(
        profile=spec.profile,
        pid=1234,
        label=spec.label,
        started_at=_status_now().isoformat(timespec="seconds"),
        heartbeat_at=heartbeat_at.isoformat(timespec="seconds"),
        hotkeys_active=hotkeys_active,
        hotkey_registration_status=hotkey_registration_status,
        hotkey_registration_detail=hotkey_registration_detail,
        bindings_count=3,
        command_log_offset=42,
        daemon_version="test",
    )


def _runner(*results: CommandResult):
    remaining = list(results)

    def fake_runner(argv, *, check=False):
        if remaining:
            return remaining.pop(0)
        return CommandResult(argv=list(argv), returncode=0)

    return fake_runner

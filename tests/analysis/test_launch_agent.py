"""Tests for per-profile LaunchAgent rendering and launchctl argv helpers."""

from __future__ import annotations

import plistlib

from saymo.analysis.launch_agent import (
    bootstrap_argv,
    bootout_argv,
    build_launch_agent_spec,
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

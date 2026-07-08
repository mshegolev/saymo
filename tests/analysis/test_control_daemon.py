"""Tests for the foreground call-control daemon heartbeat and hotkeys."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from saymo.analysis.control_daemon import (
    ControlDaemonHeartbeat,
    daemon_heartbeat_path,
    heartbeat_is_fresh,
    load_daemon_heartbeat,
    queue_daemon_hotkey_command,
    run_handbrake_reachability_probe,
    run_control_daemon,
    write_daemon_heartbeat,
)
from saymo.analysis.live_control import (
    append_control_audit,
    audit_log_path,
    effective_hotkey_bindings,
    read_control_commands,
)
from saymo.config import SaymoConfig


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _heartbeat(now: datetime) -> ControlDaemonHeartbeat:
    return ControlDaemonHeartbeat(
        profile="daily",
        pid=1234,
        label="com.saymo.call-control.daily",
        started_at=_iso(now),
        heartbeat_at=_iso(now),
        hotkeys_active=True,
        hotkey_registration_status="ok",
        hotkey_registration_detail="registered global hotkeys",
        bindings_count=3,
        command_log_offset=0,
        daemon_version="test",
    )


def _config_with_only(*actions: str) -> SaymoConfig:
    config = SaymoConfig()
    fields_by_action = {
        "toggle_auto_answer": "hotkey_toggle",
        "speak": "hotkey_speak",
        "stop": "hotkey_stop",
        "takeover": "hotkey_takeover",
        "approved_speak": "hotkey_approved_speak",
        "skip_current": "hotkey_skip",
        "capture_marker": "hotkey_capture_marker",
        "status": "hotkey_status",
        "hard_disable": "hotkey_hard_disable",
    }
    hotkeys_by_action = {
        "toggle_auto_answer": "<cmd>+<shift>+m",
        "speak": "<cmd>+<shift>+s",
        "stop": "<cmd>+<shift>+x",
        "takeover": "<cmd>+<shift>+u",
        "approved_speak": "<cmd>+<shift>+a",
        "skip_current": "<cmd>+<shift>+k",
        "capture_marker": "<cmd>+<shift>+c",
        "status": "<cmd>+<shift>+i",
        "hard_disable": "<cmd>+<shift>+h",
    }
    for field in fields_by_action.values():
        setattr(config.safety, field, "")
    for action in actions:
        setattr(config.safety, fields_by_action[action], hotkeys_by_action[action])
    return config


class RecordingListener:
    instances: list["RecordingListener"] = []

    def __init__(self, bindings):
        self.bindings = bindings
        self.started = False
        self.stopped = False
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_heartbeat_round_trip_and_freshness(tmp_path):
    now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
    heartbeat = _heartbeat(now)

    path = write_daemon_heartbeat(heartbeat, base_dir=tmp_path)
    loaded = load_daemon_heartbeat("daily", base_dir=tmp_path)

    assert path == daemon_heartbeat_path("daily", base_dir=tmp_path)
    assert path.name == "daemon-heartbeat.json"
    assert loaded == heartbeat
    assert heartbeat_is_fresh(
        loaded,
        now=now + timedelta(seconds=1),
        max_age_seconds=5.0,
    )
    assert not heartbeat_is_fresh(
        loaded,
        now=now + timedelta(seconds=6),
        max_age_seconds=5.0,
    )
    assert not heartbeat_is_fresh(
        replace(heartbeat, heartbeat_at=_iso(now + timedelta(seconds=30))),
        now=now,
        max_age_seconds=5.0,
    )
    assert not heartbeat_is_fresh(
        replace(heartbeat, heartbeat_at="not-a-timestamp"),
        now=now,
        max_age_seconds=5.0,
    )
    assert not heartbeat_is_fresh(None, now=now, max_age_seconds=5.0)


def test_run_control_daemon_writes_fresh_heartbeat(tmp_path):
    RecordingListener.instances.clear()
    config = SaymoConfig()

    exit_code = run_control_daemon(
        config,
        profile="daily",
        label="com.saymo.call-control.daily",
        heartbeat_interval_seconds=0,
        base_dir=tmp_path,
        listener_factory=RecordingListener,
        stop_after_heartbeats=1,
    )

    loaded = load_daemon_heartbeat("daily", base_dir=tmp_path)
    assert exit_code == 0
    assert loaded is not None
    assert loaded.profile == "daily"
    assert loaded.pid == os.getpid()
    assert loaded.label == "com.saymo.call-control.daily"
    assert loaded.hotkeys_active is True
    assert loaded.hotkey_registration_status == "ok"
    assert loaded.bindings_count == len(effective_hotkey_bindings(config))
    assert loaded.command_log_offset == 0
    assert loaded.daemon_version
    assert heartbeat_is_fresh(loaded, max_age_seconds=5.0)
    assert RecordingListener.instances
    assert RecordingListener.instances[0].started is True
    assert RecordingListener.instances[0].stopped is True


def test_daemon_hotkeys_queue_existing_commands(tmp_path):
    config = _config_with_only("stop", "takeover", "status")

    class InvokingListener:
        def __init__(self, bindings):
            self.bindings = bindings

        def start(self):
            for handler in self.bindings.values():
                handler()

        def stop(self):
            pass

    run_control_daemon(
        config,
        profile="daily",
        heartbeat_interval_seconds=0,
        base_dir=tmp_path,
        listener_factory=InvokingListener,
        stop_after_heartbeats=1,
    )

    commands, _ = read_control_commands("daily", base_dir=tmp_path)
    assert [command.action for command in commands] == ["stop", "takeover", "status"]
    assert [command.source for command in commands] == [
        "daemon_hotkey",
        "daemon_hotkey",
        "daemon_hotkey",
    ]


def test_daemon_hotkey_source_and_payload_are_sanitized(tmp_path):
    queue_daemon_hotkey_command(
        "daily",
        "status",
        payload={
            "probe_id": "probe-123",
            "raw_transcript": "private meeting text",
            "secret": {"token": "not-for-audit"},
        },
        base_dir=tmp_path,
    )

    commands, _ = read_control_commands("daily", base_dir=tmp_path)

    assert len(commands) == 1
    assert commands[0].action == "status"
    assert commands[0].source == "daemon_hotkey"
    assert commands[0].payload == {"probe_id": "probe-123"}


def test_daemon_survives_hotkey_registration_failure(tmp_path):
    config = _config_with_only("stop")

    class FailingListener:
        def __init__(self, bindings):
            self.bindings = bindings

        def start(self):
            raise RuntimeError("Accessibility denied for test app")

        def stop(self):
            pass

    exit_code = run_control_daemon(
        config,
        profile="daily",
        heartbeat_interval_seconds=0,
        base_dir=tmp_path,
        listener_factory=FailingListener,
        stop_after_heartbeats=1,
    )

    loaded = load_daemon_heartbeat("daily", base_dir=tmp_path)
    assert exit_code == 0
    assert loaded is not None
    assert loaded.hotkeys_active is False
    assert loaded.hotkey_registration_status == "blocked"
    assert "RuntimeError" in loaded.hotkey_registration_detail
    assert "Accessibility denied" in loaded.hotkey_registration_detail
    assert len(loaded.hotkey_registration_detail) <= 200


def test_handbrake_reachability_probe_requires_full_command_and_audit_proof(
    tmp_path,
    monkeypatch,
):
    now = datetime(2026, 7, 8, 16, 30, tzinfo=timezone.utc)
    write_daemon_heartbeat(_heartbeat(now), base_dir=tmp_path)
    original_sleep = __import__("time").sleep
    sleep_count = {"value": 0}

    def fake_sleep(seconds):
        sleep_count["value"] += 1
        commands, offset = read_control_commands("daily", base_dir=tmp_path)
        assert commands
        command = commands[-1]
        write_daemon_heartbeat(
            replace(_heartbeat(now), command_log_offset=offset),
            base_dir=tmp_path,
        )
        append_control_audit(
            "daily",
            action="status",
            source="probe",
            previous_state=None,
            next_state=None,
            result="status_printed",
            command_id=command.command_id,
            probe_id=command.payload["probe_id"],
            payload=command.payload,
            base_dir=tmp_path,
        )
        original_sleep(0)

    monkeypatch.setattr("saymo.analysis.control_daemon.time.sleep", fake_sleep)

    probe = run_handbrake_reachability_probe(
        "daily",
        base_dir=tmp_path,
        timeout_seconds=1.0,
        poll_interval_seconds=0.01,
        now=now,
    )
    commands, _ = read_control_commands("daily", base_dir=tmp_path)

    assert probe.ok is True
    assert probe.heartbeat_fresh is True
    assert probe.hotkeys_active is True
    assert probe.command_written is True
    assert probe.command_consumed is True
    assert probe.audit_applied is True
    assert probe.detail == "reachable"
    assert commands[-1].action == "status"
    assert commands[-1].source == "probe"
    assert commands[-1].payload == {"probe_id": probe.probe_id}
    assert probe.probe_id and "/" not in probe.probe_id and " " not in probe.probe_id
    assert probe.command_log_path.endswith("commands.jsonl")
    assert probe.audit_log_path.endswith("audit.jsonl")
    assert probe.stdout_log_path.endswith(".out.log")
    assert probe.stderr_log_path.endswith(".err.log")
    audit_payload = audit_log_path("daily", base_dir=tmp_path).read_text(encoding="utf-8")
    assert probe.probe_id in audit_payload
    assert sleep_count["value"] >= 1


def test_handbrake_reachability_probe_reports_separate_failure_modes(
    tmp_path,
):
    now = datetime(2026, 7, 8, 16, 30, tzinfo=timezone.utc)

    write_daemon_heartbeat(_heartbeat(now - timedelta(seconds=30)), base_dir=tmp_path)
    stale = run_handbrake_reachability_probe(
        "daily",
        base_dir=tmp_path,
        timeout_seconds=0,
        poll_interval_seconds=0,
        now=now,
    )
    assert stale.ok is False
    assert stale.heartbeat_fresh is False
    assert stale.command_written is True
    assert stale.command_consumed is False
    assert stale.audit_applied is False
    assert stale.detail == "stale heartbeat"

    write_daemon_heartbeat(
        replace(
            _heartbeat(now),
            hotkeys_active=False,
            hotkey_registration_status="blocked",
            hotkey_registration_detail="Accessibility denied",
        ),
        base_dir=tmp_path,
    )
    blocked = run_handbrake_reachability_probe(
        "daily",
        base_dir=tmp_path,
        timeout_seconds=0,
        poll_interval_seconds=0,
        now=now,
    )
    assert blocked.ok is False
    assert blocked.heartbeat_fresh is True
    assert blocked.hotkeys_active is False
    assert blocked.detail == "hotkeys blocked"

    write_daemon_heartbeat(_heartbeat(now), base_dir=tmp_path)
    not_consumed = run_handbrake_reachability_probe(
        "daily",
        base_dir=tmp_path,
        timeout_seconds=0,
        poll_interval_seconds=0,
        now=now,
    )
    assert not_consumed.ok is False
    assert not_consumed.command_written is True
    assert not_consumed.command_consumed is False
    assert not_consumed.audit_applied is False
    assert not_consumed.detail == "command not consumed"

    commands, offset = read_control_commands("daily", base_dir=tmp_path)
    write_daemon_heartbeat(
        replace(_heartbeat(now), command_log_offset=offset),
        base_dir=tmp_path,
    )
    missing_audit = run_handbrake_reachability_probe(
        "daily",
        base_dir=tmp_path,
        timeout_seconds=0,
        poll_interval_seconds=0,
        now=now,
    )
    assert commands
    assert missing_audit.ok is False
    assert missing_audit.command_consumed is True
    assert missing_audit.audit_applied is False
    assert missing_audit.detail == "missing audit"

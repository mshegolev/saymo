"""Tests for remediation hints."""

from __future__ import annotations

import json

from saymo.analysis.regression_replay import RegressionMetrics
from saymo.analysis.remediation import (
    RemediationHint,
    hints_from_launch_readiness,
    hints_from_preflight_checks,
    hints_from_scorecard,
    render_remediation_hints,
)
from saymo.analysis.session_scorecard import build_scorecard_from_regression
from saymo.commands.tests import PreflightCheck


def test_render_remediation_hints_is_actionable_and_sanitized():
    rendered = render_remediation_hints(
        [
            RemediationHint(
                category="audio-device",
                title="Configure capture input",
                detail="Missing /Users/me/private.wav TOKEN-123",
                action="Set audio.capture_device to a valid input device",
                rerun="saymo auto-preflight -p personal",
            )
        ]
    )

    assert "remediation:" in rendered
    assert "[audio-device] Configure capture input" in rendered
    assert "Set audio.capture_device" in rendered
    assert "rerun: saymo auto-preflight -p personal" in rendered
    assert "/Users/me" not in rendered
    assert "TOKEN-123" not in rendered


def test_preflight_hints_classify_next_actions():
    hints = hints_from_preflight_checks(
        "personal",
        [
            PreflightCheck("capture input", False, "missing BlackHole 16ch"),
            PreflightCheck("provider tab", False, "glip tab not found"),
            PreflightCheck("response cache", False, "0/4 variants", blocking=False),
            PreflightCheck("hotkeys", False, "(none configured)", blocking=False),
        ],
    )

    categories = {hint.title: hint.category for hint in hints}

    assert categories["Fix capture input"] == "audio-device"
    assert categories["Open provider meeting tab"] == "retest"
    assert categories["Prepare response cache"] == "source-data"
    assert categories["Configure global hotkeys"] == "config"
    assert all("saymo auto-preflight -p personal" in hint.rerun for hint in hints)


def test_launch_provider_audio_hints_classify_permissions():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="provider_meeting_tab",
                label="provider meeting tab",
                severity="block",
                ok=False,
                detail="meeting_tab_not_found",
            ),
            LaunchReadinessCheck(
                key="provider_capabilities",
                label="provider capabilities",
                severity="warn",
                ok=False,
                detail="mic_switch_unsupported",
            ),
            LaunchReadinessCheck(
                key="provider_output_blackhole",
                label="provider output BlackHole",
                severity="block",
                ok=False,
                detail="device_not_found",
            ),
            LaunchReadinessCheck(
                key="capture_route_blackhole",
                label="capture route BlackHole",
                severity="block",
                ok=False,
                detail="device_not_found",
            ),
            LaunchReadinessCheck(
                key="chrome_automation_permission",
                label="Chrome automation permission",
                severity="block",
                ok=False,
                detail="chrome_automation_blocked",
            ),
            LaunchReadinessCheck(
                key="hotkey_accessibility_permission",
                label="hotkey Accessibility permission",
                severity="block",
                ok=False,
                detail="hotkey_accessibility_blocked",
            ),
            LaunchReadinessCheck(
                key="microphone_capture_permission",
                label="microphone capture permission",
                severity="block",
                ok=False,
                detail="microphone_capture_permission_blocked",
            ),
            LaunchReadinessCheck(
                key="audio_routing_permission",
                label="audio routing permission",
                severity="block",
                ok=False,
                detail="audio_routing_permission_blocked",
            ),
        ),
    )

    categories = {hint.title: hint.category for hint in hints_from_launch_readiness(report)}

    assert categories["provider meeting tab"] == "provider"
    assert categories["provider capabilities"] == "provider"
    assert categories["provider output BlackHole"] == "audio-device"
    assert categories["capture route BlackHole"] == "audio-device"
    assert categories["Chrome automation permission"] == "macos-permission"
    assert categories["hotkey Accessibility permission"] == "macos-permission"
    assert categories["microphone capture permission"] == "macos-permission"
    assert categories["audio routing permission"] == "macos-permission"


def test_launch_call_control_hints_include_agent_daemon_probe_and_accessibility_actions():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="call_control_agent",
                label="call-control agent",
                severity="block",
                ok=False,
                detail="LaunchAgent plist is not installed.",
                action="saymo call-control-agent install -p standup",
                rerun="saymo call-control-agent status -p standup",
                metadata={"category": "call-control"},
            ),
            LaunchReadinessCheck(
                key="call_control_daemon",
                label="call-control daemon",
                severity="block",
                ok=False,
                detail="LaunchAgent is loaded but daemon heartbeat is stale.",
                action="saymo call-control-agent restart -p standup",
                rerun="saymo call-control probe -p standup",
                metadata={"category": "call-control"},
            ),
            LaunchReadinessCheck(
                key="call_control_hotkeys",
                label="call-control hotkeys",
                severity="block",
                ok=False,
                detail="Daemon heartbeat reports hotkey registration blocked.",
                action="grant Accessibility permission, then saymo call-control-agent restart -p standup",
                rerun="saymo call-control-agent status -p standup",
                metadata={"category": "macos-permission"},
            ),
        ),
    )

    hints = hints_from_launch_readiness(report)
    payload = json.dumps([hint.__dict__ for hint in hints])
    categories = {hint.title: hint.category for hint in hints}

    assert categories["call-control agent"] == "call-control"
    assert categories["call-control daemon"] == "call-control"
    assert categories["call-control hotkeys"] == "macos-permission"
    assert "saymo call-control-agent install -p standup" in payload
    assert "saymo call-control-agent restart -p standup" in payload
    assert "saymo call-control probe -p standup" in payload
    assert "Accessibility" in payload


def test_scorecard_hints_cover_review_and_safety_issues():
    metrics = RegressionMetrics(
        profile="personal",
        session_id="daily",
        total=2,
        false_handoffs=1,
        missed_handoffs=0,
        question_noise=0,
        known_speakers=1,
        unknown_speakers=1,
        labeled_decisions=1,
        unlabeled_decisions=1,
        readiness="not_ready",
        readiness_missing=("need one rejected label",),
        speaker_counts={"other": 1, "unknown": 1},
        category_counts={"asked_to_speak": 1, "mentioned_me": 1},
        decision_counts={"accepted": 1, "unlabeled": 1},
        samples=(),
    )
    scorecard = build_scorecard_from_regression(metrics)

    hints = hints_from_scorecard(scorecard)
    payload = json.dumps([hint.__dict__ for hint in hints])

    assert "Review handoff labels" in payload
    assert "Improve speaker labels" in payload
    assert "saymo trigger-samples queue -p personal --session daily" in payload
    assert "saymo session-scorecard -p personal --session daily" in payload

"""Tests for remediation hints."""

from __future__ import annotations

import json

from saymo.analysis.regression_replay import RegressionMetrics
from saymo.analysis.remediation import (
    RemediationHint,
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


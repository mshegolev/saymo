"""Tests for local safety soak gates."""

from __future__ import annotations

import json

from saymo.analysis.rehearsal import (
    RehearsalArtifact,
    RehearsalCheck,
    RehearsalDecision,
    rehearsal_artifact_to_json,
)
from saymo.analysis.safety_soak import (
    build_safety_soak_report,
    render_safety_soak_markdown,
    safety_soak_to_json,
)
from saymo.analysis.session_scorecard import (
    TriggerScorecardMetrics,
    PlaybackScorecardMetrics,
    SafetyScorecardMetrics,
    SessionScorecard,
    build_scorecard_from_rehearsal,
)


def _scorecard(
    *,
    source_id: str = "scorecard.json",
    would_speak: bool | None = False,
    auto_answer_enabled: bool | None = True,
    manual_takeover: bool | None = False,
    hard_disabled: bool | None = False,
    false_handoffs: int | None = 0,
    missed_handoffs: int | None = 0,
    question_noise: int | None = 0,
    unknown_speakers: int | None = 0,
    unsafe_automatic_playback: int = 0,
) -> SessionScorecard:
    return SessionScorecard(
        profile="personal",
        source_type="session",
        source_id=source_id,
        status="pass",
        trigger_metrics=TriggerScorecardMetrics(
            total_decisions=1,
            triggered_decisions=1 if would_speak else 0,
            question_noise=question_noise,
            false_handoffs=false_handoffs,
            missed_handoffs=missed_handoffs,
            speaker_coverage={"known": 1, "unknown": unknown_speakers, "total": 1},
            would_speak=would_speak,
        ),
        playback_metrics=PlaybackScorecardMetrics(
            playback_gate_status="pass",
            approved_speak_attempts=1 if would_speak else 0,
            blocked_automatic_playback=0,
            unsafe_automatic_playback=unsafe_automatic_playback,
            latency_ms={"decision": 120.0, "playback_start": 480.0},
        ),
        safety_metrics=SafetyScorecardMetrics(
            auto_answer_enabled=auto_answer_enabled,
            manual_takeover=manual_takeover,
            hard_disabled=hard_disabled,
        ),
    )


def _write_rehearsal(tmp_path, *, would_speak: bool = True, auto_answer_enabled: bool = True):
    artifact = RehearsalArtifact(
        profile="personal",
        provider="glip",
        transcript="Alice, share the confidential account update",
        dry_run=True,
        status="pass",
        checks=(
            RehearsalCheck("playback gate", "pass", "dry-run would speak"),
            RehearsalCheck("latency", "pass", "decision=120ms playback_start=480ms"),
        ),
        decision=RehearsalDecision(
            triggered=True,
            addressing="addressed_to_me",
            reason="direct question with trigger",
            auto_action="answer_now",
            would_speak=would_speak,
            question=True,
        ),
        live_control_state={"auto_answer_enabled": auto_answer_enabled},
        hotkey_status="ok",
        created_at="2026-05-22T10:00:00+00:00",
    )
    path = tmp_path / "rehearsal.json"
    path.write_text(
        json.dumps(rehearsal_artifact_to_json(artifact), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_safety_soak_passes_safe_rehearsal_without_leaking_transcript(tmp_path):
    scorecard = build_scorecard_from_rehearsal(_write_rehearsal(tmp_path))

    report = build_safety_soak_report(profile="personal", scorecards=(scorecard,))
    payload = safety_soak_to_json(report)
    rendered = render_safety_soak_markdown(report)
    combined = json.dumps(payload, ensure_ascii=False) + rendered

    assert report.status == "pass"
    assert payload["totals"]["items"] == 1
    assert payload["totals"]["would_speak"] == 1
    assert payload["violations"] == []
    assert "Alice, share" not in combined
    assert "confidential account update" not in combined


def test_safety_soak_fails_when_speech_would_bypass_handbrake():
    report = build_safety_soak_report(
        profile="personal",
        scorecards=(
            _scorecard(
                source_id="manual-takeover.json",
                would_speak=True,
                auto_answer_enabled=False,
                manual_takeover=True,
                hard_disabled=True,
            ),
        ),
    )
    rules = {violation.rule for violation in report.violations}

    assert report.status == "fail"
    assert rules == {"auto_answer_off", "manual_takeover_active", "hard_disabled"}
    assert all("manual-takeover.json" == violation.source_id for violation in report.violations)


def test_safety_soak_fails_real_session_unsafe_playback_without_would_speak():
    report = build_safety_soak_report(
        profile="personal",
        scorecards=(
            _scorecard(
                source_id="real-session-scorecard.json",
                would_speak=None,
                unsafe_automatic_playback=1,
            ),
        ),
    )

    assert report.status == "fail"
    assert [violation.rule for violation in report.violations] == [
        "unsafe_automatic_playback"
    ]


def test_safety_soak_fails_only_worsened_baseline_metrics():
    baseline = build_safety_soak_report(
        profile="personal",
        scorecards=(
            _scorecard(
                source_id="baseline.json",
                false_handoffs=0,
                missed_handoffs=1,
                question_noise=2,
                unknown_speakers=0,
            ),
        ),
    )
    current = build_safety_soak_report(
        profile="personal",
        scorecards=(
            _scorecard(
                source_id="current.json",
                false_handoffs=2,
                missed_handoffs=1,
                question_noise=0,
                unknown_speakers=1,
            ),
        ),
        baseline=baseline,
    )

    worsened = {metric.name: metric.delta for metric in current.drift if metric.worsened}
    improved = {metric.name: metric.delta for metric in current.drift if metric.delta < 0}

    assert current.status == "fail"
    assert worsened == {"false_handoffs": 2, "unknown_speakers": 1}
    assert improved == {"question_noise": -2}

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
    safety_soak_from_json,
    safety_soak_to_json,
)
from saymo.analysis.session_scorecard import (
    LaunchScorecardMetrics,
    TriggerScorecardMetrics,
    PlaybackScorecardMetrics,
    RealtimeScorecardMetrics,
    SafetyScorecardMetrics,
    SessionScorecard,
    build_scorecard_from_rehearsal,
    scorecard_from_json,
    scorecard_to_json,
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
    launch_metrics: LaunchScorecardMetrics | None = None,
    realtime_metrics: RealtimeScorecardMetrics | None = None,
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
        launch_metrics=launch_metrics or LaunchScorecardMetrics(),
        realtime_metrics=realtime_metrics or RealtimeScorecardMetrics(),
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


def test_safety_soak_fails_voice_readiness_blockers():
    scorecard = _scorecard(would_speak=True)
    scorecard = SessionScorecard(
        **{
            **scorecard.__dict__,
            "playback_metrics": PlaybackScorecardMetrics(
                playback_gate_status="blocked",
                playback_gate_detail="voice_profile_unapproved voice_metadata_stale engine_not_voice_clone",
                approved_speak_attempts=1,
                blocked_automatic_playback=0,
                unsafe_automatic_playback=0,
            ),
        }
    )

    report = build_safety_soak_report(profile="personal", scorecards=(scorecard,))
    rules = {violation.rule for violation in report.violations}

    assert report.status == "fail"
    assert "voice_profile_unapproved" in rules
    assert "voice_metadata_stale" in rules
    assert "engine_not_voice_clone" in rules


def test_safety_soak_fails_v19_launch_daemon_cache_provider_and_runtime_blockers():
    scorecard = _scorecard(
        source_id="v19-unsafe-scorecard.json",
        would_speak=False,
        launch_metrics=LaunchScorecardMetrics(
            status="loaded",
            ready=False,
            block_count=3,
            warn_count=1,
            failed_labels=(
                "response cache coverage",
                "call-control daemon",
                "provider meeting tab",
            ),
            blocker_categories={"source-data": 1, "call-control": 1, "provider": 1},
            cache_ready=1,
            cache_total=3,
            cache_missing=2,
            provider_ready=False,
            daemon_ready=False,
            daemon_running=False,
            daemon_heartbeat_fresh=False,
        ),
        realtime_metrics=RealtimeScorecardMetrics(
            status="loaded",
            total_events=8,
            cache_hits=1,
            cache_misses=1,
            fallback_blocks=1,
            provider_blocks=1,
            handbrake_blocks=1,
            malformed_rows=1,
            label_counts={
                "cache-miss-blocked": 1,
                "cache-disabled-blocked": 1,
                "voice-metadata-blocked": 1,
            },
        ),
    )

    report = build_safety_soak_report(profile="personal", scorecards=(scorecard,))
    payload = safety_soak_to_json(report)
    rendered = render_safety_soak_markdown(report)
    rules = {violation.rule for violation in report.violations}

    assert report.status == "fail"
    assert rules == {
        "launch_not_ready",
        "stale_or_missing_response_cache",
        "call_control_daemon_not_ready",
        "provider_blocked",
        "fallback_blocked",
        "handbrake_blocked",
    }
    assert payload["totals"]["launch_not_ready"] == 1
    assert payload["totals"]["launch_blocks"] == 3
    assert payload["totals"]["launch_warnings"] == 1
    assert payload["totals"]["cache_hits"] == 1
    assert payload["totals"]["cache_misses"] == 1
    assert payload["totals"]["cache_missing"] == 2
    assert payload["totals"]["provider_blocks"] == 2
    assert payload["totals"]["fallback_blocks"] == 1
    assert payload["totals"]["handbrake_blocks"] == 1
    assert payload["totals"]["realtime_malformed_rows"] == 1
    assert payload["totals"]["daemon_not_ready"] == 1
    assert "## v1.9 Evidence Totals" in rendered
    assert "launch not ready: 1" in rendered
    assert "provider blocks: 2" in rendered


def test_safety_soak_passes_safe_v19_metrics_and_keeps_old_baseline_neutral():
    safe_scorecard = _scorecard(
        source_id="v19-safe-scorecard.json",
        launch_metrics=LaunchScorecardMetrics(
            status="loaded",
            ready=True,
            block_count=0,
            warn_count=1,
            cache_ready=3,
            cache_total=3,
            cache_missing=0,
            provider_ready=True,
            daemon_ready=True,
            daemon_running=True,
            daemon_heartbeat_fresh=True,
        ),
        realtime_metrics=RealtimeScorecardMetrics(
            status="loaded",
            total_events=3,
            cache_hits=2,
            cache_misses=0,
            fallback_blocks=0,
            provider_blocks=0,
            handbrake_blocks=0,
            malformed_rows=0,
        ),
    )
    old_scorecard = scorecard_from_json(scorecard_to_json(_scorecard(source_id="old.json")))
    old_baseline = safety_soak_from_json(
        {
            "profile": "personal",
            "status": "pass",
            "totals": {
                "items": 1,
                "false_handoffs": 0,
                "missed_handoffs": 0,
                "question_noise": 0,
                "unknown_speakers": 0,
                "max_latency_ms": 480,
            },
            "sources": [],
            "violations": [],
            "drift": [],
            "warnings": [],
        }
    )

    report = build_safety_soak_report(
        profile="personal",
        scorecards=(safe_scorecard, old_scorecard),
        baseline=old_baseline,
    )
    payload = safety_soak_to_json(report)
    rendered = render_safety_soak_markdown(report)

    assert report.status == "pass"
    assert report.violations == ()
    assert not any(metric.worsened for metric in report.drift)
    assert payload["totals"]["launch_not_ready"] == 0
    assert payload["totals"]["daemon_not_ready"] == 0
    assert payload["totals"]["cache_hits"] == 2
    assert payload["totals"]["cache_missing"] == 0
    assert "## v1.9 Evidence Totals" in rendered
    assert "cache hits: 2" in rendered


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

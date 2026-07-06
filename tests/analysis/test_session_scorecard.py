"""Tests for sanitized session reliability scorecards."""

from __future__ import annotations

import json

from saymo.analysis.regression_replay import RegressionMetrics, RegressionSample
from saymo.analysis.rehearsal import (
    RehearsalArtifact,
    RehearsalCheck,
    RehearsalDecision,
    rehearsal_artifact_to_json,
)
from saymo.analysis.session_scorecard import (
    build_scorecard_from_regression,
    build_scorecard_from_rehearsal,
    render_scorecard_markdown,
    scorecard_to_json,
)


def _write_rehearsal(tmp_path, *, would_speak: bool = False):
    artifact = RehearsalArtifact(
        profile="personal",
        provider="glip",
        transcript="Alice, please share the launch secret TOKEN-123",
        dry_run=True,
        status="warn",
        checks=(
            RehearsalCheck("preflight: capture input", "pass", "BlackHole 16ch"),
            RehearsalCheck("playback gate", "pass", "would block: confirmation required"),
            RehearsalCheck("latency", "warn", "decision=420ms playback_start=900ms"),
        ),
        decision=RehearsalDecision(
            triggered=True,
            addressing="addressed_to_me",
            reason="direct question with trigger",
            auto_action="wait_for_confirmation",
            would_speak=would_speak,
            blocked_reason="confirmation required within 3.0s",
            matched_phrase="Alice",
            question=True,
        ),
        live_control_state={
            "auto_answer_enabled": False,
            "manual_takeover": True,
            "hard_disabled": False,
            "last_trigger": "raw meeting secret TOKEN-123",
        },
        hotkey_status="ok",
        created_at="2026-05-22T10:00:00+00:00",
    )
    path = tmp_path / "rehearsal.json"
    path.write_text(
        json.dumps(rehearsal_artifact_to_json(artifact), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_scorecard_from_rehearsal_is_sanitized_and_maps_trigger_metrics(tmp_path):
    rehearsal_path = _write_rehearsal(tmp_path)

    scorecard = build_scorecard_from_rehearsal(rehearsal_path)
    payload = scorecard_to_json(scorecard)
    rendered = render_scorecard_markdown(scorecard)
    combined = json.dumps(payload, ensure_ascii=False) + rendered

    assert payload["profile"] == "personal"
    assert payload["source_type"] == "rehearsal"
    assert payload["source_id"] == "rehearsal.json"
    assert payload["status"] == "warn"
    assert payload["trigger_metrics"]["triggered_decisions"] == 1
    assert payload["trigger_metrics"]["addressed_to_me_decisions"] == 1
    assert payload["trigger_metrics"]["question_decisions"] == 1
    assert payload["trigger_metrics"]["auto_action"] == "wait_for_confirmation"
    assert payload["trigger_metrics"]["would_speak"] is False
    assert payload["trigger_metrics"]["blocked_reason"] == "confirmation required within 3.0s"
    assert payload["playback_metrics"]["playback_gate_status"] == "pass"
    assert payload["safety_metrics"]["auto_answer_enabled"] is False
    assert payload["safety_metrics"]["manual_takeover"] is True
    assert payload["safety_metrics"]["hard_disabled"] is False
    assert "Alice, please share" not in combined
    assert "TOKEN-123" not in combined
    assert "last_trigger" not in combined
    assert "/private/" not in combined


def test_scorecard_maps_regression_metrics_without_transcripts():
    metrics = RegressionMetrics(
        profile="personal",
        session_id="daily-sync",
        total=4,
        false_handoffs=1,
        missed_handoffs=2,
        question_noise=1,
        known_speakers=3,
        unknown_speakers=1,
        labeled_decisions=3,
        unlabeled_decisions=1,
        readiness="not_ready",
        readiness_missing=("need one rejected label",),
        speaker_counts={"other": 2, "unknown": 1, "me": 1},
        category_counts={"asked_to_speak": 2, "question": 1, "mentioned_me": 1},
        decision_counts={"accepted": 2, "rejected": 1, "unlabeled": 1},
        samples=(
            RegressionSample(
                sample="sample-001.json",
                sequence=1,
                stored_category="asked_to_speak",
                current_category="question",
                speaker="unknown",
                decision="accepted",
                current_will_answer=False,
                false_handoff=False,
                missed_handoff=True,
            ),
        ),
    )

    scorecard = build_scorecard_from_regression(metrics)
    payload = scorecard_to_json(scorecard)
    rendered = render_scorecard_markdown(scorecard)

    assert payload["source_type"] == "session"
    assert payload["source_id"] == "daily-sync"
    assert payload["status"] == "fail"
    assert payload["trigger_metrics"]["false_handoffs"] == 1
    assert payload["trigger_metrics"]["missed_handoffs"] == 2
    assert payload["trigger_metrics"]["question_noise"] == 1
    assert payload["trigger_metrics"]["speaker_coverage"]["known"] == 3
    assert payload["trigger_metrics"]["review_coverage"]["labeled"] == 3
    assert payload["trigger_metrics"]["classifier_readiness"] == "not_ready"
    assert "private" not in rendered
    assert "sample-001.json" in json.dumps(payload)


def test_scorecard_counts_live_control_audit_and_skips_malformed_rows(tmp_path):
    rehearsal_path = _write_rehearsal(tmp_path)
    audit_root = tmp_path / "live_control"
    audit_dir = audit_root / "personal"
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"action": "approved_speak", "result": "played"}),
                json.dumps({"action": "stop", "result": "cancelled"}),
                json.dumps({"action": "takeover", "result": "ok"}),
                json.dumps({"action": "hard_disable", "result": "ok"}),
                json.dumps({"action": "speak", "result": "automatic_playback_blocked"}),
                "{malformed",
                json.dumps({"action": "not-a-real-action", "result": "cancelled"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    scorecard = build_scorecard_from_rehearsal(rehearsal_path, audit_root=audit_root)
    payload = scorecard_to_json(scorecard)

    assert payload["playback_metrics"]["approved_speak_attempts"] == 1
    assert payload["playback_metrics"]["blocked_automatic_playback"] == 1
    assert payload["safety_metrics"]["stop_events"] == 1
    assert payload["safety_metrics"]["takeover_events"] == 1
    assert payload["safety_metrics"]["hard_disable_events"] == 1
    assert payload["safety_metrics"]["cancellation_events"] == 2
    assert "skipped 2 malformed audit rows" in payload["warnings"]


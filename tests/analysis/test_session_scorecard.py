"""Tests for sanitized session reliability scorecards."""

from __future__ import annotations

import json

from saymo.analysis.regression_replay import RegressionMetrics, RegressionSample
from saymo.analysis.realtime_events import RealtimeDecisionEvent
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
    scorecard_from_json,
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


def _write_launch_evidence(tmp_path):
    path = tmp_path / "call-ready.json"
    payload = {
        "schema_version": "1.0",
        "evidence_kind": "launch-readiness",
        "mode": "call-ready",
        "artifact_path": str(path),
        "profile": "personal",
        "provider": "glip",
        "ready": False,
        "check_count": 4,
        "ready_count": 1,
        "block_count": 2,
        "warn_count": 1,
        "checks": [
            {
                "key": "response_cache_coverage",
                "label": "response cache coverage",
                "severity": "block",
                "ok": False,
                "detail": "missing response cache variants",
                "action": "prepare response cache",
                "rerun": "saymo call-ready -p personal --provider glip",
                "metadata": {
                    "category": "source-data",
                    "ready": 1,
                    "total": 3,
                    "missing": 2,
                },
            },
            {
                "key": "provider_meeting_tab",
                "label": "provider meeting tab",
                "severity": "info",
                "ok": True,
                "detail": "meeting tab found",
                "metadata": {"meeting_found": True, "app_running": True},
            },
            {
                "key": "call_control_daemon",
                "label": "call-control daemon",
                "severity": "block",
                "ok": False,
                "detail": "stale heartbeat",
                "action": "restart daemon",
                "rerun": "saymo call-control-agent status -p personal",
                "metadata": {
                    "category": "call-control",
                    "running": False,
                    "heartbeat_fresh": False,
                    "stdout_log_path": "/tmp/saymo/out.log",
                    "stderr_log_path": "/tmp/saymo/err.log",
                },
            },
            {
                "key": "cloned_voice_metadata",
                "label": "cloned voice metadata",
                "severity": "warn",
                "ok": False,
                "detail": "profile approval warning",
                "metadata": {
                    "category": "voice-cache",
                    "voice_profile": "personal",
                    "reference_fingerprint": "voicefp_123",
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_realtime_events(tmp_path):
    path = tmp_path / "realtime-decisions.jsonl"
    events = [
        ("skipped", "launch-start", "launch_readiness"),
        ("blocked", "launch-readiness-blocked", "launch_readiness"),
        ("skipped", "launch-end", "launch_readiness"),
        ("spoke", "response-cache-hit", "response_cache"),
        ("blocked", "cache-miss-blocked", "response_cache"),
        ("blocked", "fallback-blocked", "playback"),
        ("blocked", "provider-blocked", "provider"),
        ("blocked", "handbrake-blocked", "live_control"),
        ("spoke", "playback-attempted", "playback"),
        ("blocked", "stop-requested", "live_control"),
    ]
    lines = [
        json.dumps(
            RealtimeDecisionEvent(
                created_at=f"2026-07-08T18:10:{index:02d}Z",
                profile="personal",
                provider="glip",
                outcome=outcome,
                label=label,
                source=source,
                detail="generated answer and PRIVATE_SENTINEL should be redacted",
            ).to_dict()
        )
        for index, (outcome, label, source) in enumerate(events)
    ]
    path.write_text("\n".join([*lines, "{malformed"]) + "\n", encoding="utf-8")
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
    assert "launch_metrics" not in payload
    assert "realtime_metrics" not in payload
    assert "v1.9 Evidence" not in rendered


def test_scorecard_includes_optional_launch_and_realtime_evidence(tmp_path):
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = _write_launch_evidence(tmp_path)
    realtime_path = _write_realtime_events(tmp_path)

    scorecard = build_scorecard_from_rehearsal(
        rehearsal_path,
        launch_json=launch_path,
        realtime_jsonl=realtime_path,
    )
    payload = scorecard_to_json(scorecard)
    rendered = render_scorecard_markdown(scorecard)
    combined = json.dumps(payload, ensure_ascii=False) + rendered

    assert payload["launch_metrics"] == {
        "status": "loaded",
        "ready": False,
        "block_count": 2,
        "warn_count": 1,
        "failed_labels": ["response cache coverage", "call-control daemon", "cloned voice metadata"],
        "blocker_categories": {"call-control": 1, "source-data": 1},
        "cache_ready": 1,
        "cache_total": 3,
        "cache_missing": 2,
        "voice_profile": "personal",
        "reference_fingerprint": "voicefp_123",
        "provider_ready": True,
        "daemon_ready": False,
        "daemon_running": False,
        "daemon_heartbeat_fresh": False,
        "artifact_path": str(launch_path),
        "log_paths": ["/tmp/saymo/out.log", "/tmp/saymo/err.log"],
        "rerun_commands": [
            "saymo call-ready -p personal --provider glip",
            "saymo call-control-agent status -p personal",
        ],
    }
    assert payload["realtime_metrics"] == {
        "status": "loaded",
        "total_events": 10,
        "malformed_rows": 1,
        "launch_starts": 1,
        "launch_ends": 1,
        "launch_blocks": 1,
        "cache_hits": 1,
        "cache_misses": 1,
        "fallback_blocks": 1,
        "provider_blocks": 1,
        "handbrake_blocks": 1,
        "playback_attempts": 1,
        "stop_reasons": {"stop-requested": 1},
        "label_counts": {
            "cache-miss-blocked": 1,
            "fallback-blocked": 1,
            "handbrake-blocked": 1,
            "launch-end": 1,
            "launch-readiness-blocked": 1,
            "launch-start": 1,
            "playback-attempted": 1,
            "provider-blocked": 1,
            "response-cache-hit": 1,
            "stop-requested": 1,
        },
        "source_counts": {
            "launch_readiness": 3,
            "live_control": 2,
            "playback": 2,
            "provider": 1,
            "response_cache": 2,
        },
        "artifact_path": str(realtime_path),
    }
    assert "## v1.9 Evidence" in rendered
    assert "launch: loaded ready=no blocks=2 warns=1" in rendered
    assert "failed launch labels: response cache coverage, call-control daemon, cloned voice metadata" in rendered
    assert "daemon: ready=no running=no heartbeat_fresh=no" in rendered
    assert "realtime launch: starts=1 ends=1 blocks=1 malformed_rows=1" in rendered
    assert "cache: hits=1 misses=1 fallback_blocks=1" in rendered
    assert "runtime blocks: provider=1 handbrake=1 playback_attempts=1" in rendered
    assert "stop reasons: stop-requested=1" in rendered
    assert "generated answer" not in combined
    assert "PRIVATE_SENTINEL" not in combined


def test_scorecard_marks_supplied_missing_evidence_paths(tmp_path):
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = tmp_path / "missing-call-ready.json"
    realtime_path = tmp_path / "missing-realtime.jsonl"

    scorecard = build_scorecard_from_rehearsal(
        rehearsal_path,
        launch_json=launch_path,
        realtime_jsonl=realtime_path,
    )
    payload = scorecard_to_json(scorecard)
    rendered = render_scorecard_markdown(scorecard)

    assert payload["launch_metrics"]["status"] == "missing"
    assert payload["launch_metrics"]["artifact_path"] == str(launch_path)
    assert payload["realtime_metrics"]["status"] == "missing"
    assert payload["realtime_metrics"]["artifact_path"] == str(realtime_path)
    assert "launch: missing" in rendered
    assert "realtime: missing" in rendered
    assert "launch evidence not found" in payload["warnings"]
    assert "realtime evidence not found" in payload["warnings"]


def test_old_scorecard_json_round_trips_without_phase40_fields(tmp_path):
    old_payload = scorecard_to_json(build_scorecard_from_rehearsal(_write_rehearsal(tmp_path)))

    scorecard = scorecard_from_json(old_payload)
    payload = scorecard_to_json(scorecard)
    rendered = render_scorecard_markdown(scorecard)

    assert "launch_metrics" not in old_payload
    assert "realtime_metrics" not in old_payload
    assert "launch_metrics" not in payload
    assert "realtime_metrics" not in payload
    assert "v1.9 Evidence" not in rendered


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
    assert payload["playback_metrics"]["unsafe_automatic_playback"] == 0
    assert payload["safety_metrics"]["stop_events"] == 1
    assert payload["safety_metrics"]["takeover_events"] == 1
    assert payload["safety_metrics"]["hard_disable_events"] == 1
    assert payload["safety_metrics"]["cancellation_events"] == 2
    assert "skipped 2 malformed audit rows" in payload["warnings"]


def test_scorecard_counts_unsafe_automatic_playback_from_audit(tmp_path):
    metrics = RegressionMetrics(
        profile="personal",
        session_id="daily-sync",
        total=1,
        false_handoffs=0,
        missed_handoffs=0,
        question_noise=0,
        known_speakers=1,
        unknown_speakers=0,
        labeled_decisions=1,
        unlabeled_decisions=0,
        readiness="ready",
        readiness_missing=(),
        speaker_counts={"me": 1},
        category_counts={"asked_to_speak": 1},
        decision_counts={"accepted": 1},
        samples=(),
    )
    audit_root = tmp_path / "live_control"
    audit_dir = audit_root / "personal"
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.jsonl").write_text(
        json.dumps(
            {
                "action": "speak",
                "source": "auto",
                "result": "automatic_playback_played",
                "previous_state": {"auto_answer_enabled": False},
                "next_state": {"auto_answer_enabled": False},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    scorecard = build_scorecard_from_regression(metrics, audit_root=audit_root)
    payload = scorecard_to_json(scorecard)

    assert payload["playback_metrics"]["unsafe_automatic_playback"] == 1
    assert payload["safety_metrics"]["auto_answer_enabled"] is False

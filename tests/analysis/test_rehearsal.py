"""Tests for pre-call rehearsal artifacts."""

import json

from saymo.analysis.rehearsal import (
    RehearsalArtifact,
    RehearsalCheck,
    RehearsalDecision,
    default_rehearsal_dir,
    rehearsal_artifact_from_json,
    rehearsal_artifact_to_json,
    write_rehearsal_artifact,
)


def test_rehearsal_artifact_round_trip_is_sanitized(tmp_path):
    artifact = RehearsalArtifact(
        profile="personal",
        provider="glip",
        transcript="John, share TOKEN-123 status?",
        dry_run=True,
        status="pass",
        checks=(
            RehearsalCheck("preflight: capture input", "pass", "BlackHole 16ch"),
            RehearsalCheck("playback gate", "pass", "dry-run would speak"),
        ),
        decision=RehearsalDecision(
            triggered=True,
            addressing="addressed_to_me",
            reason="direct question with trigger",
            auto_action="answer_now",
            would_speak=True,
            blocked_reason="",
        ),
        live_control_state={
            "auto_answer_enabled": True,
            "manual_takeover": False,
            "last_trigger": "John, share TOKEN-123 status?",
        },
        hotkey_status="ok",
        created_at="2026-05-22T10:00:00+00:00",
    )

    payload = rehearsal_artifact_to_json(artifact)
    text = json.dumps(payload, ensure_ascii=False)

    assert payload["profile"] == "personal"
    assert payload["transcript"] == ""
    assert payload["decision"]["auto_action"] == "answer_now"
    assert payload["decision"]["would_speak"] is True
    assert payload["live_control_state"] == {
        "auto_answer_enabled": True,
        "manual_takeover": False,
    }
    assert "raw_audio" not in text
    assert "TOKEN-123" not in text
    assert "last_trigger" not in text

    loaded = rehearsal_artifact_from_json(payload)
    assert loaded.transcript == ""
    assert loaded.live_control_state == {"auto_answer_enabled": True, "manual_takeover": False}


def test_write_rehearsal_artifact_uses_profile_directory(tmp_path):
    artifact = RehearsalArtifact(
        profile="daily",
        provider="glip",
        transcript="",
        dry_run=True,
        status="warn",
        checks=(RehearsalCheck("response cache", "warn", "0/4 variants"),),
        decision=RehearsalDecision(
            triggered=False,
            addressing="no_trigger",
            reason="no trigger phrase in transcript",
            auto_action="skip",
            would_speak=False,
            blocked_reason="no trigger",
        ),
        live_control_state={},
        hotkey_status="skipped",
        created_at="2026-05-22T10:00:00+00:00",
    )

    path = write_rehearsal_artifact(artifact, base_dir=tmp_path)

    assert path.parent == default_rehearsal_dir("daily", base_dir=tmp_path)
    assert path.name.endswith(".json")
    loaded = rehearsal_artifact_from_json(json.loads(path.read_text(encoding="utf-8")))
    assert loaded.profile == artifact.profile
    assert loaded.decision == artifact.decision
    assert loaded.transcript == ""

"""Tests for sanitized realtime decision event evidence."""

from __future__ import annotations

import json
from pathlib import Path

from saymo.analysis.realtime_events import (
    RealtimeDecisionEvent,
    append_realtime_decision_event,
    realtime_event_log_path,
)


EXPECTED_EVENT_KEYS = {
    "created_at",
    "profile",
    "provider",
    "outcome",
    "label",
    "source",
    "automatic",
    "intent_key",
    "confidence",
    "audio_path",
    "detail",
}


def test_realtime_decision_event_serializes_stable_allowlisted_fields_only():
    event = RealtimeDecisionEvent(
        created_at="2026-07-08T17:00:00Z",
        profile="standup",
        provider="glip",
        outcome="blocked",
        label="cache-miss-blocked",
        source="response_cache",
        automatic=True,
        intent_key="status_ready",
        confidence=0.87,
        audio_path="/tmp/status-ready.wav",
        detail=(
            "token=super-secret-value PRIVATE_SENTINEL "
            "raw transcript says launch codename"
        ),
    )

    payload = event.to_dict()

    assert set(payload) == EXPECTED_EVENT_KEYS
    assert payload["outcome"] == "blocked"
    assert payload["label"] == "cache-miss-blocked"
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "super-secret-value" not in serialized
    assert "PRIVATE_SENTINEL" not in serialized
    assert "launch codename" not in serialized
    assert "transcript_window" not in serialized
    assert "generated_answer" not in serialized
    assert "answer_text" not in serialized
    assert "daily_note" not in serialized
    assert "audio_bytes" not in serialized


def test_realtime_event_log_path_uses_profile_live_control_directory(tmp_path):
    path = realtime_event_log_path("standup", base_dir=tmp_path)

    assert path == tmp_path / "standup" / "realtime-decisions.jsonl"


def test_append_realtime_decision_event_writes_jsonl_under_live_control_dir(tmp_path):
    event = RealtimeDecisionEvent(
        created_at="2026-07-08T17:01:00Z",
        profile="standup",
        provider="glip",
        outcome="spoke",
        label="response-cache-hit",
        source="response_cache",
        intent_key="status_ready",
        confidence=0.92,
        audio_path=str(tmp_path / "status-ready.wav"),
        detail="prepared cached response selected",
    )

    path = append_realtime_decision_event("standup", event, base_dir=tmp_path)

    assert path == tmp_path / "standup" / "realtime-decisions.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [event.to_dict()]


def test_append_realtime_decision_event_uses_live_control_dir_helper(monkeypatch, tmp_path):
    from saymo.analysis import live_control

    calls = []

    def fake_live_control_dir(profile: str, *, base_dir=None) -> Path:
        calls.append((profile, base_dir))
        path = tmp_path / "control" / profile
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(live_control, "live_control_dir", fake_live_control_dir)

    event = RealtimeDecisionEvent(
        created_at="2026-07-08T17:02:00Z",
        profile="standup",
        provider="glip",
        outcome="skipped",
        label="addressing-skip",
        source="deterministic",
        detail="mention-only",
    )

    path = append_realtime_decision_event("standup", event, base_dir=tmp_path)

    assert calls == [("standup", tmp_path)]
    assert path == tmp_path / "control" / "standup" / "realtime-decisions.jsonl"

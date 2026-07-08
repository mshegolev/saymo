"""Tests for sanitized realtime decision event evidence."""

from __future__ import annotations

import json
from pathlib import Path

from saymo.analysis.realtime_events import (
    RealtimeDecisionEvent,
    append_realtime_decision_event,
    load_realtime_decision_events,
    realtime_event_log_path,
    summarize_realtime_decision_events,
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


def test_load_realtime_decision_events_skips_malformed_rows_and_resanitizes(tmp_path):
    path = tmp_path / "realtime-decisions.jsonl"
    good = RealtimeDecisionEvent(
        created_at="2026-07-08T18:00:00Z",
        profile="standup",
        provider="glip",
        outcome="spoke",
        label="response-cache-hit",
        source="response_cache",
        detail="prepared response selected",
    ).to_dict()
    row_with_extra_private_fields = {
        **RealtimeDecisionEvent(
            created_at="2026-07-08T18:00:01Z",
            profile="standup",
            provider="glip",
            outcome="blocked",
            label="cache-miss-blocked",
            source="response_cache",
            detail="raw transcript contained PRIVATE_LEAK",
        ).to_dict(),
        "raw_transcript": "Alice said the launch secret",
        "generated_answer": "private answer body",
    }
    path.write_text(
        "\n".join(
            [
                json.dumps(good),
                "",
                "{malformed",
                json.dumps(["not", "an", "event"]),
                json.dumps(row_with_extra_private_fields),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    events = load_realtime_decision_events(path)

    assert [event.label for event in events] == [
        "response-cache-hit",
        "cache-miss-blocked",
    ]
    serialized = json.dumps([event.to_dict() for event in events], ensure_ascii=False)
    assert "Alice said" not in serialized
    assert "private answer body" not in serialized
    assert "PRIVATE_LEAK" not in serialized


def test_summarize_realtime_decision_events_counts_phase40_labels(tmp_path):
    path = tmp_path / "realtime-decisions.jsonl"
    rows = [
        ("skipped", "launch-start", "launch_readiness"),
        ("skipped", "launch-end", "launch_readiness"),
        ("blocked", "launch-readiness-blocked", "launch_readiness"),
        ("spoke", "response-cache-hit", "response_cache"),
        ("blocked", "cache-miss-blocked", "response_cache"),
        ("blocked", "cache-disabled-blocked", "response_cache"),
        ("blocked", "voice-metadata-blocked", "response_cache"),
        ("blocked", "fallback-blocked", "playback"),
        ("blocked", "provider-blocked", "provider"),
        ("blocked", "handbrake-blocked", "live_control"),
        ("spoke", "playback-attempted", "playback"),
        ("blocked", "stop-requested", "live_control"),
        ("blocked", "cancel-playback", "live_control"),
    ]
    lines = [
        json.dumps(
            RealtimeDecisionEvent(
                created_at=f"2026-07-08T18:01:{index:02d}Z",
                profile="standup",
                provider="glip",
                outcome=outcome,
                label=label,
                source=source,
            ).to_dict()
        )
        for index, (outcome, label, source) in enumerate(rows)
    ]
    path.write_text(
        "\n".join([*lines, "{malformed", json.dumps("not a row"), ""]) + "\n",
        encoding="utf-8",
    )

    summary = summarize_realtime_decision_events(path)

    assert summary.path == str(path)
    assert summary.total == 13
    assert summary.malformed_rows == 2
    assert summary.outcome_counts == {"blocked": 9, "skipped": 2, "spoke": 2}
    assert summary.source_counts == {
        "launch_readiness": 3,
        "live_control": 3,
        "playback": 2,
        "provider": 1,
        "response_cache": 4,
    }
    assert summary.label_counts["cache-disabled-blocked"] == 1
    assert summary.launch_starts == 1
    assert summary.launch_ends == 1
    assert summary.launch_blocks == 1
    assert summary.cache_hits == 1
    assert summary.cache_misses == 1
    assert summary.fallback_blocks == 1
    assert summary.provider_blocks == 1
    assert summary.handbrake_blocks == 1
    assert summary.playback_attempts == 1
    assert summary.stop_reasons == {
        "cancel-playback": 1,
        "stop-requested": 1,
    }

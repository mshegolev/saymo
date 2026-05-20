"""Tests for trigger-sample review primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass

from saymo.analysis.trigger_review import (
    ReviewAction,
    TriggerReviewFilters,
    apply_category_relabel,
    build_sanitized_review_report,
    filter_review_rows,
    parse_review_action,
)


@dataclass(frozen=True)
class _Record:
    path: object
    profile: str = "personal"
    category: str = "question"
    session_id: str = "daily-20260520-100000"
    session_name: str = "daily sync"
    session_sequence: int = 1
    speaker: str = "unknown"
    answer_decision: str = "unlabeled"
    created_at: str = "2026-05-20T10:00:00"
    transcript: str = "private transcript"
    trigger: bool = False
    question: bool = True
    will_answer: bool = False
    addressing: str = "ignore"
    reason: str = "test"
    rms: float = 0.01
    peak: float = 0.1
    wav: str = "sample.wav"


@dataclass(frozen=True)
class _Row:
    record: _Record
    current_category: str = "question"
    current_trigger: bool = False
    current_question: bool = True
    current_will_answer: bool = False
    current_addressing: str = "ignore"
    miss: bool = False
    false_positive: bool = False


def _row(tmp_path, name, **record_overrides):
    path = tmp_path / f"{name}.json"
    record = _Record(path=path, **record_overrides)
    return _Row(record=record)


def _write_sample(base_dir, *, profile="personal", category="question", name="sample"):
    sample_dir = base_dir / profile / category
    sample_dir.mkdir(parents=True, exist_ok=True)
    json_path = sample_dir / f"{name}.json"
    wav_path = sample_dir / f"{name}.wav"
    metadata = {
        "profile": profile,
        "category": category,
        "session_id": "daily-20260520-100000",
        "session_name": "daily sync",
        "session_sequence": 3,
        "speaker": "other",
        "answer_decision": "accepted",
        "created_at": "2026-05-20T10:00:00",
        "transcript": "do not leak this",
        "trigger": True,
        "question": True,
        "will_answer": True,
        "addressing": "addressed_to_me",
        "reason": "test",
        "rms": 0.01,
        "peak": 0.1,
        "wav": f"{name}.wav",
    }
    json_path.write_text(json.dumps(metadata), encoding="utf-8")
    wav_path.write_bytes(b"RIFF")
    return json_path, wav_path


def test_filter_review_rows_matches_metadata_and_classifier_disagreement(tmp_path):
    rows = [
        _row(
            tmp_path,
            "match",
            category="asked_to_speak",
            session_id="daily-20260520-100000",
            speaker="other",
            answer_decision="accepted",
            created_at="2026-05-20T10:15:00",
        ),
        _row(
            tmp_path,
            "wrong_session",
            category="asked_to_speak",
            session_id="weekly-20260520-100000",
            speaker="other",
            answer_decision="accepted",
            created_at="2026-05-20T10:15:00",
        ),
        _row(
            tmp_path,
            "too_old",
            category="asked_to_speak",
            session_id="daily-20260520-100001",
            speaker="other",
            answer_decision="accepted",
            created_at="2026-05-19T23:59:00",
        ),
    ]
    rows[0] = _Row(record=rows[0].record, current_category="speech")

    filtered = filter_review_rows(
        rows,
        TriggerReviewFilters(
            session="daily-20260520",
            category="asked_to_speak",
            speaker="other",
            answer_decision="accepted",
            date_from="2026-05-20",
            date_to="2026-05-20T23:59:59",
            classifier_disagreement=True,
        ),
    )

    assert [row.record.path.name for row in filtered] == ["match.json"]


def test_filter_review_rows_rejects_invalid_date_filter(tmp_path):
    rows = [_row(tmp_path, "sample")]

    try:
        filter_review_rows(rows, TriggerReviewFilters(date_from="not-a-date"))
    except ValueError as e:
        assert "Invalid date_from" in str(e)
    else:
        raise AssertionError("invalid date filter should fail")


def test_apply_category_relabel_updates_metadata_and_moves_adjacent_wav(tmp_path):
    json_path, wav_path = _write_sample(tmp_path, category="question")

    result = apply_category_relabel(json_path, "asked_to_speak")

    assert result.previous_category == "question"
    assert result.category == "asked_to_speak"
    assert not json_path.exists()
    assert not wav_path.exists()
    assert result.path == tmp_path / "personal" / "asked_to_speak" / "sample.json"
    assert result.wav_path == tmp_path / "personal" / "asked_to_speak" / "sample.wav"
    metadata = json.loads(result.path.read_text(encoding="utf-8"))
    assert metadata["category"] == "asked_to_speak"
    assert metadata["session_id"] == "daily-20260520-100000"
    assert metadata["session_name"] == "daily sync"
    assert metadata["session_sequence"] == 3
    assert result.wav_path.read_bytes() == b"RIFF"


def test_build_sanitized_review_report_groups_by_session_then_category(tmp_path):
    rows = [
        _row(
            tmp_path,
            "answer",
            category="asked_to_speak",
            session_id="daily-20260520-100000",
            session_name="daily sync",
            speaker="other",
            answer_decision="accepted",
            transcript="private answer transcript",
        ),
        _row(
            tmp_path,
            "speech",
            category="speech",
            session_id="daily-20260520-100000",
            session_name="daily sync",
            speaker="me",
            answer_decision="rejected",
            transcript="private speech transcript",
        ),
        _row(
            tmp_path,
            "question",
            category="question",
            session_id="weekly-20260520-100000",
            session_name="weekly sync",
            transcript="private question transcript",
        ),
    ]

    report = build_sanitized_review_report(rows)

    assert [session.session_id for session in report.sessions] == [
        "daily-20260520-100000",
        "weekly-20260520-100000",
    ]
    assert [category.category for category in report.sessions[0].categories] == [
        "asked_to_speak",
        "speech",
    ]
    assert report.sessions[0].categories[0].speaker_counts == {"other": 1}
    assert report.sessions[0].categories[1].answer_decision_counts == {"rejected": 1}
    assert report.sessions[0].categories[0].samples[0].path == "answer.json"
    assert not hasattr(report.sessions[0].categories[0].samples[0], "transcript")
    assert "private" not in repr(report)


def test_parse_review_action_accepts_category_speaker_decision_skip_and_quit():
    assert parse_review_action("category asked_to_speak") == ReviewAction(
        "category",
        "asked_to_speak",
    )
    assert parse_review_action("c speech") == ReviewAction("category", "speech")
    assert parse_review_action("speaker other") == ReviewAction("speaker", "other")
    assert parse_review_action("sp me") == ReviewAction("speaker", "me")
    assert parse_review_action("decision reject") == ReviewAction(
        "decision",
        "rejected",
    )
    assert parse_review_action("accepted") == ReviewAction("decision", "accepted")
    assert parse_review_action("skip") == ReviewAction("skip")
    assert parse_review_action("q") == ReviewAction("quit")
    assert parse_review_action("not-a-review-action") is None

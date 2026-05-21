"""Tests for sanitized saved-session regression replay metrics."""

from __future__ import annotations

from dataclasses import dataclass

from saymo.analysis.regression_replay import (
    build_regression_metrics,
    regression_metrics_from_json,
    regression_metrics_to_json,
    render_regression_report,
)


@dataclass(frozen=True)
class _Record:
    path: object
    category: str
    speaker: str
    answer_decision: str
    session_sequence: int
    transcript: str


@dataclass(frozen=True)
class _Row:
    record: _Record
    current_category: str
    current_question: bool
    current_will_answer: bool


def test_regression_metrics_and_report_are_sanitized(tmp_path):
    rows = [
        _Row(
            record=_Record(
                path=tmp_path / "false.json",
                category="asked_to_speak",
                speaker="unknown",
                answer_decision="rejected",
                session_sequence=1,
                transcript="private false handoff",
            ),
            current_category="mentioned_me",
            current_question=False,
            current_will_answer=False,
        ),
        _Row(
            record=_Record(
                path=tmp_path / "handoff.json",
                category="asked_to_speak",
                speaker="other",
                answer_decision="accepted",
                session_sequence=2,
                transcript="private true handoff",
            ),
            current_category="asked_to_speak",
            current_question=True,
            current_will_answer=True,
        ),
        _Row(
            record=_Record(
                path=tmp_path / "question.json",
                category="question",
                speaker="unknown",
                answer_decision="unlabeled",
                session_sequence=3,
                transcript="private general question",
            ),
            current_category="question",
            current_question=True,
            current_will_answer=False,
        ),
    ]

    metrics = build_regression_metrics(rows, profile="personal", session_id="daily")
    rendered = render_regression_report(metrics)
    loaded = regression_metrics_from_json(regression_metrics_to_json(metrics))

    assert metrics.false_handoffs == 0
    assert metrics.missed_handoffs == 0
    assert metrics.question_noise == 1
    assert metrics.known_speakers == 1
    assert metrics.unknown_speakers == 2
    assert "speaker coverage: known=1/3 unknown=2" in rendered
    assert "private" not in rendered
    assert loaded.samples[0].sample == "false.json"


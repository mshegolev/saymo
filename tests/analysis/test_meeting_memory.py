"""Tests for local meeting-memory transcript ledgers."""

import json

from saymo.analysis.meeting_memory import (
    build_meeting_ledger_from_samples,
    load_meeting_ledger,
    meeting_transcript_path,
    render_meeting_summary,
    summarize_meeting_ledger,
    write_meeting_ledger,
)
from saymo.analysis.trigger_sessions import start_trigger_session


def _write_sample(
    base_dir,
    *,
    profile="daily",
    session_id="daily-20260520-100000",
    sequence=1,
    category="question",
    speaker="other",
    transcript="John, what is the status?",
    created_at="2026-05-20T10:00:00",
    trigger=True,
    question=True,
    will_answer=True,
):
    sample_dir = base_dir / profile / category
    sample_dir.mkdir(parents=True, exist_ok=True)
    path = sample_dir / f"sample-{sequence}.json"
    path.write_text(
        json.dumps(
            {
                "profile": profile,
                "session_id": session_id,
                "session_name": "daily",
                "session_sequence": sequence,
                "created_at": created_at,
                "sample_rate": 16000,
                "wav": f"sample-{sequence}.wav",
                "category": category,
                "speaker": speaker,
                "answer_decision": "unlabeled",
                "transcript": transcript,
                "trigger": trigger,
                "question": question,
                "will_answer": will_answer,
                "addressing": "addressed_to_me" if will_answer else "ignore",
                "reason": "test",
                "rms": 0.02,
                "peak": 0.2,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_meeting_ledger_round_trip_uses_session_sidecar_path(tmp_path):
    session = start_trigger_session(
        base_dir=tmp_path,
        profile="daily",
        session_name="daily",
        started_at="2026-05-20T10:00:00",
    )
    _write_sample(tmp_path, session_id=session.session_id, sequence=1)

    ledger = build_meeting_ledger_from_samples(
        base_dir=tmp_path,
        profile="daily",
        session_id=session.session_id,
        session=session,
        window_seconds=8.0,
    )
    path = write_meeting_ledger(tmp_path, ledger)
    loaded = load_meeting_ledger(path)

    assert path == meeting_transcript_path(tmp_path, "daily", session.session_id)
    assert loaded.profile == "daily"
    assert loaded.session_id == session.session_id
    assert loaded.source_sample_count == 1
    assert loaded.segments[0].transcript == "John, what is the status?"
    assert loaded.segments[0].start_seconds == 0.0
    assert loaded.segments[0].end_seconds == 8.0
    assert loaded.segments[0].speaker == "other"


def test_build_meeting_ledger_can_drop_transcript_text(tmp_path):
    _write_sample(tmp_path, transcript="private transcript")

    ledger = build_meeting_ledger_from_samples(
        base_dir=tmp_path,
        profile="daily",
        session_id="daily-20260520-100000",
        retain_transcripts=False,
    )

    assert ledger.retain_transcripts is False
    assert ledger.segments[0].transcript == ""
    assert ledger.incomplete_segments == 1


def test_meeting_summary_counts_questions_handoffs_and_actions(tmp_path):
    _write_sample(
        tmp_path,
        sequence=1,
        category="asked_to_speak",
        transcript="John, can you share the status?",
        will_answer=True,
    )
    _write_sample(
        tmp_path,
        sequence=2,
        category="speech",
        speaker="me",
        transcript="Нужно проверить логи после созвона",
        trigger=False,
        question=False,
        will_answer=False,
        created_at="2026-05-20T10:00:08",
    )

    ledger = build_meeting_ledger_from_samples(
        base_dir=tmp_path,
        profile="daily",
        session_id="daily-20260520-100000",
    )
    summary = summarize_meeting_ledger(ledger)
    rendered = render_meeting_summary(summary)

    assert summary.total_segments == 2
    assert summary.questions[0].sequence == 1
    assert summary.handoffs[0].sequence == 1
    assert summary.action_items[0].sequence == 2
    assert "incomplete coverage: 0" in rendered
    assert "John, can you share the status?" in rendered

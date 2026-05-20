"""Tests for trigger-capture session ledgers."""

import json

from saymo.analysis.trigger_sessions import (
    basic_training_readiness,
    finish_trigger_session,
    list_trigger_sessions,
    make_session_id,
    start_trigger_session,
    summarize_trigger_session,
)


def _write_session_sample(
    base_dir,
    *,
    profile="daily",
    session_id="daily-20260520-100000",
    category="question",
    name="sample",
    speaker="unknown",
    decision="unlabeled",
    created_at="2026-05-20T10:00:00",
):
    sample_dir = base_dir / profile / category
    sample_dir.mkdir(parents=True, exist_ok=True)
    path = sample_dir / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "profile": profile,
                "session_id": session_id,
                "session_name": "daily",
                "created_at": created_at,
                "sample_rate": 16000,
                "wav": f"{name}.wav",
                "category": category,
                "speaker": speaker,
                "answer_decision": decision,
                "transcript": "",
                "trigger": False,
                "question": False,
                "will_answer": False,
                "addressing": "ignore",
                "reason": "test",
                "rms": 0.01,
                "peak": 0.1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_make_session_id_uses_name_and_timestamp():
    assert make_session_id("Daily Standup", "2026-05-20T10:00:01") == (
        "daily-standup-20260520-100001"
    )


def test_start_and_finish_trigger_session_writes_ledger(tmp_path):
    session = start_trigger_session(
        base_dir=tmp_path,
        profile="daily",
        session_name="morning sync",
        started_at="2026-05-20T10:00:00",
    )
    _write_session_sample(
        tmp_path,
        session_id=session.session_id,
        category="asked_to_speak",
        name="answer",
        speaker="other",
        decision="accepted",
    )
    _write_session_sample(
        tmp_path,
        session_id=session.session_id,
        category="speech",
        name="skip",
        speaker="me",
        decision="rejected",
        created_at="2026-05-20T10:00:08",
    )

    finished = finish_trigger_session(
        base_dir=tmp_path,
        session=session,
        ended_at="2026-05-20T10:00:10",
        status="completed",
        skipped_silence=2,
    )

    assert finished.path is not None
    payload = json.loads(finished.path.read_text(encoding="utf-8"))
    assert payload["session_id"] == session.session_id
    assert payload["status"] == "completed"
    assert payload["summary"]["saved_samples"] == 2
    assert payload["summary"]["skipped_silence"] == 2
    assert payload["summary"]["categories"]["asked_to_speak"] == 1
    assert payload["summary"]["speakers"]["other"] == 1
    assert payload["summary"]["answer_decisions"]["accepted"] == 1
    assert payload["summary"]["readiness"] == "needs_samples"


def test_start_trigger_session_avoids_overwriting_same_second(tmp_path):
    first = start_trigger_session(
        base_dir=tmp_path,
        profile="daily",
        session_name="daily",
        started_at="2026-05-20T10:00:00",
    )
    second = start_trigger_session(
        base_dir=tmp_path,
        profile="daily",
        session_name="daily",
        started_at="2026-05-20T10:00:00",
    )

    assert first.session_id == "daily-20260520-100000"
    assert second.session_id == "daily-20260520-100000-2"
    assert first.path != second.path


def test_summarize_trigger_session_counts_current_sample_metadata(tmp_path):
    _write_session_sample(
        tmp_path,
        category="asked_to_speak",
        name="accepted",
        speaker="other",
        decision="accepted",
    )
    _write_session_sample(
        tmp_path,
        category="speech",
        name="rejected",
        speaker="me",
        decision="rejected",
        created_at="2026-05-20T10:00:05",
    )
    _write_session_sample(
        tmp_path,
        session_id="other-session",
        category="question",
        name="ignored",
    )

    summary = summarize_trigger_session(
        base_dir=tmp_path,
        profile="daily",
        session_id="daily-20260520-100000",
        skipped_silence=1,
    )

    assert summary.total_windows == 3
    assert summary.saved_samples == 2
    assert summary.skipped_silence == 1
    assert summary.categories == {"asked_to_speak": 1, "speech": 1}
    assert summary.speakers == {"me": 1, "other": 1}
    assert summary.answer_decisions == {"accepted": 1, "rejected": 1}
    assert summary.first_sample_at == "2026-05-20T10:00:00"
    assert summary.last_sample_at == "2026-05-20T10:00:05"


def test_list_trigger_sessions_refreshes_summary(tmp_path):
    session = start_trigger_session(
        base_dir=tmp_path,
        profile="daily",
        session_name="daily",
        started_at="2026-05-20T10:00:00",
    )
    _write_session_sample(tmp_path, session_id=session.session_id, category="question")
    finish_trigger_session(
        base_dir=tmp_path,
        session=session,
        ended_at="2026-05-20T10:00:10",
        status="completed",
        skipped_silence=1,
    )

    sessions = list_trigger_sessions(tmp_path, profile="daily")

    assert [s.session_id for s in sessions] == [session.session_id]
    assert sessions[0].summary.saved_samples == 1
    assert sessions[0].summary.skipped_silence == 1


def test_basic_training_readiness_labels():
    assert basic_training_readiness(saved_samples=0, answer_decisions={}) == "empty"
    assert (
        basic_training_readiness(saved_samples=2, answer_decisions={"accepted": 1})
        == "needs_samples"
    )
    assert (
        basic_training_readiness(saved_samples=4, answer_decisions={"accepted": 4})
        == "needs_labels"
    )
    assert (
        basic_training_readiness(
            saved_samples=4,
            answer_decisions={"accepted": 2, "rejected": 2},
        )
        == "ready"
    )

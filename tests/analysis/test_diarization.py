"""Tests for optional local diarization helpers."""

import json

from saymo.analysis.diarization import (
    DiarizationConfigView,
    DiarizationResult,
    DiarizationSessionSidecar,
    DiarizationSegment,
    TriggerSampleSpeakerSuggestion,
    build_speaker_quality_report,
    build_session_speaker_suggestions,
    check_diarization_availability,
    diarization_result_from_json,
    diarization_result_to_json,
    render_speaker_quality_report,
    review_speaker_suggestion,
    load_session_diarization,
    session_diarization_path,
    speaker_cluster_summary,
    write_session_diarization,
)
from saymo.config import DiarizationConfig


def test_diarization_availability_reports_disabled_by_default():
    status = check_diarization_availability(DiarizationConfig())

    assert status.engine == "disabled"
    assert status.available is False
    assert status.status == "disabled"
    assert "disabled" in status.reason


def test_diarization_availability_reports_missing_pyannote():
    status = check_diarization_availability(
        DiarizationConfig(enabled=True, engine="pyannote", auth_token_env="")
    )

    assert status.engine == "pyannote"
    assert status.available is False
    assert status.status in {"missing_dependency", "missing_token"}
    assert status.reason


def test_diarization_availability_checks_token_env(monkeypatch):
    monkeypatch.delenv("SAYMO_DIARIZATION_TOKEN", raising=False)

    status = check_diarization_availability(
        DiarizationConfig(
            enabled=True,
            engine="pyannote",
            auth_token_env="SAYMO_DIARIZATION_TOKEN",
        ),
        import_checker=lambda module: True,
    )

    assert status.status == "missing_token"
    assert status.token_env == "SAYMO_DIARIZATION_TOKEN"
    assert status.token_available is False

    monkeypatch.setenv("SAYMO_DIARIZATION_TOKEN", "secret")
    ready = check_diarization_availability(
        DiarizationConfig(
            enabled=True,
            engine="pyannote",
            auth_token_env="SAYMO_DIARIZATION_TOKEN",
        ),
        import_checker=lambda module: True,
    )

    assert ready.available is True
    assert ready.status == "ready"
    assert ready.token_available is True


def test_diarization_config_view_normalizes_bounds():
    view = DiarizationConfigView.from_config(
        DiarizationConfig(
            enabled=True,
            engine=" PyAnNoTe ",
            model="",
            device="",
            min_speakers=0,
            max_speakers=1,
        )
    )

    assert view.engine == "pyannote"
    assert view.model == "pyannote/speaker-diarization-3.1"
    assert view.device == "cpu"
    assert view.min_speakers == 1
    assert view.max_speakers == 1


def test_diarization_result_json_roundtrip():
    result = DiarizationResult(
        profile="personal",
        session_id="daily-20260520-120000",
        engine="pyannote",
        model="pyannote/speaker-diarization-3.1",
        created_at="2026-05-20T12:00:00",
        segments=(
            DiarizationSegment(
                speaker_id="SPEAKER_00",
                start_seconds=0.2,
                end_seconds=1.4,
                confidence=0.87,
            ),
        ),
    )

    payload = diarization_result_to_json(result)
    loaded = diarization_result_from_json(json.loads(json.dumps(payload)))

    assert loaded == result


def test_build_session_speaker_suggestions_uses_best_overlap():
    class Sample:
        path = "/samples/personal/question/a.json"
        session_sequence = 1
        speaker = "unknown"

    suggestions = build_session_speaker_suggestions(
        [Sample()],
        (
            DiarizationSegment("SPEAKER_00", 0.0, 2.0, 0.8),
            DiarizationSegment("SPEAKER_01", 2.0, 8.0, 0.6),
        ),
        window_seconds=8.0,
        speaker_mappings={"SPEAKER_01": "other"},
    )

    assert suggestions == (
        TriggerSampleSpeakerSuggestion(
            sample_path="/samples/personal/question/a.json",
            session_sequence=1,
            current_speaker="unknown",
            speaker_id="SPEAKER_01",
            suggested_speaker="other",
            confidence=0.6,
            overlap_seconds=6.0,
            status="suggested",
        ),
    )


def test_session_diarization_sidecar_roundtrip(tmp_path):
    sidecar = DiarizationSessionSidecar(
        profile="personal",
        session_id="daily-20260520-120000",
        engine="pyannote",
        model="model",
        created_at="2026-05-20T12:00:00",
        segments=(DiarizationSegment("SPEAKER_00", 0.0, 4.0, 0.7),),
        speaker_mappings={"SPEAKER_00": "me"},
        suggestions=(
            TriggerSampleSpeakerSuggestion(
                sample_path="question/a.json",
                session_sequence=1,
                current_speaker="unknown",
                speaker_id="SPEAKER_00",
                suggested_speaker="me",
                confidence=0.7,
                overlap_seconds=4.0,
            ),
        ),
    )

    path = write_session_diarization(tmp_path, sidecar)
    loaded = load_session_diarization(path)

    assert path == session_diarization_path(tmp_path, "personal", sidecar.session_id)
    assert loaded == sidecar


def test_speaker_cluster_summary_counts_segments_and_suggestions():
    sidecar = DiarizationSessionSidecar(
        profile="personal",
        session_id="daily",
        engine="pyannote",
        model="model",
        created_at="2026-05-20T12:00:00",
        segments=(
            DiarizationSegment("SPEAKER_00", 0.0, 2.0, 0.5),
            DiarizationSegment("SPEAKER_00", 3.0, 5.0, 0.9),
            DiarizationSegment("SPEAKER_01", 6.0, 7.0, 0.4),
        ),
        speaker_mappings={"SPEAKER_00": "me"},
        suggestions=(
            TriggerSampleSpeakerSuggestion("a.json", 1, "unknown", "SPEAKER_00", "me", 0.9, 2.0),
            TriggerSampleSpeakerSuggestion("b.json", 2, "unknown", "SPEAKER_01", "unknown", 0.4, 1.0),
        ),
    )

    summary = speaker_cluster_summary(sidecar)

    assert summary["SPEAKER_00"].sample_count == 1
    assert summary["SPEAKER_00"].start_seconds == 0.0
    assert summary["SPEAKER_00"].end_seconds == 5.0
    assert summary["SPEAKER_00"].mapped_label == "me"
    assert summary["SPEAKER_01"].sample_count == 1
    assert summary["SPEAKER_01"].mapped_label == "unknown"


def test_review_speaker_suggestion_accepts_without_losing_original():
    sidecar = DiarizationSessionSidecar(
        profile="personal",
        session_id="daily",
        engine="import",
        model="segments-json",
        created_at="2026-05-20T12:00:00",
        segments=(DiarizationSegment("SPEAKER_00", 0.0, 8.0, 0.91),),
        speaker_mappings={"SPEAKER_00": "me"},
        suggestions=(
            TriggerSampleSpeakerSuggestion(
                "/samples/personal/question/a.json",
                1,
                "unknown",
                "SPEAKER_00",
                "me",
                0.91,
                8.0,
            ),
        ),
    )

    updated, reviewed = review_speaker_suggestion(
        sidecar,
        sample_path="/samples/personal/question/a.json",
        action="accept",
        reviewed_at="2026-05-20T13:00:00",
    )

    assert reviewed.status == "accepted"
    assert reviewed.speaker_id == "SPEAKER_00"
    assert reviewed.suggested_speaker == "me"
    assert reviewed.reviewed_speaker == "me"
    assert reviewed.reviewed_at == "2026-05-20T13:00:00"
    assert updated.suggestions[0] == reviewed


def test_speaker_quality_report_counts_status_confidence_and_conflicts():
    sidecar = DiarizationSessionSidecar(
        profile="personal",
        session_id="daily",
        engine="import",
        model="segments-json",
        created_at="2026-05-20T12:00:00",
        segments=(
            DiarizationSegment("SPEAKER_00", 0.0, 8.0, 0.91),
            DiarizationSegment("SPEAKER_01", 8.0, 16.0, 0.64),
            DiarizationSegment("SPEAKER_02", 16.0, 24.0, 0.32),
        ),
        speaker_mappings={
            "SPEAKER_00": "me",
            "SPEAKER_01": "other",
            "SPEAKER_02": "me",
        },
        suggestions=(
            TriggerSampleSpeakerSuggestion(
                "/samples/personal/question/a.json",
                1,
                "unknown",
                "SPEAKER_00",
                "me",
                0.91,
                8.0,
                status="accepted",
                reviewed_speaker="me",
            ),
            TriggerSampleSpeakerSuggestion(
                "/samples/personal/question/b.json",
                2,
                "unknown",
                "SPEAKER_01",
                "other",
                0.64,
                8.0,
                status="rejected",
            ),
            TriggerSampleSpeakerSuggestion(
                "/samples/personal/question/c.json",
                3,
                "unknown",
                "SPEAKER_02",
                "me",
                0.32,
                8.0,
            ),
        ),
    )

    report = build_speaker_quality_report(
        sidecar,
        sample_speakers={
            "/samples/personal/question/a.json": "me",
            "/samples/personal/question/b.json": "unknown",
            "/samples/personal/question/c.json": "other",
        },
    )
    rendered = render_speaker_quality_report(report)

    assert report.total_suggestions == 3
    assert report.accepted_suggestions == 1
    assert report.rejected_suggestions == 1
    assert report.unknown_speaker_labels == 1
    assert report.confidence_buckets == {"high": 1, "medium": 1, "low": 1}
    assert len(report.conflicts) == 1
    assert report.conflicts[0].sample_name == "c.json"
    assert "accepted suggestions: 1" in rendered
    assert "confidence high: 1" in rendered

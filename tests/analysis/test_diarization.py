"""Tests for optional local diarization helpers."""

import json

from saymo.analysis.diarization import (
    DiarizationConfigView,
    DiarizationResult,
    DiarizationSegment,
    check_diarization_availability,
    diarization_result_from_json,
    diarization_result_to_json,
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

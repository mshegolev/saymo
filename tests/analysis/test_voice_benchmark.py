"""Tests for voice benchmark review and score artifacts."""

from __future__ import annotations

import json
from pathlib import Path


def _records(tmp_path: Path):
    return [
        {
            "engine": "f5tts",
            "phrase_id": 1,
            "text": "PRIVATE GENERATED TEXT IS OK",
            "output_wav": str(tmp_path / "f5tts-01.wav"),
            "latency_ms": 1200,
            "settings": {"dry_run": False, "ref_text_chars": 23},
        },
        {
            "engine": "f5tts",
            "phrase_id": 2,
            "text": "second phrase",
            "output_wav": str(tmp_path / "f5tts-02.wav"),
            "latency_ms": 1600,
            "settings": {"dry_run": False, "ref_text_chars": 23},
        },
    ]


def test_write_review_template_and_score_report_do_not_leak_reference_text(tmp_path):
    from saymo.analysis.voice_benchmark import (
        render_score_report,
        write_benchmark_artifacts,
    )

    records = _records(tmp_path)
    write_benchmark_artifacts(
        tmp_path,
        records,
        expected_clips=2,
        reference_transcript="PRIVATE REFERENCE TRANSCRIPT",
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    review = json.loads((tmp_path / "review.json").read_text(encoding="utf-8"))
    score_report = (tmp_path / "score-report.md").read_text(encoding="utf-8")

    assert manifest["expected_clips"] == 2
    assert manifest["run_status"] == "complete"
    assert review["score_status"] == "unscored"
    assert review["clips"][0]["scores"] == {
        "similarity": None,
        "naturalness": None,
        "russian_pronunciation": None,
        "artifacts": None,
        "call_readiness": None,
    }
    assert "promotion ready: no" in score_report
    assert "run status: complete" in score_report
    assert "score status: unscored" in score_report
    assert "PRIVATE REFERENCE TRANSCRIPT" not in json.dumps(manifest, ensure_ascii=False)
    assert "PRIVATE REFERENCE TRANSCRIPT" not in json.dumps(review, ensure_ascii=False)
    assert "PRIVATE REFERENCE TRANSCRIPT" not in score_report


def test_score_report_marks_partial_run_not_promotion_ready(tmp_path):
    from saymo.analysis.voice_benchmark import write_benchmark_artifacts

    write_benchmark_artifacts(tmp_path, _records(tmp_path)[:1], expected_clips=2)

    report = (tmp_path / "score-report.md").read_text(encoding="utf-8")
    assert "run status: partial" in report
    assert "promotion ready: no" in report


def test_score_report_marks_approved_complete_scored_run(tmp_path):
    from saymo.analysis.voice_benchmark import write_benchmark_artifacts

    write_benchmark_artifacts(tmp_path, _records(tmp_path), expected_clips=2)
    review_path = tmp_path / "review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    for clip in review["clips"]:
        clip["scores"] = {
            "similarity": 5,
            "naturalness": 4,
            "russian_pronunciation": 5,
            "artifacts": 4,
            "call_readiness": 4,
        }
    review["decision"] = "approved"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    write_benchmark_artifacts(tmp_path, _records(tmp_path), expected_clips=2)

    report = (tmp_path / "score-report.md").read_text(encoding="utf-8")
    updated_review = json.loads(review_path.read_text(encoding="utf-8"))
    assert updated_review["score_status"] == "scored"
    assert "score status: scored" in report
    assert "decision: approved" in report
    assert "promotion ready: yes" in report

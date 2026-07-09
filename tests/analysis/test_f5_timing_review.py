"""Tests for privacy-safe F5 timing preview artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from saymo.config import SaymoConfig


def test_write_f5_timing_preview_artifacts_hashes_private_text(tmp_path: Path):
    from saymo.analysis.f5_timing_review import (
        build_f5_timing_record,
        write_f5_timing_preview_artifacts,
    )

    config = SaymoConfig()
    record = build_f5_timing_record(
        config,
        label="candidate",
        preset_id="calm",
        text="PRIVATE MEETING PREVIEW TEXT",
        output_wav=tmp_path / "candidate.wav",
        dry_run=True,
        latency_ms=0,
    )

    run_dir = tmp_path / "run"
    manifest_path = write_f5_timing_preview_artifacts(
        run_dir,
        [record],
        expected_clips=1,
        source_text="PRIVATE MEETING PREVIEW TEXT",
    )

    assert manifest_path == run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert manifest["run_status"] == "dry-run"
    assert manifest["records"][0]["text_sha256"]
    assert manifest["records"][0]["text_chars"] == len("PRIVATE MEETING PREVIEW TEXT")
    assert manifest["records"][0]["timing"]["preset_id"] == "calm"
    assert "PRIVATE MEETING PREVIEW TEXT" not in manifest_text
    assert "PRIVATE MEETING PREVIEW TEXT" not in (run_dir / "review.json").read_text(
        encoding="utf-8"
    )
    assert "PRIVATE MEETING PREVIEW TEXT" not in (run_dir / "timing-report.md").read_text(
        encoding="utf-8"
    )


def test_record_f5_timing_preference_updates_review_and_report(tmp_path: Path):
    from saymo.analysis.f5_timing_review import (
        build_f5_timing_record,
        record_f5_timing_preference,
        write_f5_timing_preview_artifacts,
    )

    config = SaymoConfig()
    run_dir = tmp_path / "run"
    records = [
        build_f5_timing_record(
            config,
            label="current",
            preset_id="approved",
            text="first private text",
            output_wav=run_dir / "current.wav",
            dry_run=True,
            latency_ms=0,
        ),
        build_f5_timing_record(
            config,
            label="candidate",
            preset_id="calm",
            text="second private text",
            output_wav=run_dir / "candidate.wav",
            dry_run=True,
            latency_ms=0,
        ),
    ]
    write_f5_timing_preview_artifacts(run_dir, records, expected_clips=2)

    review = record_f5_timing_preference(
        run_dir,
        preferred="calm",
        notes="Better pauses, less rushed.",
    )

    assert review["preference"]["preferred"] == "calm"
    assert review["recommendation"]["preset_id"] == "calm"
    report = (run_dir / "timing-report.md").read_text(encoding="utf-8")
    assert "recommended preset: calm" in report
    assert "first private text" not in report
    assert "second private text" not in report

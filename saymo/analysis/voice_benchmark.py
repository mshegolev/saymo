"""Voice benchmark artifact helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Mapping


SCORE_KEYS = (
    "similarity",
    "naturalness",
    "russian_pronunciation",
    "artifacts",
    "call_readiness",
)


def write_benchmark_artifacts(
    run_dir: str | Path,
    records: list[Mapping[str, Any]],
    *,
    expected_clips: int,
    reference_transcript: str | None = None,
) -> None:
    """Write manifest, review template, and score report for one run.

    ``reference_transcript`` is intentionally accepted only so callers can pass
    it without the helper leaking the text into artifacts.
    """
    del reference_transcript
    out = Path(run_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    normalized_records = [dict(record) for record in records]
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "expected_clips": expected_clips,
        "run_status": _run_status(normalized_records, expected_clips),
        "records": normalized_records,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    review = _merge_review(out / "review.json", normalized_records)
    review["score_status"] = _score_status(review)
    (out / "review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "score-report.md").write_text(
        render_score_report(manifest, review),
        encoding="utf-8",
    )


def render_score_report(manifest: Mapping[str, Any], review: Mapping[str, Any]) -> str:
    """Render a concise benchmark score report."""
    records = list(manifest.get("records") or [])
    latencies = [
        int(record.get("latency_ms") or 0)
        for record in records
        if int(record.get("latency_ms") or 0) > 0
    ]
    score_status = str(review.get("score_status") or "unscored")
    decision = str(review.get("decision") or "none")
    run_status = str(manifest.get("run_status") or "partial")
    promotion_ready = (
        run_status == "complete"
        and score_status == "scored"
        and decision == "approved"
    )

    lines = [
        "# Voice Benchmark Score Report",
        "",
        f"run status: {run_status}",
        f"score status: {score_status}",
        f"decision: {decision}",
        f"clips: {len(records)}/{int(manifest.get('expected_clips') or len(records))}",
        f"promotion ready: {'yes' if promotion_ready else 'no'}",
        "",
        "## Latency",
        "",
    ]
    if latencies:
        lines.extend(
            [
                f"average latency: {int(mean(latencies))}ms",
                f"max latency: {max(latencies)}ms",
            ]
        )
    else:
        lines.append("average latency: n/a")
    lines.extend(["", "## Clips", ""])
    for record in records:
        lines.append(
            f"- phrase {record.get('phrase_id')}: {record.get('engine')} "
            f"{record.get('latency_ms', 0)}ms `{record.get('output_wav')}`"
        )
    return "\n".join(lines) + "\n"


def _run_status(records: list[Mapping[str, Any]], expected_clips: int) -> str:
    if records and all(record.get("settings", {}).get("dry_run") for record in records):
        return "dry-run"
    if len(records) >= expected_clips:
        return "complete"
    return "partial"


def _merge_review(path: Path, records: list[Mapping[str, Any]]) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    prior_clips = {
        str(clip.get("output_wav")): clip
        for clip in existing.get("clips", [])
        if isinstance(clip, dict)
    }
    clips = []
    for record in records:
        output_wav = str(record.get("output_wav") or "")
        previous = prior_clips.get(output_wav)
        if previous:
            clip = deepcopy(previous)
            clip["phrase_id"] = record.get("phrase_id")
            clip["engine"] = record.get("engine")
            clip["output_wav"] = output_wav
        else:
            clip = {
                "phrase_id": record.get("phrase_id"),
                "engine": record.get("engine"),
                "output_wav": output_wav,
                "scores": {key: None for key in SCORE_KEYS},
                "notes": "",
            }
        clips.append(clip)
    return {
        "version": 1,
        "score_status": "unscored",
        "decision": existing.get("decision") or "none",
        "clips": clips,
    }


def _score_status(review: Mapping[str, Any]) -> str:
    clips = list(review.get("clips") or [])
    if not clips:
        return "unscored"
    for clip in clips:
        scores = clip.get("scores") or {}
        if any(scores.get(key) is None for key in SCORE_KEYS):
            return "unscored"
    return "scored"

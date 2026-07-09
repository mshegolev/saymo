"""Privacy-safe artifacts for F5 timing A/B previews."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from saymo.config import SaymoConfig
from saymo.tts.f5_presets import f5_timing_snapshot


def build_f5_timing_record(
    config: SaymoConfig,
    *,
    label: str,
    preset_id: str,
    text: str,
    output_wav: str | Path,
    dry_run: bool,
    latency_ms: int = 0,
) -> dict[str, Any]:
    """Build one sanitized preview record without storing raw text."""
    return {
        "label": label,
        "preset_id": preset_id,
        "engine": "f5tts_clone",
        "output_wav": str(output_wav),
        "latency_ms": int(latency_ms or 0),
        "text_sha256": _sha256_text(text),
        "text_chars": len(str(text or "")),
        "timing": f5_timing_snapshot(config, preset_id=preset_id),
        "settings": {
            "dry_run": bool(dry_run),
        },
    }


def write_f5_timing_preview_artifacts(
    run_dir: str | Path,
    records: list[Mapping[str, Any]],
    *,
    expected_clips: int,
    source_text: str | None = None,
) -> Path:
    """Write manifest, editable review JSON, and a concise timing report.

    ``source_text`` is accepted so callers can pass it deliberately; it is
    never written to disk.
    """
    del source_text
    out = Path(run_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    normalized_records = [dict(record) for record in records]
    manifest = {
        "version": 1,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "expected_clips": int(expected_clips),
        "run_status": _run_status(normalized_records, int(expected_clips)),
        "records": normalized_records,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    review = _merge_review(out / "review.json", normalized_records)
    (out / "review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "timing-report.md").write_text(
        render_f5_timing_report(manifest, review),
        encoding="utf-8",
    )
    return manifest_path


def record_f5_timing_preference(
    run_dir: str | Path,
    *,
    preferred: str,
    notes: str = "",
) -> dict[str, Any]:
    """Record the user's preferred clip or preset and refresh the report."""
    out = Path(run_dir).expanduser()
    manifest_path = out / "manifest.json"
    review_path = out / "review.json"
    if not manifest_path.exists():
        raise ValueError(f"F5 timing manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    review = (
        json.loads(review_path.read_text(encoding="utf-8"))
        if review_path.exists()
        else _merge_review(review_path, list(manifest.get("records") or []))
    )

    records = list(manifest.get("records") or [])
    match = _match_preferred_record(records, preferred)
    if match is None:
        available = ", ".join(
            sorted(
                {
                    str(record.get("label") or "")
                    for record in records
                    if record.get("label")
                }
                | {
                    str(record.get("preset_id") or "")
                    for record in records
                    if record.get("preset_id")
                }
            )
        )
        raise ValueError(f"Unknown preferred F5 timing choice: {preferred}. Available: {available}")

    recommendation = {
        "preset_id": str(match.get("preset_id") or preferred),
        "label": str(match.get("label") or preferred),
        "timing": dict(match.get("timing") or {}),
    }
    review["score_status"] = "reviewed"
    review["preference"] = {
        "preferred": preferred,
        "notes": notes,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    review["recommendation"] = recommendation
    review_path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "timing-report.md").write_text(
        render_f5_timing_report(manifest, review),
        encoding="utf-8",
    )
    return review


def render_f5_timing_report(
    manifest: Mapping[str, Any],
    review: Mapping[str, Any],
) -> str:
    """Render a short human-readable timing review report."""
    recommendation = dict(review.get("recommendation") or {})
    recommended_preset = str(recommendation.get("preset_id") or "none")
    preference = dict(review.get("preference") or {})
    lines = [
        "# F5 Timing Preview Report",
        "",
        f"run status: {manifest.get('run_status') or 'partial'}",
        f"review status: {review.get('score_status') or 'unscored'}",
        f"preferred: {preference.get('preferred') or 'none'}",
        f"recommended preset: {recommended_preset}",
        "",
        "## Clips",
        "",
    ]
    for record in manifest.get("records") or []:
        timing = dict(record.get("timing") or {})
        lines.append(
            "- "
            f"{record.get('label')}: preset `{record.get('preset_id')}` "
            f"sentence={timing.get('sentence_pause_seconds')}s "
            f"clause={timing.get('clause_pause_seconds')}s "
            f"silent_breath={timing.get('silent_breath_pause_seconds')}s "
            f"`{record.get('output_wav')}`"
        )
    return "\n".join(lines) + "\n"


def _merge_review(path: Path, records: list[Mapping[str, Any]]) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    prior_clips = {
        str(clip.get("label")): clip
        for clip in existing.get("clips", [])
        if isinstance(clip, dict)
    }
    clips = []
    for record in records:
        label = str(record.get("label") or "")
        previous = prior_clips.get(label)
        if previous:
            clip = deepcopy(previous)
            clip["preset_id"] = record.get("preset_id")
            clip["output_wav"] = record.get("output_wav")
        else:
            clip = {
                "label": label,
                "preset_id": record.get("preset_id"),
                "output_wav": record.get("output_wav"),
                "scores": {
                    "pause_naturalness": None,
                    "artifact_cleanliness": None,
                    "call_readiness": None,
                },
                "notes": "",
            }
        clips.append(clip)
    return {
        "version": 1,
        "score_status": existing.get("score_status") or "unscored",
        "preference": existing.get("preference") or {"preferred": "", "notes": ""},
        "recommendation": existing.get("recommendation") or {"preset_id": ""},
        "clips": clips,
    }


def _match_preferred_record(
    records: list[Mapping[str, Any]],
    preferred: str,
) -> Mapping[str, Any] | None:
    needle = str(preferred or "").strip().lower()
    for record in records:
        if str(record.get("preset_id") or "").lower() == needle:
            return record
        if str(record.get("label") or "").lower() == needle:
            return record
    return None


def _run_status(records: list[Mapping[str, Any]], expected_clips: int) -> str:
    if records and all(record.get("settings", {}).get("dry_run") for record in records):
        return "dry-run"
    if len(records) >= expected_clips:
        return "complete"
    return "partial"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()

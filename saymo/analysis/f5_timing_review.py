"""Privacy-safe artifacts for F5 timing A/B previews."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from saymo.analysis.f5_timing_metrics import build_f5_timing_metrics
from saymo.config import SaymoConfig
from saymo.tts.f5_presets import f5_timing_snapshot

_PAUSE_GROUPS = ("sentence", "clause", "paragraph", "silent_breath")


def build_f5_timing_record(
    config: SaymoConfig,
    *,
    label: str,
    preset_id: str,
    text: str,
    output_wav: str | Path,
    dry_run: bool,
    latency_ms: int = 0,
    source_kind: str = "manual",
    corpus_id: str | None = None,
    corpus_category: str | None = None,
    corpus_label: str | None = None,
    audio_duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Build one sanitized preview record without storing raw text."""
    record = {
        "label": label,
        "preset_id": preset_id,
        "source_kind": source_kind,
        "engine": "f5tts_clone",
        "output_wav": str(output_wav),
        "latency_ms": int(latency_ms or 0),
        "text_sha256": _sha256_text(text),
        "text_chars": len(str(text or "")),
        "timing": f5_timing_snapshot(config, preset_id=preset_id),
        "metrics": build_f5_timing_metrics(
            config,
            text=text,
            preset_id=preset_id,
            audio_duration_seconds=audio_duration_seconds,
        ),
        "settings": {
            "dry_run": bool(dry_run),
        },
    }
    if corpus_id is not None:
        record["corpus"] = {
            "id": corpus_id,
            "category": corpus_category,
            "label": corpus_label,
        }
    return record


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
            f"{_format_record_metrics(record.get('metrics'))} "
            f"`{record.get('output_wav')}`"
        )
    lines.extend(["", "## Current vs Candidate Deltas", ""])
    lines.extend(_format_delta_lines(list(manifest.get("records") or [])))
    return "\n".join(lines) + "\n"


def _format_record_metrics(metrics: Any) -> str:
    if not isinstance(metrics, Mapping):
        return "metrics=unavailable"
    duration = _display_duration_seconds(metrics)
    chars_per_second = _metric_float(metrics, "chars_per_second")
    words_per_minute = _metric_float(metrics, "words_per_minute")
    pause_distribution = metrics.get("pause_distribution")
    if (
        duration is None
        or chars_per_second is None
        or words_per_minute is None
        or not isinstance(pause_distribution, Mapping)
    ):
        return "metrics=unavailable"
    pauses = ", ".join(
        _format_pause_group(pause_distribution, group)
        for group in _PAUSE_GROUPS
    )
    return (
        f"duration={duration:.2f}s "
        f"rate={chars_per_second:.2f} chars/s {words_per_minute:.2f} wpm "
        f"pauses={pauses}"
    )


def _format_pause_group(
    pause_distribution: Mapping[str, Any],
    group: str,
) -> str:
    values = pause_distribution.get(group)
    if not isinstance(values, Mapping):
        count = 0
        seconds = 0.0
    else:
        count = int(_metric_float(values, "count") or 0)
        seconds = _metric_float(values, "seconds") or 0.0
    return f"{group} {count}/{seconds:.2f}s"


def _format_delta_lines(records: list[Mapping[str, Any]]) -> list[str]:
    pairs = _current_candidate_pairs(records)
    if not pairs:
        return ["- no complete current/candidate pairs"]

    lines = []
    for key, current, candidate in pairs:
        deltas = _metric_deltas(current.get("metrics"), candidate.get("metrics"))
        if deltas is None:
            lines.append(f"- {key}: metrics=unavailable")
            continue
        lines.append(
            f"- {key}: "
            f"duration_delta={deltas['duration_delta']:+.2f}s "
            f"chars_per_second_delta={deltas['chars_per_second_delta']:+.2f} "
            f"words_per_minute_delta={deltas['words_per_minute_delta']:+.2f} "
            f"pause_total_delta={deltas['pause_total_delta']:+.2f}s"
        )
    return lines


def _current_candidate_pairs(
    records: list[Mapping[str, Any]],
) -> list[tuple[str, Mapping[str, Any], Mapping[str, Any]]]:
    buckets: dict[str, dict[str, Mapping[str, Any]]] = {}
    for record in records:
        role = _record_pair_role(record)
        if role is None:
            continue
        key = _record_pair_key(record)
        buckets.setdefault(key, {})[role] = record

    pairs = []
    for key in sorted(buckets):
        bucket = buckets[key]
        current = bucket.get("current")
        candidate = bucket.get("candidate")
        if current is not None and candidate is not None:
            pairs.append((key, current, candidate))
    return pairs


def _record_pair_key(record: Mapping[str, Any]) -> str:
    corpus = record.get("corpus")
    if isinstance(corpus, Mapping) and corpus.get("id"):
        return str(corpus["id"])
    return "manual"


def _record_pair_role(record: Mapping[str, Any]) -> str | None:
    label = str(record.get("label") or "").lower()
    if label == "current" or label.endswith(":current"):
        return "current"
    if label == "candidate" or label.endswith(":candidate"):
        return "candidate"
    return None


def _metric_deltas(
    current_metrics: Any,
    candidate_metrics: Any,
) -> dict[str, float] | None:
    if not isinstance(current_metrics, Mapping) or not isinstance(candidate_metrics, Mapping):
        return None
    current_duration = _display_duration_seconds(current_metrics)
    candidate_duration = _display_duration_seconds(candidate_metrics)
    current_chars_per_second = _metric_float(current_metrics, "chars_per_second")
    candidate_chars_per_second = _metric_float(candidate_metrics, "chars_per_second")
    current_words_per_minute = _metric_float(current_metrics, "words_per_minute")
    candidate_words_per_minute = _metric_float(candidate_metrics, "words_per_minute")
    if (
        current_duration is None
        or candidate_duration is None
        or current_chars_per_second is None
        or candidate_chars_per_second is None
        or current_words_per_minute is None
        or candidate_words_per_minute is None
    ):
        return None

    return {
        "duration_delta": candidate_duration - current_duration,
        "chars_per_second_delta": candidate_chars_per_second - current_chars_per_second,
        "words_per_minute_delta": candidate_words_per_minute - current_words_per_minute,
        "pause_total_delta": (
            _pause_total_seconds(candidate_metrics) - _pause_total_seconds(current_metrics)
        ),
    }


def _display_duration_seconds(metrics: Mapping[str, Any]) -> float | None:
    audio_duration = _metric_float(metrics, "audio_duration_seconds")
    if audio_duration is not None:
        return audio_duration
    return _metric_float(metrics, "estimated_total_duration_seconds")


def _pause_total_seconds(metrics: Mapping[str, Any]) -> float:
    pause_distribution = metrics.get("pause_distribution")
    if not isinstance(pause_distribution, Mapping):
        return 0.0
    total = 0.0
    for group in _PAUSE_GROUPS:
        values = pause_distribution.get(group)
        if isinstance(values, Mapping):
            total += _metric_float(values, "seconds") or 0.0
    return total


def _metric_float(metrics: Mapping[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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

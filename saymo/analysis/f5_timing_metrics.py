"""Deterministic, privacy-safe F5 timing metrics."""

from __future__ import annotations

import re
from typing import Any

from saymo.config import F5TTSConfig, SaymoConfig
from saymo.tts.f5_presets import f5_timing_snapshot
from saymo.tts.naturalness import prepare_for_natural_pacing, split_for_tts

_PAUSE_GROUPS = ("sentence", "clause", "paragraph", "silent_breath")
_DRY_RUN_CHARS_PER_SECOND = 14.0
_MIN_DISPLAY_DURATION_SECONDS = 0.01


def build_f5_timing_metrics(
    config: SaymoConfig | F5TTSConfig,
    *,
    text: str,
    preset_id: str | None = None,
    audio_duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Build JSON-safe timing metrics without storing raw source text."""
    timing = f5_timing_snapshot(config, preset_id=preset_id)
    chunks = split_for_tts(
        prepare_for_natural_pacing(
            text,
            clause_pause_seconds=float(timing["clause_pause_seconds"]),
        )
    )
    spoken_chunks, pause_distribution = _walk_f5_timing_chunks(chunks, timing)
    spoken_text = " ".join(spoken_chunks)
    spoken_chars = len(spoken_text)
    spoken_words = len(re.findall(r"\w+", spoken_text, flags=re.UNICODE))

    f5_speed = _positive_float(getattr(_resolve_f5_config(config), "speed", 1.0), 1.0)
    spoken_duration = spoken_chars / (_DRY_RUN_CHARS_PER_SECOND * f5_speed)
    total_pause_seconds = sum(group["seconds"] for group in pause_distribution.values())
    estimated_total_duration_seconds = _round_seconds(
        max(0.0, spoken_duration + total_pause_seconds)
    )
    measured_duration = (
        _round_seconds(max(0.0, float(audio_duration_seconds)))
        if audio_duration_seconds is not None
        else None
    )
    display_duration = measured_duration
    if display_duration is None:
        display_duration = estimated_total_duration_seconds
    display_duration = max(float(display_duration), _MIN_DISPLAY_DURATION_SECONDS)

    return {
        "estimated_total_duration_seconds": estimated_total_duration_seconds,
        "audio_duration_seconds": measured_duration,
        "spoken_chars": spoken_chars,
        "spoken_words": spoken_words,
        "chars_per_second": _round_rate(spoken_chars / display_duration),
        "words_per_minute": _round_rate((spoken_words / display_duration) * 60),
        "pause_distribution": pause_distribution,
    }


def _walk_f5_timing_chunks(
    chunks: list[str | float],
    timing: dict[str, Any],
) -> tuple[list[str], dict[str, dict[str, int | float]]]:
    distribution = {
        group: {"count": 0, "seconds": 0.0}
        for group in _PAUSE_GROUPS
    }
    spoken_chunks: list[str] = []
    spoken_since_breath = 0
    sentence_pause = max(0.0, float(timing["sentence_pause_seconds"]))
    paragraph_pause = max(0.0, float(timing["paragraph_pause_seconds"]))
    silent_breath_pause = max(0.0, float(timing["silent_breath_pause_seconds"]))
    breath_interval = max(0, int(timing["breath_interval_sentences"] or 0))

    for idx, chunk in enumerate(chunks):
        if isinstance(chunk, float):
            _add_pause(distribution, "clause", max(0.0, float(chunk)))
            continue
        if chunk == "":
            _add_pause(distribution, "paragraph", paragraph_pause)
            spoken_since_breath = 0
            continue

        spoken_chunks.append(chunk)
        spoken_since_breath += 1
        if _next_chunk_is_adjacent_speech(chunks, idx):
            if breath_interval and spoken_since_breath >= breath_interval:
                _add_pause(distribution, "silent_breath", silent_breath_pause)
                spoken_since_breath = 0
            else:
                _add_pause(distribution, "sentence", sentence_pause)

    for group in _PAUSE_GROUPS:
        distribution[group]["seconds"] = _round_seconds(distribution[group]["seconds"])
    return spoken_chunks, distribution


def _add_pause(
    distribution: dict[str, dict[str, int | float]],
    group: str,
    seconds: float,
) -> None:
    distribution[group]["count"] = int(distribution[group]["count"]) + 1
    distribution[group]["seconds"] = float(distribution[group]["seconds"]) + seconds


def _next_chunk_is_adjacent_speech(chunks: list[str | float], idx: int) -> bool:
    for later in chunks[idx + 1 :]:
        if isinstance(later, float):
            return False
        if later == "":
            return False
        return True
    return False


def _resolve_f5_config(config: SaymoConfig | F5TTSConfig) -> F5TTSConfig:
    if isinstance(config, F5TTSConfig):
        return config
    return config.tts.f5tts


def _positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _round_seconds(value: float) -> float:
    return round(float(value), 2)


def _round_rate(value: float) -> float:
    return round(float(value), 2)

"""Tests for privacy-safe F5 timing metrics."""

from __future__ import annotations

import json

from saymo.config import F5TTSConfig
from saymo.analysis.f5_timing_metrics import build_f5_timing_metrics


def test_f5_timing_metrics_are_json_safe_and_sanitized():
    text = "Private source phrase. It should be summarized only."

    metrics = build_f5_timing_metrics(F5TTSConfig(), text=text)

    assert metrics["estimated_total_duration_seconds"] > 0
    assert metrics["audio_duration_seconds"] is None
    assert metrics["spoken_chars"] > 0
    assert metrics["spoken_words"] > 0
    assert metrics["chars_per_second"] > 0
    assert metrics["words_per_minute"] > 0
    assert set(metrics["pause_distribution"]) == {
        "sentence",
        "clause",
        "paragraph",
        "silent_breath",
    }
    for group in metrics["pause_distribution"].values():
        assert set(group) == {"count", "seconds"}
        assert isinstance(group["count"], int)
        assert isinstance(group["seconds"], float)

    encoded = json.dumps(metrics, sort_keys=True)
    assert "Private source phrase" not in encoded
    assert "summarized only" not in encoded


def test_f5_timing_metrics_count_pause_distribution_from_natural_pacing():
    metrics = build_f5_timing_metrics(
        F5TTSConfig(),
        text="One. Two. Three.\n\nFour - five.",
    )

    assert metrics["pause_distribution"] == {
        "sentence": {"count": 1, "seconds": 0.38},
        "clause": {"count": 1, "seconds": 0.18},
        "paragraph": {"count": 1, "seconds": 0.6},
        "silent_breath": {"count": 1, "seconds": 0.6},
    }


def test_f5_timing_metrics_round_seconds_and_rates_to_two_decimals():
    metrics = build_f5_timing_metrics(
        F5TTSConfig(speed=0.9),
        text="One. Two.",
        audio_duration_seconds=1.234,
    )

    assert metrics["audio_duration_seconds"] == 1.23
    assert metrics["estimated_total_duration_seconds"] == round(
        metrics["estimated_total_duration_seconds"], 2
    )
    assert metrics["chars_per_second"] == round(metrics["chars_per_second"], 2)
    assert metrics["words_per_minute"] == round(metrics["words_per_minute"], 2)
    for group in metrics["pause_distribution"].values():
        assert group["seconds"] == round(group["seconds"], 2)

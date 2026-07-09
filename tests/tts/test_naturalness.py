"""Tests for reusable TTS naturalness helpers."""

from __future__ import annotations

from saymo.tts.naturalness import prepare_for_natural_pacing, split_for_tts


def test_prepare_for_natural_pacing_marks_high_confidence_clause_boundaries():
    text = "Первое — отчёт; второе: запуск в 10:30, без задержек."

    prepared = prepare_for_natural_pacing(text, clause_pause_seconds=0.18)

    assert prepared == (
        "Первое [pause:0.18] отчёт [pause:0.18] второе "
        "[pause:0.18] запуск в 10:30, без задержек."
    )
    assert split_for_tts(prepared) == [
        "Первое",
        0.18,
        "отчёт",
        0.18,
        "второе",
        0.18,
        "запуск в 10:30, без задержек.",
    ]


def test_prepare_for_natural_pacing_preserves_explicit_pause_markers():
    text = "Сначала коротко. [pause:1.2] Потом продолжаю."

    prepared = prepare_for_natural_pacing(text, clause_pause_seconds=0.18)

    assert "[pause:1.2]" in prepared
    assert split_for_tts(prepared) == [
        "Сначала коротко.",
        1.2,
        "Потом продолжаю.",
    ]

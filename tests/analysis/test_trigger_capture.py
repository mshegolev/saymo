"""Tests for trigger-capture sample classification and persistence."""

import json

import numpy as np
import soundfile as sf

from saymo.analysis.trigger_capture import (
    classify_trigger_sample,
    save_trigger_sample,
)


def test_classifies_addressed_trigger_as_asked_to_speak():
    sample = classify_trigger_sample(
        "John, what is the status?",
        trigger_phrases=["John"],
        rms=0.04,
        peak=0.4,
    )

    assert sample.category == "asked_to_speak"
    assert sample.speaker == "unknown"
    assert sample.trigger is True
    assert sample.question is True
    assert sample.will_answer is True
    assert sample.addressing == "addressed_to_me"


def test_classifies_direct_request_to_speak_as_asked_to_speak():
    sample = classify_trigger_sample(
        "John, please tell us about your blockers",
        trigger_phrases=["John"],
        rms=0.04,
        peak=0.4,
    )

    assert sample.category == "asked_to_speak"
    assert sample.trigger is True
    assert sample.will_answer is True


def test_classifies_general_question_without_trigger_as_question():
    sample = classify_trigger_sample(
        "Does anyone have questions?",
        trigger_phrases=["John"],
        rms=0.04,
        peak=0.4,
    )

    assert sample.category == "question"
    assert sample.trigger is False
    assert sample.question is True
    assert sample.will_answer is False
    assert sample.addressing == "no_trigger"


def test_classifies_non_question_speech_as_speech():
    sample = classify_trigger_sample(
        "Thanks everyone, have a good weekend.",
        trigger_phrases=["John"],
        rms=0.04,
        peak=0.4,
    )

    assert sample.category == "speech"
    assert sample.trigger is False
    assert sample.question is False


def test_classifies_empty_low_signal_as_silence():
    sample = classify_trigger_sample(
        "",
        trigger_phrases=["John"],
        rms=0.0,
        peak=0.0,
    )

    assert sample.category == "silence"
    assert sample.trigger is False
    assert sample.question is False


def test_save_trigger_sample_writes_wav_and_metadata_under_category(tmp_path):
    audio = np.zeros(1600, dtype=np.float32)
    sample = classify_trigger_sample(
        "Does anyone have questions?",
        trigger_phrases=["John"],
        rms=0.04,
        peak=0.4,
    )

    wav_path, meta_path = save_trigger_sample(
        audio,
        sample_rate=16000,
        sample=sample,
        base_dir=tmp_path,
        profile="daily",
        sequence=7,
        created_at="2026-05-15T19:20:00",
    )

    assert wav_path.parent == tmp_path / "daily" / "question"
    assert meta_path.parent == wav_path.parent
    assert wav_path.exists()
    assert meta_path.exists()
    assert sf.info(str(wav_path)).samplerate == 16000

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    assert metadata["profile"] == "daily"
    assert metadata["category"] == "question"
    assert metadata["speaker"] == "unknown"
    assert metadata["transcript"] == "Does anyone have questions?"
    assert metadata["wav"] == wav_path.name

"""Tests for F5 pause preset catalog helpers."""

from __future__ import annotations

import pytest

from saymo.config import SaymoConfig


def test_f5_pause_preset_catalog_includes_approved_defaults():
    from saymo.tts.f5_presets import get_f5_pause_preset, list_f5_pause_presets

    names = [preset.id for preset in list_f5_pause_presets()]

    assert names == ["approved", "crisp", "calm", "deliberate"]
    approved = get_f5_pause_preset("approved")
    assert approved.sentence_pause_seconds == pytest.approx(0.38)
    assert approved.clause_pause_seconds == pytest.approx(0.18)
    assert approved.silent_breath_pause_seconds == pytest.approx(0.60)
    assert approved.paragraph_pause_seconds == pytest.approx(0.60)
    assert approved.breath_interval_sentences == 2


def test_apply_f5_pause_preset_updates_config_timing_knobs():
    from saymo.tts.f5_presets import apply_f5_pause_preset

    config = SaymoConfig()
    preset = apply_f5_pause_preset(config, "deliberate")

    assert preset.id == "deliberate"
    assert config.tts.f5tts.pause_preset == "deliberate"
    assert config.tts.f5tts.sentence_pause_seconds == pytest.approx(0.55)
    assert config.tts.f5tts.clause_pause_seconds == pytest.approx(0.28)
    assert config.tts.f5tts.silent_breath_pause_seconds == pytest.approx(0.85)
    assert config.tts.f5tts.breath_interval_sentences == 2


def test_unknown_f5_pause_preset_raises_clear_error():
    from saymo.tts.f5_presets import get_f5_pause_preset

    with pytest.raises(ValueError, match="Unknown F5 pause preset"):
        get_f5_pause_preset("robot")

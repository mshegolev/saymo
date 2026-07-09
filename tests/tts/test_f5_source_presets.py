"""Tests for F5 pause preset source-type resolution."""

from __future__ import annotations

import copy

import pytest

from saymo.config import SaymoConfig
from saymo.tts.f5_presets import (
    config_with_f5_pause_preset_for_source,
    f5_source_type_for_purpose,
    normalize_f5_source_type,
    resolve_f5_pause_preset_for_source,
)


def _config_with_meetings(
    *,
    global_preset: str = "approved",
    meetings: dict | None = None,
) -> SaymoConfig:
    config = SaymoConfig()
    config.tts.f5tts.pause_preset = global_preset
    config.meetings = meetings or {}
    return config


def test_normalize_f5_source_type_trims_and_accepts_only_known_values():
    assert normalize_f5_source_type(" prepared ") == "prepared"
    assert normalize_f5_source_type("response_cache") == "response_cache"
    assert normalize_f5_source_type("spontaneous") == "spontaneous"
    assert normalize_f5_source_type(None) == "spontaneous"

    with pytest.raises(ValueError) as excinfo:
        normalize_f5_source_type("cache")

    message = str(excinfo.value)
    assert "Unknown F5 source type" in message
    assert "prepared" in message
    assert "response_cache" in message
    assert "spontaneous" in message


def test_f5_source_type_for_purpose_maps_existing_selector_purposes():
    assert f5_source_type_for_purpose("prepare") == "prepared"
    assert f5_source_type_for_purpose("response_cache") == "response_cache"
    assert f5_source_type_for_purpose("preview") == "spontaneous"
    assert f5_source_type_for_purpose("live_call") is None


def test_resolve_f5_pause_preset_for_source_uses_profile_source_override():
    config = _config_with_meetings(
        meetings={
            "standup": {
                "voice": {
                    "f5_pause_preset": "crisp",
                    "f5_pause_presets": {"prepared": "calm"},
                }
            }
        }
    )

    resolution = resolve_f5_pause_preset_for_source(
        config,
        profile="standup",
        source_type="prepared",
    )

    assert config.get_meeting("standup").voice["f5_pause_presets"]["prepared"] == "calm"
    assert resolution.profile == "standup"
    assert resolution.source_type == "prepared"
    assert resolution.purpose == "prepare"
    assert resolution.profile_preset_id == "crisp"
    assert resolution.override_preset_id == "calm"
    assert resolution.resolved_preset_id == "calm"
    assert resolution.preset.id == "calm"


def test_resolve_f5_pause_preset_for_source_falls_back_to_profile_preset():
    config = _config_with_meetings(
        meetings={
            "standup": {
                "voice": {
                    "f5_pause_preset": "crisp",
                    "f5_pause_presets": {"prepared": "calm"},
                }
            }
        }
    )

    resolution = resolve_f5_pause_preset_for_source(
        config,
        profile="standup",
        source_type="response_cache",
    )

    assert resolution.source_type == "response_cache"
    assert resolution.purpose == "response_cache"
    assert resolution.profile_preset_id == "crisp"
    assert resolution.override_preset_id == ""
    assert resolution.resolved_preset_id == "crisp"


def test_resolve_f5_pause_preset_for_source_falls_back_to_global_preset():
    config = _config_with_meetings(
        global_preset="deliberate",
        meetings={"standup": {"voice": {"f5_pause_presets": {}}}},
    )

    resolution = resolve_f5_pause_preset_for_source(
        config,
        profile="standup",
        source_type="prepared",
    )

    assert resolution.profile_preset_id == ""
    assert resolution.override_preset_id == ""
    assert resolution.resolved_preset_id == "deliberate"
    assert resolution.preset.id == "deliberate"


def test_config_with_f5_pause_preset_for_source_returns_copy_without_mutating_original():
    config = _config_with_meetings(
        meetings={
            "standup": {
                "voice": {
                    "f5_pause_preset": "crisp",
                    "f5_pause_presets": {"prepared": "calm"},
                }
            }
        }
    )
    original = copy.deepcopy(config)

    updated, resolution = config_with_f5_pause_preset_for_source(
        config,
        profile="standup",
        source_type="prepared",
    )

    assert updated is not config
    assert resolution.resolved_preset_id == "calm"
    assert updated.tts.f5tts.pause_preset == "calm"
    assert updated.tts.f5tts.sentence_pause_seconds == 0.44
    assert updated.tts.f5tts.clause_pause_seconds == 0.22
    assert config.tts.f5tts.pause_preset == original.tts.f5tts.pause_preset
    assert config.tts.f5tts.sentence_pause_seconds == original.tts.f5tts.sentence_pause_seconds
    assert config.meetings == original.meetings

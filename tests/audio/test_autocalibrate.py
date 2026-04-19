"""Tests for the autocalibration grid search + verdict."""

import numpy as np
import pytest

from saymo.audio.autocalibrate import (
    AutoCalibrationVerdict,
    CalibrationTargets,
    autocalibrate,
)


SR = 22050


def _sine(freq_hz: float, seconds: float, amp: float) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def _noise(seconds: float, amp: float) -> np.ndarray:
    return (np.random.RandomState(0).randn(int(seconds * SR)) * amp).astype(np.float32)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_clean_room_normal_voice_is_excellent_or_good():
    """Quiet room + properly-leveled voice → verdict at least 'good'."""
    noise = _noise(3.0, amp=0.0005)  # very quiet room
    # amp ≈ 0.13 → peak ≈ -17 dB, rms ≈ -20 dB — already in the target band.
    voice = _sine(300, 5.0, amp=0.13)
    verdict = autocalibrate(noise, voice, SR)
    assert verdict.quality in {"excellent", "good"}
    assert not verdict.actionable()
    assert verdict.settings["input_gain_db"] <= 6.0  # small tweak at most


def test_too_quiet_voice_flags_rerecord_with_sys_volume_hint():
    """Voice far below target even at max software gain → needs_rerecord
    with a positive system-volume recommendation."""
    noise = _noise(3.0, amp=0.0005)
    voice = _sine(300, 5.0, amp=0.005)  # very quiet
    verdict = autocalibrate(noise, voice, SR)
    assert verdict.quality == "needs_rerecord"
    assert verdict.actionable()
    assert 0.0 < (verdict.system_volume_recommendation or 0.0) <= 0.35
    assert verdict.settings["input_gain_db"] == 15.0  # cap hit


def test_noisy_room_triggers_snr_warning():
    noise = _noise(3.0, amp=0.05)  # loud room
    voice = _sine(300, 5.0, amp=0.1)
    verdict = autocalibrate(noise, voice, SR)
    assert any("snr" in w.lower() or "noise" in w.lower() for w in verdict.warnings)


def test_clipping_input_is_warned():
    noise = _noise(3.0, amp=0.0005)
    voice = _sine(300, 5.0, amp=0.99)  # clipped peaks
    verdict = autocalibrate(noise, voice, SR)
    assert any("clip" in w.lower() for w in verdict.warnings)


# ---------------------------------------------------------------------------
# Settings shape + determinism
# ---------------------------------------------------------------------------


def test_settings_keys_match_config_yaml_block():
    voice = _sine(300, 2.0, amp=0.15)
    noise = _noise(2.0, amp=0.001)
    verdict = autocalibrate(noise, voice, SR)
    assert set(verdict.settings.keys()) == {
        "input_gain_db",
        "noise_gate_db",
        "highpass_cutoff_hz",
        "noise_reduction",
    }
    assert isinstance(verdict.settings["noise_reduction"], bool)


def test_yaml_snippet_contains_audio_header():
    verdict = autocalibrate(
        _noise(1.0, amp=0.001), _sine(300, 2.0, amp=0.15), SR
    )
    snippet = verdict.yaml_snippet()
    assert snippet.splitlines()[0] == "audio:"
    assert "input_gain_db:" in snippet


def test_autocalibrate_is_deterministic_on_same_input():
    """Twice the same buffers → twice the same settings."""
    noise = _noise(2.0, amp=0.001)
    voice = _sine(300, 3.0, amp=0.15)
    a = autocalibrate(noise, voice, SR)
    b = autocalibrate(noise, voice, SR)
    assert a.settings == b.settings
    assert a.quality == b.quality


# ---------------------------------------------------------------------------
# Targets override
# ---------------------------------------------------------------------------


def test_custom_targets_affect_verdict():
    noise = _noise(1.0, amp=0.001)
    voice = _sine(300, 2.0, amp=0.15)
    loose = CalibrationTargets(
        voice_rms_db=(-30.0, -10.0),
        voice_peak_db=(-12.0, 0.0),
        min_snr_db=15.0,
        excellent_snr_db=25.0,
    )
    verdict = autocalibrate(noise, voice, SR, targets=loose)
    assert isinstance(verdict, AutoCalibrationVerdict)
    # Wider targets should mean the result is at least 'good'.
    assert verdict.quality in {"excellent", "good"}


# ---------------------------------------------------------------------------
# High-pass heuristic
# ---------------------------------------------------------------------------


def test_lowfreq_noise_triggers_highpass():
    """Low-frequency rumble noise + clean mid-band voice → highpass on."""
    rumble = _sine(40, 3.0, amp=0.01)  # noise dominated by 40 Hz
    voice = _sine(300, 3.0, amp=0.15)
    verdict = autocalibrate(rumble, voice, SR)
    assert verdict.settings["highpass_cutoff_hz"] == 80.0


def test_broadband_noise_leaves_highpass_off():
    noise = _noise(3.0, amp=0.01)
    voice = _sine(300, 3.0, amp=0.15)
    verdict = autocalibrate(noise, voice, SR)
    # White noise has most of its energy above 120 Hz at 22050 Hz SR.
    assert verdict.settings["highpass_cutoff_hz"] == 0.0

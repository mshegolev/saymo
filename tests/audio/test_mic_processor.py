"""Tests for the mic input chain (gain, gate, high-pass, denoise)."""

import numpy as np
import pytest

from saymo.audio.mic_processor import (
    AudioMeter,
    MicProcessor,
    apply_gain,
    apply_highpass,
    apply_noise_gate,
    db_to_linear,
    peak_db,
    recommend_calibration,
    rms_db,
)


SR = 22050


def _sine(freq_hz: float, seconds: float, amp: float = 0.5, sr: int = SR) -> np.ndarray:
    t = np.arange(int(seconds * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def test_db_to_linear_roundtrip():
    assert db_to_linear(0.0) == pytest.approx(1.0)
    assert db_to_linear(6.0) == pytest.approx(1.9953, rel=1e-3)
    assert db_to_linear(-6.0) == pytest.approx(0.5012, rel=1e-3)


def test_rms_db_matches_known_signal():
    """A full-scale sine has RMS ≈ -3 dB relative to its peak."""
    sig = _sine(1000, 1.0, amp=1.0)
    # Exact RMS of a unit-amplitude sine is 1/sqrt(2) ≈ -3.01 dB
    assert rms_db(sig) == pytest.approx(-3.01, abs=0.05)


def test_peak_db_matches_amplitude():
    sig = _sine(1000, 1.0, amp=0.5)
    # 0.5 linear == -6.02 dBFS peak
    assert peak_db(sig) == pytest.approx(-6.02, abs=0.05)


def test_apply_gain_adds_db():
    sig = _sine(440, 0.2, amp=0.1)
    before = rms_db(sig)
    after = rms_db(apply_gain(sig, 6.0))
    assert after - before == pytest.approx(6.0, abs=0.1)


def test_apply_gain_clips_to_unit():
    """Huge gain must not overflow beyond [-1, 1]."""
    sig = _sine(440, 0.2, amp=0.5)
    hot = apply_gain(sig, 60.0)
    assert float(np.max(np.abs(hot))) <= 1.0


def test_apply_gain_zero_is_identity():
    sig = _sine(440, 0.2, amp=0.2)
    out = apply_gain(sig, 0.0)
    assert out is sig or np.array_equal(out, sig)


def test_noise_gate_silences_quiet_frames():
    """Sine at -40 dB gated at -30 dB should become silence."""
    quiet = _sine(440, 0.5, amp=0.01)  # ≈ -43 dB RMS
    gated = apply_noise_gate(quiet, threshold_db=-30.0, sample_rate=SR)
    assert rms_db(gated) < -100  # essentially silent


def test_noise_gate_passes_loud_frames():
    """Loud sine well above threshold must be unaffected."""
    loud = _sine(440, 0.5, amp=0.5)
    gated = apply_noise_gate(loud, threshold_db=-40.0, sample_rate=SR)
    assert rms_db(gated) == pytest.approx(rms_db(loud), abs=0.5)


def test_highpass_attenuates_dc():
    """DC offset must be almost fully removed by an 80 Hz high-pass."""
    sig = np.full(SR, 0.5, dtype=np.float32)
    out = apply_highpass(sig, cutoff_hz=80.0, sample_rate=SR)
    # Skip filter ring-in region
    tail = out[SR // 4 :]
    assert float(np.mean(np.abs(tail))) < 0.01


def test_highpass_preserves_high_frequencies():
    """A 1 kHz sine should survive an 80 Hz high-pass nearly intact."""
    sig = _sine(1000, 0.5, amp=0.5)
    out = apply_highpass(sig, cutoff_hz=80.0, sample_rate=SR)
    # Skip transient at the start.
    in_rms = rms_db(sig[SR // 4 :])
    out_rms = rms_db(out[SR // 4 :])
    assert abs(in_rms - out_rms) < 1.0


def test_highpass_noop_when_cutoff_zero():
    sig = _sine(500, 0.2, amp=0.3)
    out = apply_highpass(sig, cutoff_hz=0.0, sample_rate=SR)
    assert np.array_equal(out, sig)


# ---------------------------------------------------------------------------
# MicProcessor
# ---------------------------------------------------------------------------


def test_mic_processor_noop_by_default():
    p = MicProcessor(sample_rate=SR)
    assert p.is_noop()
    sig = _sine(440, 0.2, amp=0.2)
    out = p.process(sig)
    assert np.array_equal(out, sig)


def test_mic_processor_applies_gain():
    p = MicProcessor(sample_rate=SR, gain_db=6.0)
    assert not p.is_noop()
    sig = _sine(440, 0.2, amp=0.1)
    out = p.process(sig)
    assert rms_db(out) - rms_db(sig) == pytest.approx(6.0, abs=0.1)


def test_mic_processor_silence_stays_silent():
    p = MicProcessor(sample_rate=SR, gain_db=12.0, noise_gate_db=-60)
    silence = np.zeros(SR // 2, dtype=np.float32)
    out = p.process(silence)
    assert np.all(out == 0.0)


def test_mic_processor_records_stats():
    p = MicProcessor(sample_rate=SR, gain_db=3.0)
    sig = _sine(440, 0.2, amp=0.2)
    p.process(sig)
    assert p.last_stats is not None
    assert p.last_stats.rms_out_db - p.last_stats.rms_in_db == pytest.approx(3.0, abs=0.1)


def test_mic_processor_process_int16_roundtrip():
    p = MicProcessor(sample_rate=SR, gain_db=0.0)
    buf = (np.random.randn(1000) * 1000).astype(np.int16)
    out = p.process_int16(buf)
    assert out.dtype == np.int16
    assert out.shape == buf.shape


def test_mic_processor_from_config_reads_audio_config():
    class FakeAudio:
        sample_rate = SR
        input_gain_db = 3.0
        noise_gate_db = -50.0
        highpass_cutoff_hz = 80.0
        noise_reduction = False
        noise_reduction_strength = 0.5

    p = MicProcessor.from_config(FakeAudio())
    assert p.gain_db == 3.0
    assert p.noise_gate_db == -50.0
    assert p.highpass_cutoff_hz == 80.0
    assert not p.is_noop()


# ---------------------------------------------------------------------------
# Soft dependency on noisereduce
# ---------------------------------------------------------------------------


def test_denoise_falls_back_when_lib_missing(monkeypatch):
    """When the soft dep is not installed, enabling denoise logs and
    returns pass-through — Saymo keeps running on a bare CPU-only install."""
    from saymo.audio import mic_processor as m

    monkeypatch.setattr(m, "HAS_NOISEREDUCE", False)
    monkeypatch.setattr(m, "_noisereduce", None)
    sig = _sine(500, 0.2, amp=0.3)
    out = m.apply_spectral_denoise(sig, sample_rate=SR, strength=0.5)
    assert np.array_equal(out, sig)


# ---------------------------------------------------------------------------
# Meter + calibration advisor
# ---------------------------------------------------------------------------


def test_audio_meter_tracks_levels():
    meter = AudioMeter(window_ms=200.0, sample_rate=SR)
    meter.push(_sine(440, 0.3, amp=0.5))
    assert meter.rms_db() == pytest.approx(-9.03, abs=0.5)


def test_recommend_calibration_happy_path():
    """Clean quiet room + normal voice → small gain up, gate above noise floor."""
    noise = (np.random.randn(SR) * 0.001).astype(np.float32)  # ≈ -60 dB
    voice = _sine(300, 2.0, amp=0.2)  # ≈ -17 dB
    result = recommend_calibration(noise, voice)
    assert -12 <= result.suggested_gain_db <= 12
    assert result.suggested_gate_db > result.noise_floor_db
    assert result.voice_rms_db - result.noise_floor_db > 20


def test_recommend_calibration_warns_on_clipping():
    noise = np.zeros(SR, dtype=np.float32)
    voice = _sine(300, 1.0, amp=0.99)  # peak essentially 0 dB
    result = recommend_calibration(noise, voice)
    assert result.clipping
    assert any("clip" in w.lower() for w in result.warnings)


def test_yaml_snippet_has_required_fields():
    noise = (np.random.randn(SR) * 0.001).astype(np.float32)
    voice = _sine(300, 1.0, amp=0.3)
    result = recommend_calibration(noise, voice)
    snippet = result.yaml_snippet()
    assert "audio:" in snippet
    assert "input_gain_db:" in snippet
    assert "noise_gate_db:" in snippet

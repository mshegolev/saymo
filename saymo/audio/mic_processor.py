"""Microphone input processing: gain, noise gate, high-pass filter, denoise.

Used by both offline capture (``saymo record-voice``, ``saymo train-prepare``)
and live capture (``saymo auto``). Processing is tunable through
``config.audio.*`` so the user can calibrate for their room and mic without
editing source; the ``saymo mic-check`` wizard writes a ready-to-paste YAML
snippet.

Design rules:

- Pure numpy / scipy on the fast path. ``noisereduce`` is an **optional**
  dependency — if it is not installed, setting
  ``config.audio.noise_reduction: true`` logs a warning and falls back to
  pass-through. Saymo's ``Local by default`` / CPU-only guarantee holds.
- All operations accept and return ``float32`` samples in ``[-1, 1]``. The
  recorder converts to/from ``int16`` at the edges.
- ``MicProcessor.process`` is idempotent on silence: pure zero input stays
  zero output, so silence trimming downstream is not confused.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger("saymo.audio.mic")

# Soft dependency — used only when ``noise_reduction`` is enabled.
try:
    import noisereduce as _noisereduce  # type: ignore

    HAS_NOISEREDUCE = True
except ImportError:  # pragma: no cover - environment-dependent
    _noisereduce = None
    HAS_NOISEREDUCE = False


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def db_to_linear(db: float) -> float:
    """Convert a dB gain value to a linear amplitude multiplier."""
    return float(10.0 ** (db / 20.0))


def rms_db(audio: np.ndarray, eps: float = 1e-10) -> float:
    """Return the RMS level of ``audio`` in dBFS.

    ``eps`` prevents ``-inf`` for digital silence — callers typically see
    numbers like ``-85 dB`` for a quiet mic even in silence.
    """
    if audio.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(audio.astype(np.float32)))) + eps)
    return 20.0 * np.log10(rms)


def peak_db(audio: np.ndarray, eps: float = 1e-10) -> float:
    """Return the peak sample level in dBFS."""
    if audio.size == 0:
        return -120.0
    peak = float(np.max(np.abs(audio)) + eps)
    return 20.0 * np.log10(peak)


def apply_gain(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """Multiply ``audio`` by ``10^(gain_db/20)``, clipping to [-1, 1]."""
    if gain_db == 0.0:
        return audio
    out = audio.astype(np.float32) * db_to_linear(gain_db)
    return np.clip(out, -1.0, 1.0)


def apply_noise_gate(
    audio: np.ndarray,
    threshold_db: float,
    frame_ms: float = 20.0,
    sample_rate: int = 22050,
) -> np.ndarray:
    """Zero out frames whose RMS is below ``threshold_db``.

    Framed gate (20 ms default) rather than per-sample — per-sample gating
    introduces crackle at word boundaries.
    """
    if audio.size == 0:
        return audio
    frame_len = max(1, int(sample_rate * frame_ms / 1000.0))
    threshold_linear = db_to_linear(threshold_db)
    out = audio.astype(np.float32).copy()
    for start in range(0, len(out), frame_len):
        end = min(len(out), start + frame_len)
        frame = out[start:end]
        if frame.size == 0:
            continue
        rms = float(np.sqrt(np.mean(np.square(frame))))
        if rms < threshold_linear:
            out[start:end] = 0.0
    return out


def apply_highpass(
    audio: np.ndarray,
    cutoff_hz: float,
    sample_rate: int,
    order: int = 4,
) -> np.ndarray:
    """Butterworth high-pass. Cuts mains hum, rumble, wind.

    ``cutoff_hz <= 0`` returns the input unchanged. Implemented with
    second-order sections for numerical stability at low cutoffs.
    """
    if cutoff_hz <= 0 or audio.size == 0:
        return audio
    nyquist = 0.5 * sample_rate
    if cutoff_hz >= nyquist:
        logger.warning(
            f"highpass cutoff {cutoff_hz} Hz >= Nyquist {nyquist} Hz — skipping"
        )
        return audio
    from scipy.signal import butter, sosfilt  # local import keeps cold-start fast

    sos = butter(order, cutoff_hz / nyquist, btype="highpass", output="sos")
    filtered = np.asarray(sosfilt(sos, audio), dtype=np.float32)
    return filtered


def apply_spectral_denoise(
    audio: np.ndarray,
    sample_rate: int,
    noise_profile: Optional[np.ndarray] = None,
    strength: float = 0.75,
) -> np.ndarray:
    """Spectral-subtraction denoise via the ``noisereduce`` library.

    If the library is not installed, logs once and returns input unchanged
    — the whole CPU-only / no-GPU story works without this dep.
    """
    if audio.size == 0:
        return audio
    if not HAS_NOISEREDUCE or _noisereduce is None:
        logger.warning(
            "noise_reduction enabled but 'noisereduce' is not installed; "
            "run 'pip install noisereduce' or set config.audio.noise_reduction: false"
        )
        return audio
    try:
        kwargs = {
            "y": audio.astype(np.float32),
            "sr": sample_rate,
            "prop_decrease": float(np.clip(strength, 0.0, 1.0)),
            "stationary": noise_profile is None,
        }
        if noise_profile is not None and noise_profile.size > 0:
            kwargs["y_noise"] = noise_profile.astype(np.float32)
        result = _noisereduce.reduce_noise(**kwargs)
        return np.asarray(result, dtype=np.float32)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"spectral denoise failed: {e}; returning input unchanged")
        return audio


# ---------------------------------------------------------------------------
# Processor combining the primitives per config
# ---------------------------------------------------------------------------


@dataclass
class MicStats:
    """Levels observed during the last processed buffer."""

    rms_in_db: float
    peak_in_db: float
    rms_out_db: float
    peak_out_db: float
    clipped: bool


class MicProcessor:
    """Run the full input chain on a mic buffer.

    Order is fixed: high-pass → denoise → gain → noise gate. Changing order
    changes the audio character; this order matches what reputable DAW
    plugins do for voice recording.
    """

    def __init__(
        self,
        sample_rate: int,
        gain_db: float = 0.0,
        noise_gate_db: float = -120.0,
        highpass_cutoff_hz: float = 0.0,
        noise_reduction: bool = False,
        noise_reduction_strength: float = 0.75,
        noise_profile: Optional[np.ndarray] = None,
    ):
        self.sample_rate = int(sample_rate)
        self.gain_db = float(gain_db)
        self.noise_gate_db = float(noise_gate_db)
        self.highpass_cutoff_hz = float(highpass_cutoff_hz)
        self.noise_reduction = bool(noise_reduction)
        self.noise_reduction_strength = float(noise_reduction_strength)
        self.noise_profile = noise_profile
        self.last_stats: Optional[MicStats] = None

    @classmethod
    def from_config(
        cls,
        audio_config,
        sample_rate: Optional[int] = None,
        noise_profile: Optional[np.ndarray] = None,
    ) -> "MicProcessor":
        """Build from ``config.audio``. ``sample_rate`` overrides the
        config value (useful for recorder that uses 22050 while capture
        uses 16000)."""
        sr = int(sample_rate if sample_rate is not None else audio_config.sample_rate)
        return cls(
            sample_rate=sr,
            gain_db=getattr(audio_config, "input_gain_db", 0.0),
            noise_gate_db=getattr(audio_config, "noise_gate_db", -60.0),
            highpass_cutoff_hz=getattr(audio_config, "highpass_cutoff_hz", 0.0),
            noise_reduction=getattr(audio_config, "noise_reduction", False),
            noise_reduction_strength=getattr(audio_config, "noise_reduction_strength", 0.75),
            noise_profile=noise_profile,
        )

    def is_noop(self) -> bool:
        """True when no primitive would change the signal — lets callers
        skip copies on the fast path."""
        return (
            self.gain_db == 0.0
            and self.noise_gate_db <= -120.0
            and self.highpass_cutoff_hz <= 0.0
            and not self.noise_reduction
        )

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply the full chain. Input/output: float32 in [-1, 1]."""
        if audio.size == 0:
            self.last_stats = MicStats(-120, -120, -120, -120, False)
            return audio

        buf = audio.astype(np.float32, copy=False)
        rms_in = rms_db(buf)
        peak_in = peak_db(buf)

        if self.is_noop():
            self.last_stats = MicStats(rms_in, peak_in, rms_in, peak_in, peak_in > -0.5)
            return buf

        out = buf.copy()
        if self.highpass_cutoff_hz > 0:
            out = apply_highpass(out, self.highpass_cutoff_hz, self.sample_rate)
        if self.noise_reduction:
            out = apply_spectral_denoise(
                out,
                sample_rate=self.sample_rate,
                noise_profile=self.noise_profile,
                strength=self.noise_reduction_strength,
            )
        if self.gain_db != 0.0:
            out = apply_gain(out, self.gain_db)
        if self.noise_gate_db > -120.0:
            out = apply_noise_gate(
                out,
                threshold_db=self.noise_gate_db,
                sample_rate=self.sample_rate,
            )

        rms_out = rms_db(out)
        peak_out = peak_db(out)
        self.last_stats = MicStats(
            rms_in_db=rms_in,
            peak_in_db=peak_in,
            rms_out_db=rms_out,
            peak_out_db=peak_out,
            clipped=peak_out > -0.5,
        )
        return out

    def process_int16(self, audio: np.ndarray) -> np.ndarray:
        """Convenience: take int16 in, return int16 out. Used by the
        recorder which writes WAV at int16."""
        if audio.dtype != np.int16:
            raise TypeError(f"process_int16 expects int16, got {audio.dtype}")
        if self.is_noop():
            return audio
        f = audio.astype(np.float32) / 32768.0
        processed = self.process(f)
        return np.clip(processed * 32768.0, -32768, 32767).astype(np.int16)

    def set_noise_profile(self, noise_audio: np.ndarray) -> None:
        """Store a captured noise sample to drive non-stationary denoise."""
        self.noise_profile = noise_audio.astype(np.float32)
        logger.info(
            f"noise profile set: {noise_audio.size} samples, "
            f"rms={rms_db(noise_audio.astype(np.float32)):.1f} dB"
        )


# ---------------------------------------------------------------------------
# Live meter
# ---------------------------------------------------------------------------


class AudioMeter:
    """Sliding-window RMS / peak tracker for a live VU display."""

    def __init__(self, window_ms: float = 300.0, sample_rate: int = 22050):
        self.window_samples = max(1, int(sample_rate * window_ms / 1000.0))
        self._buffer: np.ndarray = np.zeros(0, dtype=np.float32)

    def push(self, audio: np.ndarray) -> None:
        self._buffer = np.concatenate(
            [self._buffer[-self.window_samples :], audio.astype(np.float32)]
        )

    def rms_db(self) -> float:
        return rms_db(self._buffer)

    def peak_db(self) -> float:
        return peak_db(self._buffer)

    def reset(self) -> None:
        self._buffer = np.zeros(0, dtype=np.float32)


# ---------------------------------------------------------------------------
# Calibration helpers (used by the mic-check wizard)
# ---------------------------------------------------------------------------


@dataclass
class CalibrationResult:
    """Output of :func:`recommend_calibration`."""

    noise_floor_db: float
    voice_rms_db: float
    voice_peak_db: float
    suggested_gain_db: float
    suggested_gate_db: float
    clipping: bool
    warnings: list[str]

    def yaml_snippet(self) -> str:
        lines = [
            "audio:",
            f"  input_gain_db: {self.suggested_gain_db:.1f}",
            f"  noise_gate_db: {self.suggested_gate_db:.1f}",
            "  highpass_cutoff_hz: 80",
            "  noise_reduction: false",
        ]
        return "\n".join(lines)


def recommend_calibration(
    noise_sample: np.ndarray,
    voice_sample: np.ndarray,
    target_voice_rms_db: float = -18.0,
    gate_margin_db: float = 6.0,
) -> CalibrationResult:
    """Suggest gain + gate given an ambient + voice recording.

    - Noise floor is the RMS of the silent sample.
    - Voice level is the RMS of the spoken sample.
    - Gain suggestion moves voice RMS toward ``target_voice_rms_db``
      (headroom for peaks stays below -0.5 dBFS).
    - Gate suggestion sits ``gate_margin_db`` above the noise floor so
      quiet breath noise is suppressed without chopping soft words.
    """
    noise_rms = rms_db(noise_sample)
    voice_rms = rms_db(voice_sample)
    voice_peak = peak_db(voice_sample)

    gain = float(np.clip(target_voice_rms_db - voice_rms, -12.0, 12.0))
    # Tighten gain to avoid clipping at the new peak.
    if voice_peak + gain > -1.0:
        gain = -1.0 - voice_peak
    gate = noise_rms + gate_margin_db
    gate = float(np.clip(gate, -90.0, -20.0))

    warnings: list[str] = []
    if voice_peak > -0.5:
        warnings.append(
            "voice clipped — lower mic input in macOS Sound Preferences before using gain"
        )
    if noise_rms > -40.0:
        warnings.append(
            f"noisy room (noise floor {noise_rms:.1f} dB) — enable noise_reduction: true"
        )
    if voice_rms - noise_rms < 20.0:
        warnings.append(
            "signal-to-noise < 20 dB — consider moving closer to the mic"
        )

    return CalibrationResult(
        noise_floor_db=noise_rms,
        voice_rms_db=voice_rms,
        voice_peak_db=voice_peak,
        suggested_gain_db=gain,
        suggested_gate_db=gate,
        clipping=voice_peak > -0.5,
        warnings=warnings,
    )

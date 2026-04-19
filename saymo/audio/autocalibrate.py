"""Automated mic calibration.

Given one silent buffer (ambient noise) and one voice buffer (user reading
a calibration sentence), produce a ``MicProcessor`` config that hits
user-defined "excellent" metrics — or explain exactly why the mic
hardware is the bottleneck so the caller can raise the system input
volume and retry.

Everything here is pure numpy math over the captured buffers. Once the
user has spoken once, different candidate configs are *simulated* by
running them through :class:`MicProcessor.process` and measuring the
output. No re-recording is needed to explore the parameter space — the
only reason the CLI re-records is when hardware input volume changes,
which is something software cannot simulate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from saymo.audio.mic_processor import (
    HAS_NOISEREDUCE,
    MicProcessor,
    peak_db,
    rms_db,
)

logger = logging.getLogger("saymo.audio.autocalibrate")


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


@dataclass
class CalibrationTargets:
    """What "excellent" means. Defaults tuned for natural speech.

    Bands chosen so that:
    - voice RMS sits in the sweet spot for loudness / perceived presence
      while accommodating the 18–22 dB crest factor of real (uncompressed)
      speech — a narrower RMS band would force people with dynamic voices
      into clipping;
    - peak stays below 0 dBFS with enough headroom to survive any
      downstream limiter or compressor;
    - SNR high enough that spectral denoise is optional, not required.
    """

    voice_rms_db: tuple[float, float] = (-24.0, -12.0)
    voice_peak_db: tuple[float, float] = (-6.0, -1.0)
    min_snr_db: float = 30.0
    excellent_snr_db: float = 40.0
    max_software_gain_db: float = 15.0
    noise_gate_margin_db: float = 6.0
    # When the peak ceiling (not the gain cap) is what stops us from
    # adding more loudness, projected RMS can fall slightly below the
    # band even though the result is genuinely good. Within this many
    # dB of the lower RMS limit we upgrade poor → good.
    peak_limited_slack_db: float = 3.0

    def mid_rms_db(self) -> float:
        return sum(self.voice_rms_db) / 2.0


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


@dataclass
class AutoCalibrationVerdict:
    """Result of a single autocalibration pass.

    ``settings`` is a plain dict ready to be serialised into the
    ``audio:`` block of ``config.yaml``.

    ``system_volume_recommendation`` is a float in ``[0.0, 1.0]`` — when
    set, the caller should raise the macOS system input volume by that
    *delta* (e.g. ``0.2`` = +20 percentage points) and re-record. When
    ``None``, no hardware change would help (or the mic is already fine).
    """

    settings: dict
    projected_voice_rms_db: float
    projected_voice_peak_db: float
    projected_snr_db: float
    noise_floor_db: float
    input_voice_rms_db: float
    input_voice_peak_db: float
    quality: str  # "excellent" | "good" | "needs_rerecord" | "poor"
    warnings: list[str] = field(default_factory=list)
    system_volume_recommendation: Optional[float] = None

    def excellent(self) -> bool:
        return self.quality == "excellent"

    def actionable(self) -> bool:
        """True when raising macOS input volume may help."""
        return self.system_volume_recommendation is not None

    def yaml_snippet(self) -> str:
        lines = ["audio:"]
        for k, v in self.settings.items():
            if isinstance(v, bool):
                lines.append(f"  {k}: {'true' if v else 'false'}")
            elif isinstance(v, float):
                lines.append(f"  {k}: {v:.1f}")
            else:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------


def _low_band_ratio(audio: np.ndarray, sample_rate: int, cutoff_hz: float = 120.0) -> float:
    """Share of the signal's energy below ``cutoff_hz``.

    Used to decide whether a high-pass filter would help. Silent input
    returns 0 instead of a NaN.
    """
    if audio.size == 0:
        return 0.0
    spectrum = np.abs(np.fft.rfft(audio))
    if float(np.sum(spectrum)) <= 1e-12:
        return 0.0
    freqs = np.fft.rfftfreq(audio.size, d=1.0 / sample_rate)
    total = float(np.sum(spectrum**2))
    below = float(np.sum(spectrum[freqs < cutoff_hz] ** 2))
    return below / total if total > 0 else 0.0


def _choose_highpass(noise: np.ndarray, voice: np.ndarray, sample_rate: int) -> float:
    """Decide a useful high-pass cutoff.

    - If the noise has >35 % of its energy under 120 Hz and the voice does
      not (voice energy under 120 Hz is tiny for speech anyway), cut at
      80 Hz. This kills mains hum / HVAC rumble without touching speech.
    - Otherwise return 0 (no filter).
    """
    noise_low = _low_band_ratio(noise, sample_rate, cutoff_hz=120.0)
    voice_low = _low_band_ratio(voice, sample_rate, cutoff_hz=120.0)
    if noise_low > 0.35 and voice_low < noise_low:
        return 80.0
    return 0.0


def _choose_gain(
    voice_rms: float,
    voice_peak: float,
    targets: CalibrationTargets,
) -> float:
    """Gain that pulls voice RMS toward the midpoint of the target band,
    clamped so the peak stays below ``target_peak_db.upper``."""
    mid = targets.mid_rms_db()
    raw_gain = mid - voice_rms
    # Don't push the peak above the top of the allowed band.
    peak_cap = targets.voice_peak_db[1] - voice_peak
    gain = min(raw_gain, peak_cap)
    gain = float(np.clip(gain, -12.0, targets.max_software_gain_db))
    return round(gain * 2) / 2.0  # 0.5 dB quantisation — YAML readability


def _choose_gate(noise_rms: float, targets: CalibrationTargets) -> float:
    gate = noise_rms + targets.noise_gate_margin_db
    gate = float(np.clip(gate, -90.0, -20.0))
    return round(gate)


def _choose_denoise(noise_rms: float, voice_rms: float, targets: CalibrationTargets) -> bool:
    """Recommend spectral denoise only when SNR is below ``min_snr_db``
    AND the ``noisereduce`` dep is actually available."""
    snr = voice_rms - noise_rms
    return HAS_NOISEREDUCE and snr < targets.min_snr_db


def _classify(
    projected_rms: float,
    projected_peak: float,
    projected_snr: float,
    targets: CalibrationTargets,
    software_gain_saturated: bool,
    peak_limited: bool,
) -> str:
    in_rms_band = targets.voice_rms_db[0] <= projected_rms <= targets.voice_rms_db[1]
    # Peak constraint is one-sided: only penalise when peak is *above* the
    # upper limit (clipping risk). A peak well below the upper limit is
    # fine — it just means more headroom. Pure sine waves have crest
    # factor 3 dB while real speech is 12–18 dB; checking against both
    # bounds falsely flagged quiet sine tests.
    peak_safe = projected_peak <= targets.voice_peak_db[1]
    snr_excellent = projected_snr >= targets.excellent_snr_db
    snr_ok = projected_snr >= targets.min_snr_db

    if in_rms_band and peak_safe and snr_excellent:
        return "excellent"
    if in_rms_band and peak_safe and snr_ok:
        return "good"
    # "Peak-limited" case: we couldn't add more gain because doing so
    # would clip, not because the software gain cap kicked in. That is
    # a genuinely fine result — crest factor of natural speech is just
    # high. Within ``peak_limited_slack_db`` of the band, call it good.
    below_band = targets.voice_rms_db[0] - projected_rms
    if (
        peak_limited
        and peak_safe
        and snr_ok
        and 0 < below_band <= targets.peak_limited_slack_db
    ):
        return "good"
    # If software gain is saturated and RMS still below target band, we
    # need the user to raise the hardware input volume and retry.
    if software_gain_saturated and projected_rms < targets.voice_rms_db[0]:
        return "needs_rerecord"
    return "poor"


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def autocalibrate(
    noise: np.ndarray,
    voice: np.ndarray,
    sample_rate: int,
    targets: Optional[CalibrationTargets] = None,
) -> AutoCalibrationVerdict:
    """Build a verdict from one silence + one voice buffer.

    Steps:

    1. Measure input levels (noise RMS, voice RMS / peak, SNR).
    2. Pick per-primitive settings: high-pass cutoff (FFT-based), gain
       (toward target RMS band, clamped by peak headroom and the
       software cap), noise gate (above noise floor), denoise (if SNR
       below the "good" threshold and ``noisereduce`` is available).
    3. Simulate the full chain on the voice buffer via
       :class:`MicProcessor.process` and measure the output — same code
       that will run at recording time, so the projection is exact.
    4. Classify as excellent / good / needs_rerecord / poor and, when
       relevant, suggest a system-volume delta for the caller to apply
       before re-recording.
    """
    targets = targets or CalibrationTargets()

    noise_rms = rms_db(noise)
    voice_rms = rms_db(voice)
    voice_peak = peak_db(voice)
    snr_in = voice_rms - noise_rms

    highpass_hz = _choose_highpass(noise, voice, sample_rate)
    gain_db = _choose_gain(voice_rms, voice_peak, targets)
    gate_db = _choose_gate(noise_rms, targets)
    denoise_on = _choose_denoise(noise_rms, voice_rms, targets)

    processor = MicProcessor(
        sample_rate=sample_rate,
        gain_db=gain_db,
        noise_gate_db=gate_db,
        highpass_cutoff_hz=highpass_hz,
        noise_reduction=denoise_on,
    )
    processed_voice = processor.process(voice)
    processed_noise = processor.process(noise)

    projected_voice_rms = rms_db(processed_voice)
    projected_voice_peak = peak_db(processed_voice)
    projected_noise_rms = rms_db(processed_noise)
    projected_snr = projected_voice_rms - projected_noise_rms

    software_gain_saturated = gain_db >= targets.max_software_gain_db - 0.01
    # Peak-limited = adding more gain would push the peak past the ceiling.
    # Equivalent condition: gain was chosen by the peak cap, not the gain cap.
    peak_cap = targets.voice_peak_db[1] - voice_peak
    peak_limited = not software_gain_saturated and gain_db >= peak_cap - 0.6

    quality = _classify(
        projected_voice_rms,
        projected_voice_peak,
        projected_snr,
        targets,
        software_gain_saturated,
        peak_limited,
    )

    warnings: list[str] = []
    if voice_peak > targets.voice_peak_db[1]:
        warnings.append(
            f"voice clipped during recording (peak {voice_peak:.1f} dB); "
            "lower macOS input volume if raising produced clipping"
        )
    if snr_in < targets.min_snr_db:
        warnings.append(
            f"low SNR {snr_in:.1f} dB — ambient noise is loud; "
            "move to a quieter room or enable noise_reduction"
        )
    if denoise_on and not HAS_NOISEREDUCE:
        warnings.append(
            "denoise recommended but 'noisereduce' is not installed; "
            "run `pip install noisereduce`"
        )

    # When the software gain has saturated, suggest raising system volume.
    # The delta is chosen so that the new hardware level brings voice RMS
    # into the middle of the target band without software gain — assuming
    # a roughly linear relationship between input-volume slider and dBFS,
    # which is accurate enough for a single calibration step.
    sys_vol_recommendation: Optional[float] = None
    if quality == "needs_rerecord":
        missing_db = targets.mid_rms_db() - projected_voice_rms
        # Rough heuristic: +10 dB ≈ +30 points on the slider (0..100 mapped to 0..1.0).
        sys_vol_recommendation = float(np.clip(missing_db / 10.0 * 0.3, 0.05, 0.35))
    if quality == "good" and peak_limited:
        warnings.append(
            "result is good but peak-limited — if you want more loudness, "
            "move slightly away from the mic or lower macOS input volume "
            "slightly, then re-run `saymo mic-check --auto`"
        )

    settings = {
        "input_gain_db": gain_db,
        "noise_gate_db": gate_db,
        "highpass_cutoff_hz": highpass_hz,
        "noise_reduction": denoise_on,
    }

    logger.info(
        f"autocalibrate verdict={quality} "
        f"voice_rms {voice_rms:.1f}→{projected_voice_rms:.1f} dB, "
        f"peak {voice_peak:.1f}→{projected_voice_peak:.1f} dB, "
        f"snr {snr_in:.1f}→{projected_snr:.1f} dB"
    )

    return AutoCalibrationVerdict(
        settings=settings,
        projected_voice_rms_db=projected_voice_rms,
        projected_voice_peak_db=projected_voice_peak,
        projected_snr_db=projected_snr,
        noise_floor_db=noise_rms,
        input_voice_rms_db=voice_rms,
        input_voice_peak_db=voice_peak,
        quality=quality,
        warnings=warnings,
        system_volume_recommendation=sys_vol_recommendation,
    )

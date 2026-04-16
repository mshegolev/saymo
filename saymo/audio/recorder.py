"""Record voice samples from microphone for voice cloning."""

import logging
import wave
from pathlib import Path

import sounddevice as sd

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.audio.recorder")

VOICE_SAMPLES_DIR = Path.home() / ".saymo" / "voice_samples"


def record_sample(
    device_name: str,
    duration: int = 30,
    sample_rate: int = 22050,
    output_path: str | None = None,
) -> Path:
    """Record a voice sample from the microphone.

    Args:
        device_name: Input device name (e.g., 'Plantronics').
        duration: Recording duration in seconds.
        sample_rate: Sample rate (22050 recommended for XTTS).
        output_path: Custom output path. If None, saves to ~/.saymo/voice_samples/.

    Returns:
        Path to the saved WAV file.
    """
    device = find_device(device_name, kind="input")
    if not device:
        raise RuntimeError(f"Input device not found: {device_name}")

    if output_path:
        path = Path(output_path)
    else:
        VOICE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        path = VOICE_SAMPLES_DIR / "voice_sample.wav"

    logger.info(f"Recording {duration}s from '{device.name}' at {sample_rate}Hz")

    # Record
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device.index,
    )
    sd.wait()

    # Save as WAV
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    logger.info(f"Saved voice sample: {path} ({path.stat().st_size} bytes)")
    return path


def get_voice_sample_path() -> Path | None:
    """Get path to existing voice sample, if any."""
    path = VOICE_SAMPLES_DIR / "voice_sample.wav"
    return path if path.exists() else None

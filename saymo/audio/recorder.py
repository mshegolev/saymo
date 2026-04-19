"""Record voice samples from microphone for voice cloning."""

import json
import logging
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd

from saymo.audio.devices import find_device
from saymo.audio.mic_processor import MicProcessor

logger = logging.getLogger("saymo.audio.recorder")

VOICE_SAMPLES_DIR = Path.home() / ".saymo" / "voice_samples"
TRAINING_DATASET_DIR = Path.home() / ".saymo" / "training_dataset"


def record_sample(
    device_name: str,
    duration: int = 30,
    sample_rate: int = 22050,
    output_path: str | None = None,
    processor: Optional[MicProcessor] = None,
) -> Path:
    """Record a voice sample from the microphone.

    Args:
        device_name: Input device name (e.g., 'Plantronics').
        duration: Recording duration in seconds.
        sample_rate: Sample rate (22050 recommended for XTTS).
        output_path: Custom output path. If None, saves to ~/.saymo/voice_samples/.
        processor: Optional mic-input chain (gain / gate / high-pass /
            denoise). When ``None`` or a no-op, the raw buffer is written
            unchanged — identical to pre-calibration behaviour.

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
    audio_1d = np.asarray(audio, dtype=np.int16).flatten()

    if processor is not None and not processor.is_noop():
        audio_1d = processor.process_int16(audio_1d)
        stats = processor.last_stats
        if stats is not None:
            logger.info(
                f"mic chain: rms {stats.rms_in_db:.1f} → {stats.rms_out_db:.1f} dB, "
                f"peak {stats.peak_in_db:.1f} → {stats.peak_out_db:.1f} dB"
                + (" [CLIPPED]" if stats.clipped else "")
            )

    # Save as WAV
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio_1d.tobytes())

    logger.info(f"Saved voice sample: {path} ({path.stat().st_size} bytes)")
    return path


def get_voice_sample_path() -> Path | None:
    """Get path to existing voice sample, if any."""
    path = VOICE_SAMPLES_DIR / "voice_sample.wav"
    return path if path.exists() else None


def _trim_silence(audio: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    """Trim leading and trailing silence from audio.

    Args:
        audio: Audio samples as int16 numpy array.
        threshold: Energy threshold relative to max amplitude (0.0-1.0).

    Returns:
        Trimmed audio array.
    """
    if len(audio) == 0:
        return audio

    # Normalize to float for energy calculation
    float_audio = audio.astype(np.float32) / 32768.0
    energy = np.abs(float_audio)

    # Find first and last sample above threshold
    above = np.where(energy > threshold)[0]
    if len(above) == 0:
        return audio  # All silence, return as-is

    start = max(0, above[0] - 1000)  # 1000 samples padding (~45ms at 22050)
    end = min(len(audio), above[-1] + 1000)
    return audio[start:end]


def _save_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    """Save audio array as WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


def record_guided_session(
    prompts: list[str],
    device_name: str,
    output_dir: Path | None = None,
    sample_rate: int = 22050,
    max_duration_per_prompt: int = 20,
    trim_silence: bool = True,
    resume: bool = False,
    processor: Optional[MicProcessor] = None,
) -> list[Path]:
    """Record voice samples one prompt at a time with guided prompts.

    Shows each prompt on screen, records the user reading it,
    optionally trims silence, saves each recording individually.

    Args:
        prompts: List of text prompts to display for reading.
        device_name: Input device name.
        output_dir: Directory for saved WAVs. Defaults to ~/.saymo/training_dataset/raw/.
        sample_rate: Sample rate (22050 recommended for XTTS).
        max_duration_per_prompt: Max recording duration per prompt in seconds.
        trim_silence: Whether to trim leading/trailing silence.
        resume: If True, skip prompts that already have recordings.

    Returns:
        List of paths to saved WAV files.
    """
    device = find_device(device_name, kind="input")
    if not device:
        raise RuntimeError(f"Input device not found: {device_name}")

    if output_dir is None:
        output_dir = TRAINING_DATASET_DIR / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track session progress
    session_file = output_dir / "session_progress.json"
    completed_indices: set[int] = set()

    if resume and session_file.exists():
        progress = json.loads(session_file.read_text())
        completed_indices = set(progress.get("completed", []))
        logger.info(f"Resuming session: {len(completed_indices)}/{len(prompts)} already recorded")

    saved_paths: list[Path] = []

    for i, prompt in enumerate(prompts):
        filename = f"{i:04d}.wav"
        path = output_dir / filename

        # Skip already recorded prompts when resuming
        if resume and i in completed_indices and path.exists():
            saved_paths.append(path)
            continue

        # Record
        logger.info(f"Recording prompt {i+1}/{len(prompts)}: {prompt[:60]}...")
        audio = sd.rec(
            int(max_duration_per_prompt * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device.index,
        )
        sd.wait()

        # Flatten to 1D
        audio = audio.flatten()

        # Mic input chain (gain / gate / high-pass / denoise)
        if processor is not None and not processor.is_noop():
            audio = processor.process_int16(audio)

        # Trim silence
        if trim_silence:
            audio = _trim_silence(audio)

        # Save
        _save_wav(path, audio, sample_rate)
        saved_paths.append(path)

        # Update progress
        completed_indices.add(i)
        session_file.write_text(json.dumps({
            "completed": sorted(completed_indices),
            "total": len(prompts),
        }))

        duration = len(audio) / sample_rate
        logger.info(f"Saved {filename}: {duration:.1f}s")

    return saved_paths


def get_training_dataset_dir() -> Path:
    """Get path to training dataset directory."""
    return TRAINING_DATASET_DIR

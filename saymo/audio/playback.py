"""Audio playback to virtual microphone (BlackHole) via sounddevice."""

import asyncio
import io
import logging

import numpy as np
import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.audio.playback")


async def play_audio_bytes(
    audio_data: bytes,
    device_name: str,
    sample_rate: int = 24000,
    blocking: bool = True,
) -> None:
    """Play audio bytes (WAV/MP3/OGG format) to a specified output device.

    Args:
        audio_data: Raw audio file bytes (any format soundfile supports).
        device_name: Output device name (e.g., 'BlackHole 2ch').
        sample_rate: Expected sample rate of the audio.
        blocking: Whether to wait for playback to finish.
    """
    device = find_device(device_name, kind="output")
    if not device:
        raise RuntimeError(f"Output device not found: {device_name}")

    # Decode audio bytes to numpy array
    audio_array, sr = sf.read(io.BytesIO(audio_data), dtype="float32")

    logger.info(f"Playing {len(audio_array)} samples at {sr}Hz to '{device.name}'")

    if blocking:
        await asyncio.to_thread(
            sd.play, audio_array, samplerate=sr, device=device.index
        )
        await asyncio.to_thread(sd.wait)
    else:
        await asyncio.to_thread(
            sd.play, audio_array, samplerate=sr, device=device.index
        )


async def play_pcm(
    pcm_data: np.ndarray,
    device_name: str,
    sample_rate: int = 24000,
) -> None:
    """Play raw PCM numpy array to a specified output device."""
    device = find_device(device_name, kind="output")
    if not device:
        raise RuntimeError(f"Output device not found: {device_name}")

    await asyncio.to_thread(sd.play, pcm_data, samplerate=sample_rate, device=device.index)
    await asyncio.to_thread(sd.wait)


def stop_playback() -> None:
    """Immediately stop all audio playback."""
    sd.stop()

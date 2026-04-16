"""Play audio to multiple devices simultaneously (e.g., BlackHole + headphones)."""

import asyncio
import io
import logging

import numpy as np
import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.audio.multi_play")


def play_to_devices(
    audio_data: np.ndarray,
    sample_rate: int,
    device_names: list[str],
) -> None:
    """Play the same audio to multiple output devices simultaneously.

    Uses threads to start playback on all devices at once.
    """
    devices = []
    for name in device_names:
        dev = find_device(name, kind="output")
        if dev:
            devices.append(dev)
        else:
            logger.warning(f"Device not found: {name}")

    if not devices:
        raise RuntimeError(f"No output devices found from: {device_names}")

    # Play on all devices in parallel threads
    streams = []
    for dev in devices:
        logger.info(f"Playing to '{dev.name}' at {sample_rate}Hz")
        stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=1 if audio_data.ndim == 1 else audio_data.shape[1],
            device=dev.index,
        )
        streams.append(stream)

    # Start all streams
    for s in streams:
        s.start()

    # Write data in chunks to all streams
    chunk_size = 1024
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i + chunk_size]
        for s in streams:
            try:
                s.write(chunk)
            except Exception:
                pass

    # Close all streams
    for s in streams:
        s.stop()
        s.close()


async def play_bytes_to_devices(
    audio_bytes: bytes,
    device_names: list[str],
) -> None:
    """Play audio file bytes to multiple devices simultaneously."""
    data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    await asyncio.to_thread(play_to_devices, data, sr, device_names)

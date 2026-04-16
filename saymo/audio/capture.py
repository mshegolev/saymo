"""Capture audio from BlackHole (Glip call) as a continuous stream."""

import logging
import queue

import numpy as np
import sounddevice as sd

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.audio.capture")


class AudioCapture:
    """Captures audio from an input device into a thread-safe queue.

    Audio is delivered as numpy chunks (float32, mono, 16kHz).
    """

    def __init__(
        self,
        device_name: str = "BlackHole 16ch",
        sample_rate: int = 16000,
        chunk_seconds: float = 2.0,
    ):
        self.sample_rate = sample_rate
        self.chunk_samples = int(sample_rate * chunk_seconds)
        self.device_name = device_name
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=30)
        self._stream = None
        self._running = False

        device = find_device(device_name, kind="input")
        if not device:
            raise RuntimeError(f"Input device not found: {device_name}")
        self.device_index = device.index
        logger.info(f"Capture device: {device.name} (index {device.index})")

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        # Convert to mono float32 if needed
        audio = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
        try:
            self.audio_queue.put_nowait(audio)
        except queue.Full:
            # Drop oldest chunk
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            self.audio_queue.put_nowait(audio)

    def start(self):
        """Start capturing audio."""
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device_index,
            blocksize=self.chunk_samples,
            callback=self._callback,
        )
        self._stream.start()
        logger.info(f"Capturing from '{self.device_name}' at {self.sample_rate}Hz")

    def stop(self):
        """Stop capturing."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("Capture stopped")

    def get_chunk(self, timeout: float = 3.0) -> np.ndarray | None:
        """Get next audio chunk. Returns None on timeout."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

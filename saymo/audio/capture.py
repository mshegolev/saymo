"""Capture audio from BlackHole (Glip call) as a continuous stream.

Uses overlapping sliding window to avoid cutting words at chunk boundaries.
"""

import logging
import queue

import numpy as np
import sounddevice as sd

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.audio.capture")


class AudioCapture:
    """Captures audio with overlapping chunks for reliable transcription.

    Uses a sliding window: each chunk overlaps the previous one by 50%.
    This ensures words at chunk boundaries are captured in at least one chunk.
    """

    def __init__(
        self,
        device_name: str = "BlackHole 16ch",
        sample_rate: int = 16000,
        chunk_seconds: float = 4.0,
        overlap_seconds: float = 2.0,
    ):
        self.sample_rate = sample_rate
        self.chunk_samples = int(sample_rate * chunk_seconds)
        self.step_samples = int(sample_rate * (chunk_seconds - overlap_seconds))
        self.device_name = device_name
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=30)
        self._stream = None
        self._running = False
        self._buffer = np.array([], dtype=np.float32)

        device = find_device(device_name, kind="input")
        if not device:
            raise RuntimeError(f"Input device not found: {device_name}")
        self.device_index = device.index
        logger.info(f"Capture: {device.name} | chunk={chunk_seconds}s overlap={overlap_seconds}s")

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio status: {status}")
        audio = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()

        # Accumulate in buffer
        self._buffer = np.concatenate([self._buffer, audio])

        # Emit overlapping chunks
        while len(self._buffer) >= self.chunk_samples:
            chunk = self._buffer[:self.chunk_samples].copy()
            self._buffer = self._buffer[self.step_samples:]
            try:
                self.audio_queue.put_nowait(chunk)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    pass
                self.audio_queue.put_nowait(chunk)

    def start(self):
        self._running = True
        self._buffer = np.array([], dtype=np.float32)
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device_index,
            blocksize=4096,
            callback=self._callback,
        )
        self._stream.start()
        logger.info(f"Capturing from '{self.device_name}'")

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_chunk(self, timeout: float = 5.0) -> np.ndarray | None:
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

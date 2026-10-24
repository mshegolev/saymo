"""Record the local microphone to a wav file for later re-transcription.

Split out of the ``--record`` path in ``scripts/live_translate.py``: same
InputStream-callback-queue-writer-thread shape, but without the silence
segmentation state machine, since this just needs one continuous wav of the
user's own speech for a post-call speech-coaching pass.
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.audio.meeting_recorder")

SAMPLE_RATE = 16000
BLOCK_SAMPLES = 1600  # 100ms blocks, matches live_translate.py


class MeetingRecorder:
    """Records one device's mono mic stream to ``out_path`` until stopped."""

    def __init__(self, device_name: str, out_path: Path):
        self.device_name = device_name
        self.out_path = Path(out_path)
        self._blocks: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=200)
        self._stop = threading.Event()
        self._stream: sd.InputStream | None = None
        self._writer_thread: threading.Thread | None = None
        self._sound_file: sf.SoundFile | None = None

    def _callback(self, indata, _frames, _time_info, status):
        if status:
            logger.debug(f"meeting recorder audio status: {status}")
        mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
        try:
            self._blocks.put_nowait(mono.astype(np.float32, copy=False))
        except queue.Full:
            pass  # drop rather than stall the audio callback

    def _write_loop(self) -> None:
        # Disk I/O happens here, never inside `_callback` (the CoreAudio
        # callback), where blocking would drop frames.
        while not self._stop.is_set() or not self._blocks.empty():
            try:
                block = self._blocks.get(timeout=0.5)
            except queue.Empty:
                continue
            self._sound_file.write(block)

    def start(self) -> None:
        device = find_device(self.device_name, kind="input")
        if not device:
            raise RuntimeError(f"Input device not found: {self.device_name!r}")

        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self._sound_file = sf.SoundFile(
            str(self.out_path),
            mode="w",
            samplerate=SAMPLE_RATE,
            channels=1,
            subtype="PCM_16",
        )
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=device.index,
            blocksize=BLOCK_SAMPLES,
            callback=self._callback,
        )
        self._stream.start()
        self._writer_thread = threading.Thread(target=self._write_loop, daemon=True)
        self._writer_thread.start()
        logger.info(f"Recording meeting mic from '{device.name}' to {self.out_path}")

    def stop(self) -> Path:
        self._stop.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        if self._writer_thread is not None:
            self._writer_thread.join(timeout=5.0)
        if self._sound_file is not None:
            self._sound_file.close()
        logger.info(f"Stopped recording, saved to {self.out_path}")
        return self.out_path

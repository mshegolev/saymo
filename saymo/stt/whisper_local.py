"""Local speech-to-text using faster-whisper.

Optimized for name detection: no VAD filter, higher beam size.
"""

import logging

import numpy as np

logger = logging.getLogger("saymo.stt.whisper")


class LocalWhisper:
    """Transcribe audio chunks using faster-whisper (local, no API)."""

    def __init__(self, model_size: str = "small", language: str = "ru"):
        self.model_size = model_size
        self.language = language
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading whisper model '{self.model_size}'...")
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
            logger.info("Whisper model loaded")
        return self._model

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio chunk to text.

        VAD filter disabled to catch short words like names.
        """
        model = self._load()
        segments, _ = model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            best_of=3,
            vad_filter=False,  # Don't filter — we need to catch short names
            no_speech_threshold=0.5,
            condition_on_previous_text=False,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        return text

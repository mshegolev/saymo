"""Local speech-to-text using faster-whisper."""

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

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio chunk to text.

        Args:
            audio: float32 numpy array (mono, 16kHz).
            sample_rate: Sample rate of audio.

        Returns:
            Transcribed text.
        """
        model = self._load()
        segments, info = model.transcribe(
            audio,
            language=self.language,
            beam_size=3,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text = " ".join(seg.text.strip() for seg in segments)
        return text

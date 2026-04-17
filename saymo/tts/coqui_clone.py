"""Coqui TTS XTTS v2 — voice cloning with a short audio sample.

Speaks in the user's cloned voice. Supports Russian.
Runs in the main saymo venv (Python 3.12+).
"""

import asyncio
import io
import logging
import tempfile
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.tts.coqui_clone")

DEFAULT_VOICE_SAMPLE = Path.home() / ".saymo" / "voice_samples" / "voice_sample.wav"
XTTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


class CoquiCloneTTS:
    """Text-to-speech using XTTS v2 with cloned voice."""

    _model = None  # lazy-loaded, shared across instances

    def __init__(self, voice_sample: str | None = None, language: str = "ru"):
        self.language = language
        self.voice_sample = Path(voice_sample) if voice_sample else DEFAULT_VOICE_SAMPLE

        if not self.voice_sample.exists():
            raise FileNotFoundError(
                f"Voice sample not found: {self.voice_sample}\n"
                f"Record with: saymo record-voice"
            )

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from TTS.api import TTS
            logger.info(f"Loading XTTS v2 model ({XTTS_MODEL_NAME})...")
            cls._model = TTS(XTTS_MODEL_NAME)
        return cls._model

    def _synthesize_sync(self, text: str, output_path: str) -> str:
        logger.info(f"Synthesizing {len(text)} chars with cloned voice")
        model = self._get_model()
        model.tts_to_file(
            text=text,
            speaker_wav=str(self.voice_sample),
            language=self.language,
            file_path=output_path,
        )
        return output_path

    async def synthesize(self, text: str) -> bytes:
        """Clone voice and synthesize text to WAV bytes."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await asyncio.to_thread(self._synthesize_sync, text, tmp_path)
            audio_bytes = Path(tmp_path).read_bytes()
            logger.info(f"Generated {len(audio_bytes)} bytes")
            return audio_bytes
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_sentences(self, sentences: list[str]) -> list[bytes]:
        """Synthesize each sentence separately. Returns list of WAV bytes."""
        results = []
        for i, sent in enumerate(sentences):
            if not sent.strip():
                continue
            logger.info(f"Sentence {i+1}/{len(sentences)}: {sent[:60]}...")
            audio = await self.synthesize(sent)
            results.append(audio)
        return results

    async def synthesize_to_device(self, text: str, device_name: str) -> None:
        """Synthesize with cloned voice and play to audio device."""
        audio_bytes = await self.synthesize(text)
        data, sr = sf.read(io.BytesIO(audio_bytes))

        device = find_device(device_name, kind="output")
        device_idx = device.index if device else None

        logger.info(f"Playing cloned voice to '{device_name}' at {sr}Hz")
        await asyncio.to_thread(sd.play, data, samplerate=sr, device=device_idx)
        await asyncio.to_thread(sd.wait)

    async def stop(self) -> None:
        sd.stop()

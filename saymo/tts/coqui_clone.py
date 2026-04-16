"""Coqui TTS XTTS v2 — voice cloning with a short audio sample.

Speaks in the user's cloned voice. Supports Russian.
Requires: pip install coqui-tts[codec]
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


class CoquiCloneTTS:
    """Text-to-speech using XTTS v2 with cloned voice."""

    def __init__(self, voice_sample: str | None = None, language: str = "ru"):
        """Initialize XTTS v2 voice clone.

        Args:
            voice_sample: Path to WAV file with voice sample (6s min, 30-60s ideal).
            language: Language code ('ru', 'en', etc.).
        """
        self.language = language
        self.voice_sample = Path(voice_sample) if voice_sample else DEFAULT_VOICE_SAMPLE

        if not self.voice_sample.exists():
            raise FileNotFoundError(
                f"Voice sample not found: {self.voice_sample}\n"
                f"Record with: python3 -m saymo record-voice"
            )

        self._tts = None

    def _load_model(self):
        """Lazy-load XTTS v2 model (first call takes ~10-30s)."""
        if self._tts is None:
            import warnings
            warnings.filterwarnings("ignore")
            from TTS.api import TTS

            logger.info("Loading XTTS v2 model (first time may download ~2GB)...")
            self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            logger.info("XTTS v2 model loaded!")
        return self._tts

    async def synthesize(self, text: str) -> bytes:
        """Clone voice and synthesize text to WAV bytes."""
        tts = await asyncio.to_thread(self._load_model)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            logger.info(f"Synthesizing {len(text)} chars with cloned voice ({self.language})")

            await asyncio.to_thread(
                tts.tts_to_file,
                text=text,
                speaker_wav=str(self.voice_sample),
                language=self.language,
                file_path=tmp_path,
            )

            audio_bytes = Path(tmp_path).read_bytes()
            logger.info(f"Generated {len(audio_bytes)} bytes")
            return audio_bytes
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_sentences(self, sentences: list[str], temperature: float = 0.65,
                                    repetition_penalty: float = 2.0) -> list[bytes]:
        """Synthesize each sentence separately. Returns list of WAV bytes per sentence."""
        tts = await asyncio.to_thread(self._load_model)
        results = []
        for i, sent in enumerate(sentences):
            if not sent.strip():
                continue
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                logger.info(f"Sentence {i+1}/{len(sentences)}: {sent[:60]}...")
                await asyncio.to_thread(
                    tts.tts_to_file,
                    text=sent,
                    speaker_wav=str(self.voice_sample),
                    language=self.language,
                    file_path=tmp_path,
                )
                results.append(Path(tmp_path).read_bytes())
            finally:
                Path(tmp_path).unlink(missing_ok=True)
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

"""OpenAI TTS engine."""

import asyncio
import logging

from openai import OpenAI

from saymo.config import OpenAITTSConfig

logger = logging.getLogger("saymo.tts.openai")


class OpenAITTS:
    """Text-to-speech using OpenAI API."""

    def __init__(self, config: OpenAITTSConfig):
        self.config = config
        self._client = OpenAI(api_key=config.api_key) if config.api_key else OpenAI()

    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes using OpenAI TTS.

        Returns MP3 audio bytes.
        """
        logger.info(f"Synthesizing {len(text)} chars with OpenAI TTS ({self.config.voice})")

        response = await asyncio.to_thread(
            self._client.audio.speech.create,
            model=self.config.model,
            voice=self.config.voice,  # type: ignore[arg-type]
            input=text,
            response_format="mp3",
        )

        audio_bytes = response.read()
        logger.info(f"Generated {len(audio_bytes)} bytes of audio")
        return audio_bytes

    async def stop(self) -> None:
        pass

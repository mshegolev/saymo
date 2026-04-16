"""Abstract TTS interface."""

from typing import Protocol


class TTSEngine(Protocol):
    """Protocol for TTS engines."""

    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (WAV/MP3/OGG format).

        Returns raw audio file bytes suitable for playback.
        """
        ...

    async def stop(self) -> None:
        """Stop any ongoing synthesis."""
        ...

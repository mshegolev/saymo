"""macOS native TTS using the `say` command. Free fallback engine."""

import asyncio
import logging
import tempfile
from pathlib import Path

from saymo.config import MacOSSayConfig

logger = logging.getLogger("saymo.tts.macos_say")


class MacOSSay:
    """Text-to-speech using macOS built-in `say` command."""

    def __init__(self, config: MacOSSayConfig):
        self.config = config

    async def synthesize(self, text: str) -> bytes:
        """Convert text to AIFF audio bytes using macOS say.

        Returns AIFF audio file bytes.
        """
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = ["say", "-v", self.config.voice, "-o", tmp_path, text]
            logger.info(f"Synthesizing with macOS say (voice: {self.config.voice})")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"macOS say failed: {stderr.decode()}")

            audio_bytes = Path(tmp_path).read_bytes()
            logger.info(f"Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_to_device(self, text: str, device_name: str) -> None:
        """Speak directly to an audio device (no file needed)."""
        cmd = ["say", "-v", self.config.voice, "-a", device_name, text]
        logger.info(f"Speaking to device '{device_name}' with voice '{self.config.voice}'")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"macOS say failed: {stderr.decode()}")

    async def stop(self) -> None:
        """Kill any running say processes."""
        proc = await asyncio.create_subprocess_exec(
            "killall", "say",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()

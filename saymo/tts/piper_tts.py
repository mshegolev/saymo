"""Piper TTS — fast local neural TTS with Russian voice support.

Uses ONNX models, no GPU needed. Much faster than cloud APIs.
Models stored in ~/.saymo/piper_models/.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.tts.piper")

DEFAULT_MODEL_DIR = Path.home() / ".saymo" / "piper_models"


class PiperTTS:
    """Text-to-speech using Piper (local, fast, Russian support)."""

    def __init__(self, model_path: str | None = None, speaker: int | None = None):
        """Initialize Piper TTS.

        Args:
            model_path: Path to .onnx model file. If None, uses default Russian model.
            speaker: Speaker ID for multi-speaker models.
        """
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = DEFAULT_MODEL_DIR / "ru_RU-dmitri-medium.onnx"

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Piper model not found: {self.model_path}\n"
                f"Download with: mkdir -p {DEFAULT_MODEL_DIR} && "
                f"curl -sL 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
                f"ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx' "
                f"-o {DEFAULT_MODEL_DIR}/ru_RU-dmitri-medium.onnx"
            )

        self.speaker = speaker

    async def synthesize(self, text: str) -> bytes:
        """Convert text to WAV audio bytes using Piper.

        Returns WAV file bytes.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = ["piper", "--model", str(self.model_path), "--output_file", tmp_path]
            if self.speaker is not None:
                cmd.extend(["--speaker", str(self.speaker)])

            logger.info(f"Synthesizing {len(text)} chars with Piper")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate(input=text.encode("utf-8"))

            if proc.returncode != 0:
                raise RuntimeError(f"Piper failed: {stderr.decode()}")

            audio_bytes = Path(tmp_path).read_bytes()
            logger.info(f"Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize_to_device(self, text: str, device_name: str) -> None:
        """Synthesize and play directly to an audio device."""
        import sounddevice as sd
        import soundfile as sf
        import io

        audio_bytes = await self.synthesize(text)
        data, sr = sf.read(io.BytesIO(audio_bytes))

        device = find_device(device_name, kind="output")
        device_idx = device.index if device else None

        logger.info(f"Playing to '{device_name}' at {sr}Hz")
        await asyncio.to_thread(sd.play, data, samplerate=sr, device=device_idx)
        await asyncio.to_thread(sd.wait)

    async def stop(self) -> None:
        pass

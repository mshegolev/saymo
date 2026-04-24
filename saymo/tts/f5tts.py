"""F5-TTS voice cloning via Misha24-10/F5-TTS_RUSSIAN.

One-stage Russian-first voice cloning — alternative to the XTTS+RVC
two-stage pipeline. Calls F5-TTS's CLI in its own venv via subprocess
because F5-TTS pins torch 2.11 + transformers 5.x which conflicts with
Saymo's mlx-audio / coqui-tts pinning.

Reference audio: ~/.saymo/voice_samples/voice_sample.wav (the same file
used for XTTS conditioning). F5-TTS needs a transcript of the reference
to align voice characteristics — read from a sidecar .txt file or
provided via config.f5tts.ref_text.
"""

import asyncio
import io
import logging
import subprocess
import tempfile
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device
from saymo.config import F5TTSConfig

logger = logging.getLogger("saymo.tts.f5tts")

DEFAULT_VOICE_SAMPLE = Path.home() / ".saymo" / "voice_samples" / "voice_sample.wav"
DEFAULT_VENV_PYTHON = Path.home() / "F5TTS" / ".venv" / "bin" / "python"


class F5TTSCloneTTS:
    """Text-to-speech using F5-TTS RU fork with cloned voice.

    Drop-in compatible with the other Saymo TTS engines.
    Subprocesses out to ~/F5TTS/.venv where f5-tts is installed.
    """

    def __init__(
        self,
        language: str = "ru",
        f5tts: F5TTSConfig | None = None,
        voice_sample: str | None = None,
    ):
        self.language = language
        self.cfg = f5tts or F5TTSConfig()
        self.voice_sample = (
            Path(voice_sample).expanduser() if voice_sample else DEFAULT_VOICE_SAMPLE
        )

        if not self.voice_sample.exists():
            raise FileNotFoundError(
                f"Voice sample not found: {self.voice_sample}. "
                f"Record one with: saymo record-voice -d 15"
            )

        venv_py = (
            Path(self.cfg.venv_python).expanduser()
            if self.cfg.venv_python
            else DEFAULT_VENV_PYTHON
        )
        if not venv_py.exists():
            raise FileNotFoundError(
                f"F5-TTS venv not found at {venv_py}. "
                f"Run ./scripts/install_f5tts.sh first."
            )
        self._venv_python = venv_py

        # Reference transcript: required by F5-TTS so it can align prosody.
        # Look for a sidecar voice_sample.txt; fall back to a generic phrase.
        ref_txt_path = self.voice_sample.with_suffix(".txt")
        if ref_txt_path.exists():
            self._ref_text = ref_txt_path.read_text(encoding="utf-8").strip()
        else:
            # Generic neutral Russian phrase. F5-TTS works best with a real
            # transcript but tolerates approximate ones for short references.
            self._ref_text = "Это пример референтного аудио для клонирования голоса."

        ckpt = self.cfg.ckpt_file
        if not ckpt:
            raise ValueError(
                "f5tts.ckpt_file is empty. Set it in config to the .pt path "
                "(e.g. ~/F5TTS/models/ru/F5TTS_v1_Base_v2/<file>.pt)"
            )
        self._ckpt = Path(ckpt).expanduser()
        if not self._ckpt.exists():
            raise FileNotFoundError(f"F5-TTS checkpoint not found: {self._ckpt}")

        self._vocab = (
            Path(self.cfg.vocab_file).expanduser() if self.cfg.vocab_file else None
        )

    def _synthesize_sync(self, text: str, output_dir: Path) -> Path:
        """Run f5-tts_infer-cli as subprocess. Blocks until WAV is on disk."""
        cli = self._venv_python.parent / "f5-tts_infer-cli"
        output_file = "out.wav"
        cmd = [
            str(cli),
            "-m", self.cfg.model_name,
            "-p", str(self._ckpt),
            "-r", str(self.voice_sample),
            "-s", self._ref_text,
            "-t", text,
            "-o", str(output_dir),
            "-w", output_file,
            "--nfe_step", str(self.cfg.nfe_step),
            "--speed", str(self.cfg.speed),
            "--device", self.cfg.device,
        ]
        if self._vocab:
            cmd.extend(["-v", str(self._vocab)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"F5-TTS inference failed (exit {result.returncode}): "
                f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
            )

        out_path = output_dir / output_file
        if not out_path.exists():
            raise RuntimeError(f"F5-TTS produced no output at {out_path}")
        return out_path

    async def synthesize(self, text: str) -> bytes:
        """Clone voice and synthesize text to WAV bytes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out = await asyncio.to_thread(self._synthesize_sync, text, tmp_path)
            audio_bytes = out.read_bytes()
            logger.info(f"F5-TTS generated {len(audio_bytes)} bytes")
            return audio_bytes

    async def synthesize_sentences(self, sentences: list[str]) -> list[bytes]:
        results = []
        for i, sent in enumerate(sentences):
            if not sent.strip():
                continue
            logger.info(f"Sentence {i+1}/{len(sentences)}: {sent[:60]}...")
            audio = await self.synthesize(sent)
            results.append(audio)
        return results

    async def synthesize_to_device(self, text: str, device_name: str) -> None:
        audio_bytes = await self.synthesize(text)
        data, sr = sf.read(io.BytesIO(audio_bytes))

        device = find_device(device_name, kind="output")
        device_idx = device.index if device else None

        logger.info(f"Playing F5-TTS to '{device_name}' at {sr}Hz")
        await asyncio.to_thread(sd.play, data, samplerate=sr, device=device_idx)
        await asyncio.to_thread(sd.wait)

    async def stop(self) -> None:
        sd.stop()

"""XTTS v2 + RVC v2 voice conversion pipeline.

Generates speech with XTTS (intonation, words, prosody), then re-timbres with
an RVC v2 model (true voice match). Combined output reaches 9-10/10 perceived
similarity vs ~7-8/10 with XTTS-only.

RVC inference runs in Applio's separate venv via subprocess, because rvc-python
requires numpy<=1.25.3 which conflicts with mlx-audio's numpy>=1.26.4. Calling
out to Applio's CLI keeps Saymo's main venv clean and avoids the dependency
hell that bit the original XTTS install.
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
from saymo.config import RVCConfig
from saymo.tts.coqui_clone import CoquiCloneTTS

logger = logging.getLogger("saymo.tts.xtts_rvc")

DEFAULT_APPLIO_DIR = Path.home() / "Applio"


class XttsRvcCloneTTS:
    """Two-stage TTS: XTTS v2 → RVC v2 voice conversion.

    Drop-in replacement for CoquiCloneTTS. Wraps an existing XTTS engine
    and post-processes its output through Applio's RVC inference CLI.
    """

    def __init__(self, language: str = "ru", rvc: RVCConfig | None = None):
        self.language = language
        self.rvc = rvc or RVCConfig()
        self._xtts = CoquiCloneTTS(language=language)

        # Validate RVC artifacts up front so the user gets a clear error
        # before the first synthesis attempt rather than a cryptic stack.
        model = Path(self.rvc.model_path).expanduser() if self.rvc.model_path else None
        index = Path(self.rvc.index_path).expanduser() if self.rvc.index_path else None
        if not model or not model.exists():
            raise FileNotFoundError(
                f"RVC model not found: {self.rvc.model_path}. "
                f"Train one via ./scripts/train_rvc.sh or set tts.rvc.model_path."
            )
        if not index or not index.exists():
            raise FileNotFoundError(f"RVC index not found: {self.rvc.index_path}")
        self._model_path = model
        self._index_path = index

        applio = Path(self.rvc.applio_dir).expanduser() if self.rvc.applio_dir else DEFAULT_APPLIO_DIR
        self._applio_python = applio / ".venv" / "bin" / "python"
        self._applio_core = applio / "core.py"
        if not self._applio_python.exists() or not self._applio_core.exists():
            raise FileNotFoundError(
                f"Applio not installed at {applio}. Run ./scripts/install_rvc.sh."
            )
        self._applio_dir = applio

    def _rvc_convert_sync(self, input_wav: Path, output_wav: Path) -> None:
        """Run Applio RVC inference as subprocess. Blocks until done."""
        cmd = [
            str(self._applio_python),
            str(self._applio_core),
            "infer",
            "--input_path", str(input_wav),
            "--output_path", str(output_wav),
            "--pth_path", str(self._model_path),
            "--index_path", str(self._index_path),
            "--pitch", str(self.rvc.pitch_shift),
            "--index_rate", str(self.rvc.index_rate),
            "--f0_method", self.rvc.f0_method,
            "--embedder_model", self.rvc.embedder_model,
            "--volume_envelope", "1.0",
            "--protect", str(self.rvc.protect),
            "--split_audio", "False",
            "--f0_autotune", "False",
            "--clean_audio", str(self.rvc.clean_audio),
            "--clean_strength", str(self.rvc.clean_strength),
            "--export_format", "WAV",
        ]
        result = subprocess.run(
            cmd,
            cwd=self._applio_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"RVC inference failed (exit {result.returncode}): "
                f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
            )
        if not output_wav.exists():
            raise RuntimeError(f"RVC produced no output at {output_wav}")

    async def synthesize(self, text: str) -> bytes:
        """XTTS → RVC → WAV bytes."""
        # Stage 1: XTTS generates raw cloned voice
        xtts_bytes = await self._xtts.synthesize(text)

        # Stage 2: write to disk, run RVC, read result
        # Both temp files live in the same dir so RVC can resolve relative paths cleanly.
        with tempfile.TemporaryDirectory() as tmp_dir:
            xtts_path = Path(tmp_dir) / "xtts.wav"
            rvc_path = Path(tmp_dir) / "rvc.wav"
            xtts_path.write_bytes(xtts_bytes)

            await asyncio.to_thread(self._rvc_convert_sync, xtts_path, rvc_path)
            audio_bytes = rvc_path.read_bytes()

        logger.info(f"XTTS→RVC: {len(xtts_bytes)} → {len(audio_bytes)} bytes")
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

        logger.info(f"Playing XTTS+RVC to '{device_name}' at {sr}Hz")
        await asyncio.to_thread(sd.play, data, samplerate=sr, device=device_idx)
        await asyncio.to_thread(sd.wait)

    async def stop(self) -> None:
        sd.stop()

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
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device
from saymo.config import F5TTSConfig
from saymo.tts.naturalness import (
    INTER_SENTENCE_PAUSE_S,
    prepare_for_natural_pacing,
    split_for_tts,
)

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
        ref_text: str | None = None,
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
        configured_ref_text = ref_text if ref_text is not None else self.cfg.ref_text
        configured_ref_text = configured_ref_text or ""
        ref_txt_path = self.voice_sample.with_suffix(".txt")
        if configured_ref_text.strip():
            self._ref_text = configured_ref_text.strip()
        elif ref_txt_path.exists():
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

    def _synthesize_chunks_sync(self, chunks: list[str], output_dir: Path) -> list[Path]:
        """Run one F5 CLI process for multiple chunks and return chunk WAVs."""
        cli = self._venv_python.parent / "f5-tts_infer-cli"
        gen_file = output_dir / "gen_chunks.txt"
        gen_file.write_text(
            "\n".join(f"[main]{chunk}" for chunk in chunks),
            encoding="utf-8",
        )
        output_file = "out.wav"
        cmd = [
            str(cli),
            "-m", self.cfg.model_name,
            "-p", str(self._ckpt),
            "-r", str(self.voice_sample),
            "-s", self._ref_text,
            "-f", str(gen_file),
            "-o", str(output_dir),
            "-w", output_file,
            "--save_chunk",
            "--no_legacy_text",
            "--nfe_step", str(self.cfg.nfe_step),
            "--speed", str(self.cfg.speed),
            "--device", self.cfg.device,
        ]
        if self._vocab:
            cmd.extend(["-v", str(self._vocab)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"F5-TTS batch inference failed (exit {result.returncode}): "
                f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
            )

        chunk_dir = output_dir / f"{Path(output_file).stem}_chunks"
        chunk_paths = sorted(
            chunk_dir.glob("*.wav"),
            key=lambda path: _chunk_sort_key(path.name),
        )
        if len(chunk_paths) != len(chunks):
            raise RuntimeError(
                "F5-TTS batch inference produced "
                f"{len(chunk_paths)} chunks for {len(chunks)} requested chunks"
            )
        return chunk_paths

    def _synthesize_raw_sync(self, text: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out = self._synthesize_sync(text, tmp_path)
            audio_bytes = out.read_bytes()
            logger.info(f"F5-TTS generated {len(audio_bytes)} bytes")
            return audio_bytes

    def _synthesize_natural_sync(self, text: str) -> bytes:
        prepared = prepare_for_natural_pacing(
            text,
            clause_pause_seconds=getattr(self.cfg, "clause_pause_seconds", 0.18),
        )
        chunks = split_for_tts(prepared)
        spoken = [chunk for chunk in chunks if isinstance(chunk, str) and chunk]
        has_explicit_pacing = any(
            isinstance(chunk, float) or (isinstance(chunk, str) and chunk == "")
            for chunk in chunks
        )
        if len(spoken) <= 1 and not has_explicit_pacing:
            return self._synthesize_raw_sync(spoken[0] if spoken else text)

        segments: list[np.ndarray | tuple[str, float]] = []
        sample_rate: int | None = None
        spoken_since_breath = 0
        sentence_pause = max(
            0.0,
            float(getattr(self.cfg, "sentence_pause_seconds", INTER_SENTENCE_PAUSE_S)),
        )
        breath_interval = max(
            0,
            int(getattr(self.cfg, "breath_interval_sentences", 0) or 0),
        )
        silent_breath_pause = max(
            0.0,
            float(getattr(self.cfg, "silent_breath_pause_seconds", 0.6)),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            spoken_paths = iter(self._synthesize_chunks_sync(spoken, tmp_path))
            for idx, chunk in enumerate(chunks):
                if isinstance(chunk, float):
                    segments.append(("silence", max(0.0, float(chunk))))
                    continue
                if chunk == "":
                    segments.append(("silence", silent_breath_pause))
                    spoken_since_breath = 0
                    continue

                out = next(spoken_paths)
                audio, sr = _read_wav_mono(out)
                if sample_rate is None:
                    sample_rate = sr
                elif sr != sample_rate:
                    audio = _resample_audio(audio, from_sr=sr, to_sr=sample_rate)
                segments.append(audio)
                spoken_since_breath += 1

                if _next_chunk_is_adjacent_speech(chunks, idx):
                    if breath_interval and spoken_since_breath >= breath_interval:
                        segments.append(("silence", silent_breath_pause))
                        spoken_since_breath = 0
                    else:
                        segments.append(("silence", sentence_pause))

        if sample_rate is None:
            return self._synthesize_raw_sync(text)

        materialized = [
            _materialize_segment(segment, sample_rate=sample_rate)
            for segment in segments
        ]
        audio = np.concatenate(materialized) if materialized else np.zeros(0, dtype=np.float32)
        with io.BytesIO() as buffer:
            sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
            audio_bytes = buffer.getvalue()
        logger.info(
            "F5-TTS natural pacing generated %s bytes from %s spoken chunks",
            len(audio_bytes),
            len(spoken),
        )
        return audio_bytes

    async def synthesize(self, text: str) -> bytes:
        """Clone voice and synthesize text to WAV bytes."""
        if getattr(self.cfg, "natural_pacing", True):
            return await asyncio.to_thread(self._synthesize_natural_sync, text)
        return await asyncio.to_thread(self._synthesize_raw_sync, text)

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


def _read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32), int(sr)


def _resample_audio(
    data: np.ndarray,
    *,
    from_sr: int,
    to_sr: int,
) -> np.ndarray:
    if from_sr <= 0 or to_sr <= 0 or from_sr == to_sr:
        return data.astype(np.float32)
    ratio = to_sr / from_sr
    return np.interp(
        np.arange(int(len(data) * ratio)),
        np.arange(len(data)) * ratio,
        data,
    ).astype(np.float32)


def _next_chunk_is_adjacent_speech(chunks: list[str | float], idx: int) -> bool:
    for later in chunks[idx + 1 :]:
        if isinstance(later, float):
            return False
        if later == "":
            return False
        return True
    return False


def _materialize_segment(
    segment: np.ndarray | tuple[str, float],
    *,
    sample_rate: int,
) -> np.ndarray:
    if isinstance(segment, np.ndarray):
        return segment.astype(np.float32)

    kind, seconds = segment
    if kind == "silence":
        return np.zeros(int(sample_rate * seconds), dtype=np.float32)
    raise ValueError(f"unknown F5 natural pacing segment: {kind}")


def _chunk_sort_key(name: str) -> tuple[int, str]:
    match = re.match(r"(\d+)_", name)
    if match:
        return int(match.group(1)), name
    return 10_000_000, name

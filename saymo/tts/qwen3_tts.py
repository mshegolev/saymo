"""Qwen3-TTS voice cloning engine via MLX.

High-quality voice cloning with streaming support.
Runs natively on Apple Silicon GPU via MLX framework.
"""

import asyncio
import io
import logging
import tempfile
from pathlib import Path

import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.tts.qwen3")

DEFAULT_VOICE_SAMPLE = Path.home() / ".saymo" / "voice_samples" / "voice_sample.wav"
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
DEFAULT_LORA_DIR = Path.home() / ".saymo" / "models" / "qwen3_finetuned"


class Qwen3CloneTTS:
    """Text-to-speech using Qwen3-TTS with voice cloning via MLX.

    Supports:
    - Zero-shot voice cloning from 3-5s reference audio
    - LoRA fine-tuned adapters for maximum similarity
    - Streaming generation for real-time Q&A
    """

    _model = None
    _model_path = None

    def __init__(
        self,
        voice_sample: str | None = None,
        language: str = "ru",
        model: str = DEFAULT_MODEL,
        lora_adapter: str | None = None,
    ):
        self.language = language
        self.voice_sample = Path(voice_sample) if voice_sample else DEFAULT_VOICE_SAMPLE
        self.model_name = model
        self.lora_adapter = lora_adapter

        if not self.voice_sample.exists():
            raise FileNotFoundError(
                f"Voice sample not found: {self.voice_sample}\n"
                f"Record with: saymo record-voice"
            )

    @classmethod
    def _get_model(cls, model_name: str = DEFAULT_MODEL, lora_adapter: str | None = None):
        """Load Qwen3-TTS model via mlx-audio, with optional LoRA adapter."""
        cache_key = f"{model_name}:{lora_adapter or 'base'}"
        if cls._model is not None and cls._model_path == cache_key:
            return cls._model

        from mlx_audio.tts.utils import load_model

        logger.info(f"Loading Qwen3-TTS model: {model_name}")

        if lora_adapter and Path(lora_adapter).exists():
            logger.info(f"Loading LoRA adapter: {lora_adapter}")
            cls._model = load_model(
                model_path=Path(model_name),
                adapter_path=Path(lora_adapter),
            )
        else:
            cls._model = load_model(model_path=Path(model_name))

        cls._model_path = cache_key
        logger.info("Qwen3-TTS loaded")
        return cls._model

    def _synthesize_sync(self, text: str, output_dir: str) -> Path:
        """Synchronous synthesis to file."""
        from mlx_audio.tts.generate import generate_audio

        logger.info(f"Synthesizing {len(text)} chars with Qwen3-TTS")

        # mlx-audio saves to output_path/audio_000.wav (creates directory)
        generate_audio(
            text=text,
            model=self.model_name,
            lang_code=self.language,
            voice="serena",  # required by CustomVoice model, overridden by ref_audio
            ref_audio=str(self.voice_sample),
            output_path=output_dir,
            save=True,
            play=False,
            verbose=False,
        )

        # Find generated file
        out_dir = Path(output_dir)
        wav_files = sorted(out_dir.glob("audio_*.wav"))
        if wav_files:
            return wav_files[0]
        raise FileNotFoundError(f"No audio generated in {output_dir}")

    async def synthesize(self, text: str) -> bytes:
        """Clone voice and synthesize text to WAV bytes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = await asyncio.to_thread(self._synthesize_sync, text, tmp_dir)
            audio_bytes = wav_path.read_bytes()
            logger.info(f"Generated {len(audio_bytes)} bytes")
            return audio_bytes

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

        logger.info(f"Playing Qwen3 voice to '{device_name}' at {sr}Hz")
        await asyncio.to_thread(sd.play, data, samplerate=sr, device=device_idx)
        await asyncio.to_thread(sd.wait)

    async def stop(self) -> None:
        sd.stop()

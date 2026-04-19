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
DEFAULT_FINETUNED_DIR = Path.home() / ".saymo" / "models" / "xtts_finetuned"
XTTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


class _FinetunedTTSWrapper:
    """Wraps a raw Xtts model to match the TTS API interface (tts_to_file)."""

    def __init__(self, model):
        self._model = model

    def tts_to_file(self, text: str, speaker_wav: str, language: str, file_path: str):
        import torch
        import torchaudio

        with torch.no_grad():
            outputs = self._model.synthesize(
                text,
                self._model.config,
                speaker_wav=speaker_wav,
                language=language,
            )
        wav = torch.tensor(outputs["wav"]).unsqueeze(0)
        torchaudio.save(file_path, wav, 22050)


class CoquiCloneTTS:
    """Text-to-speech using XTTS v2 with cloned voice.

    Automatically loads fine-tuned checkpoint if available at
    ~/.saymo/models/xtts_finetuned/. Falls back to base model.
    """

    _model = None  # lazy-loaded, shared across instances
    _model_type = None  # "base" or "finetuned"

    def __init__(
        self,
        voice_sample: str | None = None,
        language: str = "ru",
        use_finetuned: bool = True,
        checkpoint_dir: str | None = None,
    ):
        self.language = language
        self.voice_sample = Path(voice_sample) if voice_sample else DEFAULT_VOICE_SAMPLE
        self.use_finetuned = use_finetuned
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_FINETUNED_DIR

        if not self.voice_sample.exists():
            raise FileNotFoundError(
                f"Voice sample not found: {self.voice_sample}\n"
                f"Record with: saymo record-voice"
            )

    @classmethod
    def _get_model(cls, checkpoint_dir: Path | None = None, use_finetuned: bool = True):
        """Load XTTS v2 model, preferring fine-tuned checkpoint if available."""
        finetuned_dir = checkpoint_dir or DEFAULT_FINETUNED_DIR
        finetuned_model = finetuned_dir / "best_model.pth"
        if not finetuned_model.exists():
            finetuned_model = finetuned_dir / "model.pth"

        want_finetuned = use_finetuned and finetuned_model.exists()

        # Check if we need to reload (model type changed)
        desired_type = "finetuned" if want_finetuned else "base"
        if cls._model is not None and cls._model_type == desired_type:
            return cls._model

        if want_finetuned:
            logger.info(f"Loading fine-tuned XTTS v2 from {finetuned_dir}")
            try:
                # Compatibility patch: transformers >=5.x removed isin_mps_friendly
                import torch
                import transformers.pytorch_utils as _pu
                if not hasattr(_pu, "isin_mps_friendly"):
                    _pu.isin_mps_friendly = torch.isin

                from TTS.tts.configs.xtts_config import XttsConfig
                from TTS.tts.models.xtts import Xtts

                config = XttsConfig()
                config_path = finetuned_dir / "config.json"
                if config_path.exists():
                    config.load_json(str(config_path))

                model = Xtts.init_from_config(config)
                # Load base model first, then override GPT weights
                from TTS.utils.manage import ModelManager
                manager = ModelManager()
                base_dir_path, _, _ = manager.download_model(XTTS_MODEL_NAME)
                base_dir = str(base_dir_path)
                model.load_checkpoint(config, checkpoint_dir=base_dir)

                # Load fine-tuned GPT weights on top
                import torch
                gpt_state = torch.load(str(finetuned_model), map_location="cpu", weights_only=True)
                model.gpt.load_state_dict(gpt_state)
                model.eval()

                # Wrap in TTS-compatible interface
                cls._model = _FinetunedTTSWrapper(model)
                cls._model_type = "finetuned"
                logger.info("Fine-tuned XTTS v2 loaded successfully")
                return cls._model
            except Exception as e:
                logger.warning(f"Failed to load fine-tuned model, falling back to base: {e}")

        # Fall back to base model
        from TTS.api import TTS
        logger.info(f"Loading base XTTS v2 model ({XTTS_MODEL_NAME})...")
        cls._model = TTS(XTTS_MODEL_NAME)
        cls._model_type = "base"
        return cls._model

    def _synthesize_sync(self, text: str, output_path: str) -> str:
        logger.info(f"Synthesizing {len(text)} chars with cloned voice")
        model = self._get_model(self.checkpoint_dir, self.use_finetuned)
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

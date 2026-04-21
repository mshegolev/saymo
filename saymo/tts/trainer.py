"""XTTS v2 fine-tuning on user voice samples.

Fine-tunes only the GPT2 decoder head (~50M params) of XTTS v2,
keeping the audio encoder frozen. This dramatically improves voice
similarity while keeping training fast and memory-efficient.

Target hardware: Apple M1 Pro, 16GB RAM.
Training time: ~2-3 hours on MPS, ~4-6 hours on CPU.
"""

import csv
import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("saymo.tts.trainer")

DEFAULT_MODEL_DIR = Path.home() / ".saymo" / "models" / "xtts_finetuned"
DEFAULT_DATASET_DIR = Path.home() / ".saymo" / "training_dataset"


@dataclass
class TrainingResult:
    """Result of a training run."""

    checkpoint_path: Path
    epochs: int
    final_loss: float
    duration_sec: float
    total_steps: int

    def summary(self) -> str:
        return (
            f"Training complete!\n"
            f"  Checkpoint: {self.checkpoint_path}\n"
            f"  Epochs: {self.epochs}\n"
            f"  Final loss: {self.final_loss:.4f}\n"
            f"  Duration: {self.duration_sec / 60:.1f} min\n"
            f"  Steps: {self.total_steps}"
        )


class VoiceTrainer:
    """Fine-tune XTTS v2 GPT decoder on user voice dataset.

    Uses Coqui TTS Trainer API to fine-tune only the GPT2 decoder head,
    keeping the audio codec (HiFi-GAN) and speaker encoder frozen.

    Usage:
        trainer = VoiceTrainer(dataset_dir, output_dir)
        result = trainer.train(epochs=5)
    """

    def __init__(
        self,
        dataset_dir: Path | None = None,
        output_dir: Path | None = None,
        language: str = "ru",
    ):
        self.dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
        self.output_dir = output_dir or DEFAULT_MODEL_DIR
        self.language = language

        self.wavs_dir = self.dataset_dir / "wavs"
        self.metadata_path = self.dataset_dir / "metadata.csv"
        self.eval_dir = self.dataset_dir / "eval"

    def validate_dataset(self) -> None:
        """Check that training dataset exists and is sufficient."""
        if not self.wavs_dir.exists():
            raise FileNotFoundError(
                f"No training data found at {self.wavs_dir}\n"
                f"Run 'saymo train-prepare' first."
            )

        wav_files = list(self.wavs_dir.glob("*.wav"))
        if len(wav_files) < 10:
            raise ValueError(
                f"Only {len(wav_files)} segments found, need at least 10.\n"
                f"Run 'saymo train-prepare' to record more samples."
            )

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"metadata.csv not found at {self.metadata_path}\n"
                f"Run 'saymo train-prepare' to generate transcriptions."
            )

    def _detect_device(self) -> str:
        """Auto-detect best available compute device.

        Note: MPS (Apple Silicon) has a 65536 output channel limit which
        XTTS v2 GPT exceeds in its embedding layers, so we fall back to CPU.
        CPU training on M1 Pro takes ~4-6 hours for 5 epochs.
        """
        import torch

        if torch.cuda.is_available():
            logger.info("Using CUDA GPU")
            return "cuda"
        else:
            # MPS is not used: XTTS v2 GPT has layers >65536 channels
            # which MPS does not support. CPU on Apple Silicon is still fast.
            logger.info("Using CPU (Apple Silicon optimized)")
            return "cpu"

    def train(
        self,
        epochs: int = 5,
        batch_size: int = 2,
        learning_rate: float = 5e-6,
        resume: bool = False,
        progress_callback=None,
    ) -> TrainingResult:
        """Run XTTS v2 GPT fine-tuning.

        Loads the full XTTS model, freezes everything except GPT,
        and trains on audio-text pairs using the native GPT.forward()
        which returns (loss_text, loss_mel, logits).

        Args:
            epochs: Number of training epochs.
            batch_size: Batch size (unused, processes one sample at a time).
            learning_rate: Learning rate for GPT decoder.
            resume: Resume from last checkpoint.
            progress_callback: Optional callback(epoch, step, loss) for progress.

        Returns:
            TrainingResult with checkpoint path and metrics.
        """
        import torch
        import torchaudio

        # Compatibility patch: transformers >=5.x removed isin_mps_friendly
        # which Coqui TTS still imports. Provide a fallback.
        import transformers.pytorch_utils as _pu
        if not hasattr(_pu, "isin_mps_friendly"):
            _pu.isin_mps_friendly = torch.isin  # type: ignore[attr-defined]

        from TTS.tts.configs.xtts_config import XttsConfig
        from TTS.tts.models.xtts import Xtts
        from TTS.tts.layers.xtts.dvae import DiscreteVAE
        from TTS.tts.layers.tortoise.arch_utils import TorchMelSpectrogram

        self.validate_dataset()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        device = self._detect_device()
        start_time = time.time()

        # Ensure DVAE and mel_stats are available
        dvae_path, mel_stats_path = self._ensure_training_files()

        # Load base XTTS v2 model
        logger.info("Loading XTTS v2 base model for fine-tuning...")
        config = XttsConfig()
        config.load_json(self._get_base_config_path())

        model = Xtts.init_from_config(config)
        model.load_checkpoint(config, checkpoint_dir=self._get_base_model_dir())

        # Load DVAE for audio encoding
        logger.info("Loading DVAE for audio code extraction...")
        # Detect num_tokens from checkpoint to avoid size mismatch
        dvae_state = torch.load(dvae_path, map_location="cpu", weights_only=False)
        # Infer num_tokens from codebook shape
        if "codebook.embed" in dvae_state:
            dvae_num_tokens = dvae_state["codebook.embed"].shape[1]
        else:
            dvae_num_tokens = 1024  # XTTS v2 DVAE default

        dvae = DiscreteVAE(
            channels=80,
            normalization=None,
            positional_dims=1,
            num_tokens=dvae_num_tokens,
            codebook_dim=512,
            hidden_dim=512,
            num_resnet_blocks=3,
            kernel_size=3,
            num_layers=2,
            use_transposed_convs=False,
        )
        dvae.load_state_dict(dvae_state, strict=False)
        dvae.eval()

        # Mel spectrogram extractor for DVAE
        dvae_sr = getattr(config.audio, 'dvae_sample_rate', 22050)
        mel_transform = TorchMelSpectrogram(
            mel_norm_file=mel_stats_path,
            sampling_rate=dvae_sr,
        )

        # Mel spectrogram for conditioning (style encoder)
        cond_mel_transform = TorchMelSpectrogram(
            filter_length=4096,
            hop_length=1024,
            win_length=4096,
            normalize=False,
            sampling_rate=config.audio.sample_rate,
            mel_fmin=0,
            mel_fmax=8000,
            n_mel_channels=80,
            mel_norm_file=mel_stats_path,
        )

        # Freeze everything except GPT decoder
        for param in model.parameters():
            param.requires_grad = False
        for param in model.gpt.parameters():  # type: ignore[union-attr]
            param.requires_grad = True

        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters())
        logger.info(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

        model.to(device)
        dvae.to(device)
        mel_transform.to(device)
        cond_mel_transform.to(device)

        # Load dataset
        train_samples = self._load_samples()
        if not train_samples:
            raise ValueError("No valid training samples in metadata.csv")
        logger.info(f"Train samples: {len(train_samples)}")

        # Optimizer
        optimizer = torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad],
            lr=learning_rate,
            weight_decay=0.01,
        )

        # Pre-compute speaker conditioning from voice sample.
        # CRITICAL: Use a SEPARATE reference recording (voice_sample.wav),
        # NOT the training audio itself. Self-conditioning (using the same
        # audio for both conditioning and target) causes a train/inference
        # mismatch: at inference the model receives voice_sample.wav as
        # reference, but it was never trained with that conditioning signal.
        from saymo.audio.recorder import get_voice_sample_path
        voice_sample = get_voice_sample_path()
        if not voice_sample:
            voice_sample = Path(train_samples[0]["audio_file"])
        logger.info(f"Speaker reference: {voice_sample}")

        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=[str(voice_sample)]
        )

        # Pre-compute conditioning mel from voice_sample (used for ALL training steps).
        # Truncate to ~10 seconds — longer references make GPT attention
        # extremely slow on CPU and don't improve conditioning quality.
        ref_waveform, ref_sr = torchaudio.load(str(voice_sample))
        if ref_sr != 22050:
            ref_waveform = torchaudio.functional.resample(ref_waveform, ref_sr, 22050)
        max_ref_samples = 10 * 22050  # 10 seconds
        if ref_waveform.shape[-1] > max_ref_samples:
            ref_waveform = ref_waveform[..., :max_ref_samples]
            logger.info(f"Truncated reference audio to 10s ({max_ref_samples} samples)")
        ref_waveform = ref_waveform.to(device)
        with torch.no_grad():
            ref_cond_mel = cond_mel_transform(
                ref_waveform.unsqueeze(0) if ref_waveform.dim() == 1 else ref_waveform
            )
            ref_cond_mel = ref_cond_mel.unsqueeze(1)  # (B, 1, n_mel, T)
        logger.info(f"Reference conditioning mel shape: {ref_cond_mel.shape}")

        # Training loop
        total_steps = 0
        losses = []
        best_loss = float("inf")
        model.train()

        for epoch in range(epochs):
            epoch_losses = []
            random.shuffle(train_samples)

            for step, sample in enumerate(train_samples):
                try:
                    wav_path = sample["audio_file"]
                    text = sample["text"]

                    # Load training audio
                    waveform, sr = torchaudio.load(wav_path)
                    if sr != 22050:
                        waveform = torchaudio.functional.resample(waveform, sr, 22050)
                    waveform = waveform.to(device)

                    # Tokenize text
                    text_tokens = torch.IntTensor(
                        model.tokenizer.encode(text, lang=self.language)
                    ).unsqueeze(0).to(device)

                    with torch.no_grad():
                        # Compute mel spectrogram and get DVAE codes from TRAINING audio
                        dvae_mel = mel_transform(waveform.unsqueeze(0) if waveform.dim() == 1 else waveform)
                        audio_codes = dvae.get_codebook_indices(dvae_mel)

                    # GPT forward with REFERENCE conditioning (voice_sample.wav).
                    # This matches inference: model learns to produce this speaker's
                    # voice when conditioned on voice_sample.wav.
                    loss_text, loss_mel, _ = model.gpt(  # type: ignore[misc]
                        text_inputs=text_tokens,
                        text_lengths=torch.tensor([text_tokens.shape[-1]], device=device),
                        audio_codes=audio_codes,
                        wav_lengths=torch.tensor([waveform.shape[-1]], device=device),
                        cond_mels=ref_cond_mel,
                        cond_idxs=None,
                        cond_lens=torch.tensor([ref_cond_mel.shape[-1]], device=device),
                    )

                    loss = loss_text + loss_mel

                    # Backward
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(
                        [p for p in model.parameters() if p.requires_grad],
                        max_norm=1.0,
                    )
                    optimizer.step()

                    loss_val = loss.item()
                    epoch_losses.append(loss_val)
                    total_steps += 1

                    if progress_callback:
                        progress_callback(epoch + 1, step + 1, loss_val)

                    if total_steps % 50 == 0:
                        avg = sum(epoch_losses[-50:]) / min(50, len(epoch_losses))
                        logger.info(f"Epoch {epoch+1}/{epochs} Step {step+1}/{len(train_samples)} Loss: {avg:.4f}")

                except Exception as e:
                    logger.warning(f"Step {step} error: {e}")
                    continue

            # Epoch summary
            if epoch_losses:
                avg_loss = sum(epoch_losses) / len(epoch_losses)
                losses.append(avg_loss)
                logger.info(f"Epoch {epoch+1}/{epochs} complete. Avg loss: {avg_loss:.4f}")

                if avg_loss < best_loss:
                    best_loss = avg_loss
                    self._save_checkpoint(model, config, "best_model.pth")
                    logger.info(f"New best model (loss: {best_loss:.4f})")

            self._save_checkpoint(model, config, f"checkpoint_epoch{epoch+1}.pth")

        # Save final
        self._save_checkpoint(model, config, "model.pth")
        duration = time.time() - start_time

        # Training log
        log = {
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "device": device,
            "total_steps": total_steps,
            "final_loss": losses[-1] if losses else 0.0,
            "loss_history": losses,
            "duration_sec": duration,
            "trainable_params": trainable,
            "total_params": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        (self.output_dir / "training_log.json").write_text(json.dumps(log, indent=2))

        return TrainingResult(
            checkpoint_path=self.output_dir / "best_model.pth",
            epochs=epochs,
            final_loss=losses[-1] if losses else 0.0,
            duration_sec=duration,
            total_steps=total_steps,
        )

    def _load_samples(self, eval_set: bool = False) -> list[dict]:
        """Load training samples from metadata.csv.

        Returns list of dicts with keys: audio_file, text, speaker_name, language, root_path.
        Compatible with Coqui TTS dataset format.
        """
        if eval_set:
            meta_path = self.eval_dir / "metadata.csv"
            wavs_dir = self.eval_dir / "wavs"
        else:
            meta_path = self.metadata_path
            wavs_dir = self.wavs_dir

        if not meta_path.exists():
            return []

        samples = []
        with open(meta_path, newline="") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if len(row) < 2:
                    continue
                filename, text = row[0], row[1]
                wav_path = wavs_dir / f"{filename}.wav"
                if wav_path.exists() and text.strip():
                    samples.append({
                        "audio_file": str(wav_path),
                        "text": text.strip(),
                        "speaker_name": "user",
                        "language": self.language,
                        "root_path": str(wavs_dir.parent),
                    })
        return samples

    def _save_checkpoint(self, model, config, filename: str) -> None:
        """Save model checkpoint."""
        import torch

        checkpoint_path = self.output_dir / filename
        # Save only GPT state dict to save space (~500MB vs ~2GB)
        torch.save(model.gpt.state_dict(), checkpoint_path)

        # Save config alongside
        config_path = self.output_dir / "config.json"
        if not config_path.exists():
            config.save_json(str(config_path))

        logger.info(f"Checkpoint saved: {checkpoint_path}")

    def _get_base_model_dir(self) -> str:
        """Find the base XTTS v2 model directory."""
        from TTS.utils.manage import ModelManager

        manager = ModelManager()
        model_dir, config_path, _ = manager.download_model("tts_models/multilingual/multi-dataset/xtts_v2")
        return str(model_dir)

    def _get_base_config_path(self) -> str:
        """Find the base XTTS v2 config.json."""
        from TTS.utils.manage import ModelManager

        manager = ModelManager()
        model_dir, config_path, _ = manager.download_model("tts_models/multilingual/multi-dataset/xtts_v2")
        return str(config_path)

    def _ensure_training_files(self) -> tuple[str, str]:
        """Download DVAE and mel_stats required for training.

        These are not part of the standard XTTS v2 download but are needed
        to encode audio into VQ-VAE codes for GPT training.

        Returns:
            (dvae_path, mel_stats_path)
        """
        import subprocess

        base_dir = Path(self._get_base_model_dir())
        dvae_path = base_dir / "dvae.pth"
        mel_stats_path = base_dir / "mel_stats.pth"

        base_url = "https://huggingface.co/coqui/XTTS-v2/resolve/main"

        for filename, path in [("dvae.pth", dvae_path), ("mel_stats.pth", mel_stats_path)]:
            if not path.exists():
                url = f"{base_url}/{filename}"
                logger.info(f"Downloading {filename} from HuggingFace...")
                result = subprocess.run(
                    ["curl", "-sL", "-o", str(path), url],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode != 0 or not path.exists():
                    raise RuntimeError(
                        f"Failed to download {filename}: {result.stderr}\n"
                        f"Download manually: curl -L -o '{path}' '{url}'"
                    )
                logger.info(f"Saved {filename} ({path.stat().st_size} bytes)")

        return str(dvae_path), str(mel_stats_path)

    def get_training_status(self) -> dict:
        """Get status of previous training runs."""
        log_path = self.output_dir / "training_log.json"
        if log_path.exists():
            return json.loads(log_path.read_text())

        best = self.output_dir / "best_model.pth"
        if best.exists():
            return {"status": "model exists", "path": str(best)}

        return {"status": "no training done"}

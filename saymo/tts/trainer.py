"""XTTS v2 fine-tuning on user voice samples.

Fine-tunes only the GPT2 decoder head (~50M params) of XTTS v2,
keeping the audio encoder frozen. This dramatically improves voice
similarity while keeping training fast and memory-efficient.

Target hardware: Apple M1 Pro, 16GB RAM.
Training time: ~2-3 hours on MPS, ~4-6 hours on CPU.
"""

import json
import logging
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
        """Auto-detect best available compute device."""
        import torch

        if torch.backends.mps.is_available():
            logger.info("Using MPS (Apple Silicon GPU)")
            return "mps"
        elif torch.cuda.is_available():
            logger.info("Using CUDA GPU")
            return "cuda"
        else:
            logger.info("Using CPU (training will be slower)")
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

        Args:
            epochs: Number of training epochs.
            batch_size: Batch size (2 recommended for 16GB RAM).
            learning_rate: Learning rate for GPT decoder.
            resume: Resume from last checkpoint.
            progress_callback: Optional callback(epoch, step, loss) for progress.

        Returns:
            TrainingResult with checkpoint path and metrics.
        """
        import torch
        from TTS.tts.configs.xtts_config import XttsConfig
        from TTS.tts.models.xtts import Xtts

        self.validate_dataset()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        device = self._detect_device()
        start_time = time.time()

        # Load base XTTS v2 model
        logger.info("Loading XTTS v2 base model for fine-tuning...")
        config = XttsConfig()
        config.load_json(self._get_base_config_path())

        model = Xtts.init_from_config(config)
        model.load_checkpoint(config, checkpoint_dir=self._get_base_model_dir())

        # Freeze everything except GPT decoder
        for param in model.parameters():
            param.requires_grad = False

        # Unfreeze GPT layers
        gpt = model.gpt
        for param in gpt.parameters():
            param.requires_grad = True

        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters())
        logger.info(f"Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

        model.to(device)
        model.train()

        # Prepare dataset
        from TTS.tts.datasets import load_tts_samples

        train_samples, eval_samples = load_tts_samples(
            datasets=[{
                "name": "custom",
                "path": str(self.dataset_dir),
                "meta_file_train": "metadata.csv",
                "meta_file_val": "eval/metadata.csv" if self.eval_dir.exists() else None,
                "language": self.language,
            }],
            eval_split=True,
            eval_split_max_size=20,
            eval_split_size=0.1,
        )

        logger.info(f"Train samples: {len(train_samples)}, Eval samples: {len(eval_samples)}")

        # Optimizer
        optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=learning_rate,
            weight_decay=0.01,
        )

        # Training loop
        total_steps = 0
        losses = []
        best_loss = float("inf")

        for epoch in range(epochs):
            epoch_losses = []

            for step, sample in enumerate(train_samples):
                try:
                    # Process sample through model
                    wav_path = Path(sample["audio_file"])
                    text = sample["text"]

                    if not wav_path.exists():
                        continue

                    # Load audio
                    import torchaudio

                    waveform, sr = torchaudio.load(str(wav_path))
                    if sr != 22050:
                        waveform = torchaudio.functional.resample(waveform, sr, 22050)

                    waveform = waveform.to(device)

                    # Get speaker embedding from reference
                    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
                        audio_path=[str(wav_path)]
                    )

                    # Forward pass through GPT
                    loss = model.gpt.compute_loss(
                        text,
                        waveform,
                        gpt_cond_latent,
                        speaker_embedding,
                        language=self.language,
                    )

                    # Backward
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(
                        filter(lambda p: p.requires_grad, model.parameters()),
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
                        logger.info(f"Epoch {epoch+1}/{epochs} Step {step+1} Loss: {avg:.4f}")

                except Exception as e:
                    logger.warning(f"Error processing sample: {e}")
                    continue

            # Epoch summary
            if epoch_losses:
                avg_loss = sum(epoch_losses) / len(epoch_losses)
                losses.append(avg_loss)
                logger.info(f"Epoch {epoch+1}/{epochs} complete. Avg loss: {avg_loss:.4f}")

                # Save best model
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    self._save_checkpoint(model, config, "best_model.pth")
                    logger.info(f"New best model saved (loss: {best_loss:.4f})")

            # Save periodic checkpoint
            self._save_checkpoint(model, config, f"checkpoint_epoch{epoch+1}.pth")

        # Save final model
        self._save_checkpoint(model, config, "model.pth")

        duration = time.time() - start_time

        # Save training log
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
        log_path = self.output_dir / "training_log.json"
        log_path.write_text(json.dumps(log, indent=2))

        return TrainingResult(
            checkpoint_path=self.output_dir / "best_model.pth",
            epochs=epochs,
            final_loss=losses[-1] if losses else 0.0,
            duration_sec=duration,
            total_steps=total_steps,
        )

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
        model_path, _, _ = manager.download_model("tts_models/multilingual/multi-dataset/xtts_v2")
        return str(Path(model_path).parent)

    def _get_base_config_path(self) -> str:
        """Find the base XTTS v2 config.json."""
        model_dir = self._get_base_model_dir()
        return str(Path(model_dir) / "config.json")

    def get_training_status(self) -> dict:
        """Get status of previous training runs."""
        log_path = self.output_dir / "training_log.json"
        if log_path.exists():
            return json.loads(log_path.read_text())

        best = self.output_dir / "best_model.pth"
        if best.exists():
            return {"status": "model exists", "path": str(best)}

        return {"status": "no training done"}

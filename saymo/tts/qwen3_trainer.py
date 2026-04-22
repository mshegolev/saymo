"""Qwen3-TTS LoRA fine-tuning on user voice samples.

Uses MLX framework for Apple Silicon GPU acceleration.
LoRA adapts only a small subset of parameters (~2-5M),
making training fast (1-2 hours) and memory-efficient.

Based on: github.com/cheeweijie/qwen3-tts-lora-finetuning
"""

import csv
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("saymo.tts.qwen3_trainer")

DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
DEFAULT_ADAPTER_DIR = Path.home() / ".saymo" / "models" / "qwen3_finetuned"
DEFAULT_DATASET_DIR = Path.home() / ".saymo" / "training_dataset"


@dataclass
class Qwen3TrainingResult:
    """Result of a LoRA training run."""

    adapter_path: Path
    epochs: int
    final_loss: float
    duration_sec: float
    total_steps: int

    def summary(self) -> str:
        return (
            f"Training complete!\n"
            f"  Adapter: {self.adapter_path}\n"
            f"  Epochs: {self.epochs}\n"
            f"  Final loss: {self.final_loss:.4f}\n"
            f"  Duration: {self.duration_sec / 60:.1f} min\n"
            f"  Steps: {self.total_steps}"
        )


class Qwen3VoiceTrainer:
    """LoRA fine-tune Qwen3-TTS on user voice dataset.

    Uses mlx-lm LoRA training to adapt the model to a specific voice.
    Only trains ~2-5M parameters (LoRA rank 8), keeping base model frozen.

    Usage:
        trainer = Qwen3VoiceTrainer()
        result = trainer.train(epochs=10)
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        dataset_dir: Path | None = None,
        output_dir: Path | None = None,
        language: str = "ru",
    ):
        self.model_name = model_name
        self.dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
        self.output_dir = output_dir or DEFAULT_ADAPTER_DIR
        self.language = language

        self.wavs_dir = self.dataset_dir / "wavs"
        self.metadata_path = self.dataset_dir / "metadata.csv"

    def validate_dataset(self) -> None:
        """Check that training dataset exists and is sufficient."""
        if not self.wavs_dir.exists():
            raise FileNotFoundError(
                f"No training data at {self.wavs_dir}\n"
                f"Run 'saymo train-prepare' first."
            )

        wav_files = list(self.wavs_dir.glob("*.wav"))
        if len(wav_files) < 10:
            raise ValueError(
                f"Only {len(wav_files)} segments, need at least 10.\n"
                f"Run 'saymo train-prepare' to record more."
            )

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"metadata.csv not found at {self.metadata_path}\n"
                f"Run 'saymo train-prepare' to generate transcriptions."
            )

    def _load_samples(self) -> list[dict]:
        """Load training samples from metadata.csv."""
        samples = []
        with open(self.metadata_path, newline="") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if len(row) < 2:
                    continue
                filename, text = row[0], row[1]
                wav_path = self.wavs_dir / f"{filename}.wav"
                if wav_path.exists() and text.strip():
                    samples.append({
                        "audio_file": str(wav_path),
                        "text": text.strip(),
                    })
        return samples

    def _prepare_training_data(self) -> Path:
        """Convert dataset to JSONL format for mlx-lm LoRA training.

        Each line: {"text": "<prompt>", "audio": "<path_to_wav>"}
        """
        samples = self._load_samples()
        if not samples:
            raise ValueError("No valid samples in metadata.csv")

        train_file = self.dataset_dir / "train.jsonl"
        eval_file = self.dataset_dir / "eval.jsonl"

        # 90/10 split
        n_eval = max(1, len(samples) // 10)

        with open(eval_file, "w") as ef:
            for s in samples[:n_eval]:
                ef.write(json.dumps(s, ensure_ascii=False) + "\n")

        with open(train_file, "w") as tf:
            for s in samples[n_eval:]:
                tf.write(json.dumps(s, ensure_ascii=False) + "\n")

        logger.info(f"Prepared {len(samples)-n_eval} train, {n_eval} eval samples")
        return train_file

    def train(
        self,
        epochs: int = 10,
        lora_rank: int = 8,
        lora_scale: float = 0.3,
        learning_rate: float = 1e-4,
        batch_size: int = 1,
        progress_callback=None,
    ) -> Qwen3TrainingResult:
        """Run LoRA fine-tuning on Qwen3-TTS.

        Args:
            epochs: Number of training epochs.
            lora_rank: LoRA rank (8-16 recommended).
            lora_scale: LoRA alpha scale (0.3-0.35 optimal).
            learning_rate: Learning rate (1e-4 default for LoRA).
            batch_size: Batch size.
            progress_callback: Optional callback(epoch, step, loss).

        Returns:
            Qwen3TrainingResult with adapter path and metrics.
        """
        import mlx.core as mx
        import mlx.nn as nn
        import mlx.optimizers as optim
        import mlx.utils as mlx_utils

        self.validate_dataset()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        logger.info(f"Device: {mx.default_device()}")

        # Load model. Pass as str (not Path) so mlx_audio's load_config
        # routes through get_model_path → snapshot_download from HF. When
        # given a Path, it treats it as local and fails if not cached.
        from mlx_audio.tts.utils import load_model
        logger.info(f"Loading {self.model_name}...")
        model_ref = self.model_name
        if isinstance(model_ref, Path):
            model_ref = str(model_ref)
        # If the string looks like a local directory that exists, keep it
        # as a Path so local checkpoints still work.
        local_candidate = Path(model_ref)
        if local_candidate.exists() and local_candidate.is_dir():
            model = load_model(model_path=local_candidate)
        else:
            model = load_model(model_path=model_ref)  # type: ignore[arg-type]

        # Apply LoRA to model layers
        logger.info(f"Applying LoRA (rank={lora_rank}, scale={lora_scale})...")
        lora_layers = self._apply_lora(model, rank=lora_rank, scale=lora_scale)

        trainable = sum(p.size for _, p in mlx_utils.tree_flatten(lora_layers))  # type: ignore[union-attr]
        total = sum(p.size for _, p in mlx_utils.tree_flatten(model.parameters()))  # type: ignore[union-attr]
        logger.info(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

        # Prepare data
        train_file = self._prepare_training_data()
        samples = self._load_samples()

        # Optimizer
        optimizer = optim.AdamW(learning_rate=learning_rate)

        # Training
        total_steps = 0
        losses = []
        best_loss = float("inf")

        loss_and_grad_fn = nn.value_and_grad(model, self._compute_loss)

        for epoch in range(epochs):
            epoch_losses = []

            for step, sample in enumerate(samples):
                try:
                    loss, grads = loss_and_grad_fn(
                        model, sample["text"], sample["audio_file"]
                    )

                    optimizer.update(model, grads)
                    mx.eval(model.parameters(), optimizer.state)

                    loss_val = loss.item()
                    epoch_losses.append(loss_val)
                    total_steps += 1

                    if progress_callback:
                        progress_callback(epoch + 1, step + 1, loss_val)

                    if total_steps % 50 == 0:
                        avg = sum(epoch_losses[-50:]) / min(50, len(epoch_losses))
                        logger.info(
                            f"Epoch {epoch+1}/{epochs} "
                            f"Step {step+1}/{len(samples)} "
                            f"Loss: {avg:.4f}"
                        )

                except Exception as e:
                    logger.warning(f"Step {step} error: {e}")
                    continue

            if epoch_losses:
                avg_loss = sum(epoch_losses) / len(epoch_losses)
                losses.append(avg_loss)
                logger.info(f"Epoch {epoch+1}/{epochs} complete. Avg loss: {avg_loss:.4f}")

                if avg_loss < best_loss:
                    best_loss = avg_loss
                    self._save_adapter(model, lora_layers, "best_adapter")
                    logger.info(f"New best adapter (loss: {best_loss:.4f})")

        # Save final adapter
        self._save_adapter(model, lora_layers, "adapter")

        duration = time.time() - start_time

        # Training log
        log = {
            "model": self.model_name,
            "method": "lora",
            "epochs": epochs,
            "lora_rank": lora_rank,
            "lora_scale": lora_scale,
            "learning_rate": learning_rate,
            "total_steps": total_steps,
            "final_loss": losses[-1] if losses else 0.0,
            "loss_history": losses,
            "duration_sec": duration,
            "trainable_params": trainable,
            "total_params": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        (self.output_dir / "training_log.json").write_text(json.dumps(log, indent=2))

        return Qwen3TrainingResult(
            adapter_path=self.output_dir / "best_adapter",
            epochs=epochs,
            final_loss=losses[-1] if losses else 0.0,
            duration_sec=duration,
            total_steps=total_steps,
        )

    def _apply_lora(self, model, rank: int = 8, scale: float = 0.3):
        """Apply LoRA adapters to model's linear layers."""
        import mlx.nn as nn
        from mlx_lm.tuner.lora import LoRALinear

        lora_layers = []

        def apply_to_module(module, path=""):
            for name, child in module.named_modules():
                if isinstance(child, nn.Linear):
                    lora = LoRALinear.from_base(
                        child, r=rank, scale=scale
                    )
                    setattr(module, name, lora)
                    lora_layers.append(lora)

        # Apply LoRA to attention layers in the model
        apply_to_module(model)
        model.freeze()
        # Unfreeze only LoRA parameters
        for layer in lora_layers:
            layer.unfreeze()

        return lora_layers

    @staticmethod
    def _compute_loss(model, text, audio_path):
        """Compute loss for a single text-audio pair.

        Tries several common return shapes from Qwen3-TTS forward:

        1. ``{"loss": tensor}`` — HuggingFace-style pre-computed loss.
        2. Object with ``.loss`` attribute — some MLX port variants.
        3. ``{"logits": tensor, "labels": tensor}`` — compute CE ourselves
           against the target audio tokens.
        4. Tuple/list ``(logits, labels)`` — same but positional.

        Raises ``NotImplementedError`` with the observed shape when none
        of these patterns apply — safer than silently optimising a
        meaningless objective like ``mx.mean(output)``.
        """
        import mlx.core as mx
        import mlx.nn as nn

        output = model(text, audio_path)

        # Pattern 1: dict with loss
        if isinstance(output, dict) and "loss" in output:
            return output["loss"]

        # Pattern 2: object with .loss attribute
        if hasattr(output, "loss"):
            loss_attr = getattr(output, "loss", None)
            if loss_attr is not None:
                return loss_attr

        # Pattern 3: dict with logits + labels
        if isinstance(output, dict) and "logits" in output and "labels" in output:
            return nn.losses.cross_entropy(
                output["logits"], output["labels"], reduction="mean"
            )

        # Pattern 4: (logits, labels) tuple/list
        if isinstance(output, (tuple, list)) and len(output) == 2:
            logits, labels = output
            if isinstance(logits, mx.array) and isinstance(labels, mx.array):
                return nn.losses.cross_entropy(logits, labels, reduction="mean")

        raise NotImplementedError(
            f"Qwen3-TTS model.forward() returned an unsupported shape: "
            f"type={type(output).__name__}, "
            f"keys={list(output.keys()) if isinstance(output, dict) else 'n/a'}. "
            f"Extend Qwen3VoiceTrainer._compute_loss to handle it before training."
        )

    def _save_adapter(self, model, lora_layers, name: str) -> None:
        """Save LoRA adapter weights."""
        import mlx.nn as nn

        adapter_path = self.output_dir / name
        adapter_path.mkdir(parents=True, exist_ok=True)

        # Save only LoRA weights
        weights = {}
        for i, layer in enumerate(lora_layers):
            weights[f"lora_{i}_scale"] = layer.scale
            weights[f"lora_{i}_lora_a"] = layer.lora_a
            weights[f"lora_{i}_lora_b"] = layer.lora_b

        import mlx.core as mx
        mx.savez(str(adapter_path / "adapter.npz"), **weights)

        # Save config
        config = {
            "model": self.model_name,
            "num_layers": len(lora_layers),
        }
        (adapter_path / "config.json").write_text(json.dumps(config, indent=2))

        logger.info(f"Adapter saved: {adapter_path}")

    def get_training_status(self) -> dict:
        """Get status of previous training runs."""
        log_path = self.output_dir / "training_log.json"
        if log_path.exists():
            return json.loads(log_path.read_text())

        best = self.output_dir / "best_adapter"
        if best.exists():
            return {"status": "adapter exists", "path": str(best)}

        return {"status": "no training done"}

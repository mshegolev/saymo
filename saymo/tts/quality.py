"""Quality evaluation for voice cloning — A/B comparison and similarity metrics."""

import io
import logging
import random
from pathlib import Path

import sounddevice as sd
import soundfile as sf

logger = logging.getLogger("saymo.tts.quality")


class QualityEvaluator:
    """Compare TTS output between base and fine-tuned XTTS v2 models.

    Generates same sentences with both models, plays for blind comparison,
    and optionally computes speaker embedding cosine similarity.
    """

    def __init__(self, config, model_dir: Path):
        self.config = config
        self.model_dir = model_dir

    def _generate_with_model(self, text: str, use_finetuned: bool) -> bytes:
        """Generate audio for a sentence with specified model variant."""
        from saymo.tts.coqui_clone import CoquiCloneTTS
        from saymo.tts.text_normalizer import normalize_for_tts

        normalized = normalize_for_tts(text)
        tts = CoquiCloneTTS(
            use_finetuned=use_finetuned,
            checkpoint_dir=str(self.model_dir),
        )

        import asyncio
        return asyncio.run(tts.synthesize(normalized))

    def _play_audio(self, audio_bytes: bytes) -> None:
        """Play audio bytes to configured device."""
        data, sr = sf.read(io.BytesIO(audio_bytes))

        from saymo.audio.devices import find_device
        dev = find_device(self.config.audio.playback_device, kind="output")
        device_idx = dev.index if dev else None

        sd.play(data, samplerate=sr, device=device_idx)
        sd.wait()

    def evaluate_interactive(self, sentences: list[str]) -> dict:
        """Run interactive A/B blind listening test.

        For each sentence:
        1. Generate audio with base and fine-tuned model
        2. Play in randomized order (A/B)
        3. Ask user which sounds more natural
        4. Tally results

        Returns:
            Dict with evaluation results.
        """
        from rich.console import Console
        console = Console()

        results = {
            "total": len(sentences),
            "finetuned_preferred": 0,
            "base_preferred": 0,
            "same": 0,
            "avg_similarity": None,
            "avg_similarity_base": None,
        }

        for i, sentence in enumerate(sentences):
            console.print(f"\n[bold cyan]Sentence {i+1}/{len(sentences)}:[/] {sentence}")
            console.print("[dim]Generating...[/]")

            try:
                # Generate both versions
                base_audio = self._generate_with_model(sentence, use_finetuned=False)
                ft_audio = self._generate_with_model(sentence, use_finetuned=True)

                # Randomize order
                is_a_finetuned = random.choice([True, False])
                a_audio = ft_audio if is_a_finetuned else base_audio
                b_audio = base_audio if is_a_finetuned else ft_audio

                # Play A
                console.print("[bold yellow][A][/] Playing...")
                self._play_audio(a_audio)

                # Play B
                console.print("[bold yellow][B][/] Playing...")
                self._play_audio(b_audio)

                # Ask preference
                console.print("[bold]Which sounds more like you? [a/b/s(ame)/r(eplay)][/]")

                while True:
                    choice = input().strip().lower()
                    if choice == "r":
                        console.print("[yellow][A][/] Replaying...")
                        self._play_audio(a_audio)
                        console.print("[yellow][B][/] Replaying...")
                        self._play_audio(b_audio)
                        console.print("[bold]Choice? [a/b/s/r][/]")
                        continue
                    if choice in ("a", "b", "s"):
                        break
                    console.print("[dim]Enter a, b, s (same), or r (replay)[/]")

                if choice == "s":
                    results["same"] += 1
                elif (choice == "a" and is_a_finetuned) or (choice == "b" and not is_a_finetuned):
                    results["finetuned_preferred"] += 1
                    console.print("[green]Fine-tuned model selected[/]")
                else:
                    results["base_preferred"] += 1
                    console.print("[yellow]Base model selected[/]")

            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
                continue

        return results

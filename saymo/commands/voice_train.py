"""Voice-cloning / training commands.

record-voice, test-voice-sample, train-prepare, train-rebuild, train-status,
train-voice, train-eval.
"""

import click
from rich.table import Table

from saymo.commands import console, main


@main.command("record-voice")
@click.option("--duration", "-d", default=30, help="Recording duration in seconds")
@click.option("--output", "-o", default=None, help="Output WAV file path")
@click.pass_context
def record_voice(ctx, duration, output):
    """Record a voice sample for voice cloning.

    Uses the Plantronics mic (or configured capture device).
    Recommended: 30-60 seconds of natural speech in Russian.
    """
    import sounddevice as sd

    from saymo.audio.recorder import record_sample
    from saymo.audio.devices import find_device

    config = ctx.obj["config"]

    # Use configured recording device, or fall back to system default
    mic_name: str = config.audio.recording_device or ""
    mic = find_device(mic_name, kind="input") if mic_name else None
    if not mic:
        default_dev = sd.query_devices(kind="input")
        if isinstance(default_dev, dict):
            default_name = str(default_dev["name"])
            if mic_name:
                console.print(f"[yellow]'{mic_name}' not found, using default: {default_name}[/]")
            else:
                console.print(f"[yellow]No recording device configured, using default: {default_name}[/]")
            mic_name = default_name
            mic = find_device(mic_name, kind="input")
        else:
            console.print("[bold red]No input devices found![/]")
            return

    console.print(f"[bold blue]Recording voice sample[/]")
    console.print(f"  Mic: {mic_name}")
    console.print(f"  Duration: {duration}s")
    console.print(f"  Tip: Speak naturally in Russian. Read aloud or talk about your day.")
    console.print()
    console.print("[bold yellow]Recording starts in 3 seconds...[/]")

    import time
    for i in range(3, 0, -1):
        console.print(f"  {i}...")
        time.sleep(1)

    console.print("[bold red]RECORDING![/]")

    try:
        from saymo.audio.mic_processor import MicProcessor

        processor = MicProcessor.from_config(config.audio, sample_rate=22050)
        if not processor.is_noop():
            console.print(
                f"[dim]Mic chain: gain {processor.gain_db:+.1f} dB, "
                f"gate {processor.noise_gate_db:.0f} dB, "
                f"highpass {processor.highpass_cutoff_hz:.0f} Hz, "
                f"denoise {'on' if processor.noise_reduction else 'off'}[/]"
            )
        path = record_sample(
            device_name=mic_name,
            duration=duration,
            sample_rate=22050,
            output_path=output,
            processor=processor,
        )
        console.print(f"\n[bold green]Saved:[/] {path}")
        console.print(f"[blue]Size: {path.stat().st_size / 1024:.0f} KB[/]")
        console.print(f"\nTo use as voice clone: set tts.engine to 'coqui_clone' in config.yaml")
    except Exception as e:
        console.print(f"[bold red]Recording failed:[/] {e}")


@main.command("test-voice-sample")
@click.pass_context
def test_voice_sample(ctx):
    """Play back the recorded voice sample to verify quality."""
    from saymo.audio.recorder import get_voice_sample_path

    path = get_voice_sample_path()
    if not path:
        console.print("[yellow]No voice sample found. Run 'saymo record-voice' first.[/]")
        return

    console.print(f"[blue]Playing: {path}[/]")
    config = ctx.obj["config"]

    import sounddevice as sd
    import soundfile as sf

    data, sr = sf.read(str(path))
    device = None
    # Try to find the playback device
    from saymo.audio.devices import find_device
    dev = find_device(config.audio.playback_device, kind="output")
    if dev:
        device = dev.index

    sd.play(data, samplerate=sr, device=device)
    sd.wait()
    console.print("[green]Done![/]")


# ---------------------------------------------------------------------------
# Voice training commands
# ---------------------------------------------------------------------------

@main.command("train-prepare")
@click.option("--duration", "-d", default=1800, help="Max total recording duration in seconds")
@click.option("--resume", "-r", is_flag=True, help="Resume interrupted recording session")
@click.option("--category", type=click.Choice(["standup", "qa", "general", "it"]),
              default=None, help="Prompt category (default: all)")
@click.option("--extra", "-e", "extra_file", type=click.Path(), default=None,
              help="Append prompts from a text file (one per line). Useful for mixing in your own domain sentences.")
@click.option("--only-extra", is_flag=True,
              help="Use ONLY the --extra file, skipping the default prompt set.")
@click.option("--dataset-dir", type=click.Path(), default=None,
              help="Write recordings to a custom dataset dir (default: ~/.saymo/training_dataset/). "
                   "Use a different name for a parallel dataset, e.g. ~/.saymo/training_dataset_bigdata.")
@click.pass_context
def train_prepare(ctx, duration, resume, category, extra_file, only_extra, dataset_dir):
    """Record training samples with guided prompts for voice fine-tuning.

    Shows prompts one by one. Read each prompt aloud naturally.
    Press Ctrl+C to stop early (progress is saved for --resume).
    """
    import sounddevice as sd

    from saymo.audio.devices import find_device
    from saymo.audio.mic_processor import MicProcessor
    from saymo.tts.prompts import get_prompts
    from saymo.tts.dataset import DatasetBuilder
    from saymo.commands.tests import _read_prompts_file

    config = ctx.obj["config"]
    prompts = [] if only_extra else list(get_prompts(category))
    if extra_file:
        from pathlib import Path
        extra = _read_prompts_file(Path(extra_file))
        if not extra:
            console.print(f"[yellow]No prompts read from {extra_file} — skipping[/]")
        else:
            console.print(f"[blue]+{len(extra)} personal prompts from {extra_file}[/]")
            prompts.extend(extra)
    if not prompts:
        console.print("[bold red]No prompts to record — check --category / --extra[/]")
        return
    processor = MicProcessor.from_config(config.audio, sample_rate=22050)

    # Detect mic
    mic_name: str = config.audio.recording_device or ""
    mic = find_device(mic_name, kind="input") if mic_name else None
    if not mic:
        default_dev = sd.query_devices(kind="input")
        if isinstance(default_dev, dict):
            mic_name = str(default_dev["name"])
            console.print(f"[yellow]Using default mic: {mic_name}[/]")
        else:
            console.print("[bold red]No input devices found![/]")
            return

    console.print(f"[bold blue]Voice Training — Dataset Preparation[/]")
    console.print(f"  Prompts: {len(prompts)} ({category or 'all categories'})")
    console.print(f"  Mic: {mic_name}")
    console.print(f"  Max duration: {duration}s")
    console.print()
    console.print("[dim]Read each prompt aloud naturally. Press Enter to start, Ctrl+C to stop.[/]")

    # Rendering imports — big live banner while recording, clear rule between prompts.
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text

    recorded = []

    from pathlib import Path as _Path
    dataset_root = _Path(dataset_dir).expanduser() if dataset_dir else _Path.home() / ".saymo" / "training_dataset"
    raw_dir = dataset_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[dim]Dataset dir: {dataset_root}[/]")

    try:

        quit_requested = False
        i = 0
        while i < len(prompts):
            prompt = prompts[i]
            # Check if already recorded (resume mode)
            wav_path = raw_dir / f"{i:04d}.wav"

            if resume and wav_path.exists() and wav_path not in recorded:
                recorded.append(wav_path)
                i += 1
                continue

            console.print()
            console.rule(
                f"[bold cyan]Prompt {i+1}/{len(prompts)}  ·  saved: {len(recorded)}",
                style="cyan",
            )
            console.print()
            console.print(f"  [bold]{prompt}[/]")
            console.print()
            # Adaptive per-prompt cap: ~0.45 s per word + 2 s slack, floor 4 s, cap 20 s.
            words = max(1, len(prompt.split()))
            adaptive_cap = int(min(20, max(4, words * 0.45 + 2)))
            can_redo_prev = i > 0
            controls = (
                "  [dim]press Enter → start (max {cap}s)   "
                "Enter again → stop   "
                "[yellow]s[/] → skip   "
                "[red]q[/] → quit"
                + ("   [magenta]r[/] → redo previous prompt" if can_redo_prev else "")
                + "[/]"
            ).format(cap=adaptive_cap)
            console.print(controls)

            try:
                user_input = input("  > ").strip().lower()
            except EOFError:
                break
            if user_input == "q":
                quit_requested = True
                break
            if user_input == "s":
                console.print("  [yellow]· skipped[/]")
                i += 1
                continue
            if user_input == "r" and can_redo_prev:
                prev_path = raw_dir / f"{i-1:04d}.wav"
                try:
                    prev_path.unlink()
                except FileNotFoundError:
                    pass
                if recorded and recorded[-1] == prev_path:
                    recorded.pop()
                console.print(f"  [magenta]↶ rewinding to prompt {i}[/]")
                i -= 1
                continue

            # Small breath before recording starts so the mic does not
            # catch the Enter-key click.
            import time as _t
            _t.sleep(0.35)

            import numpy as np
            import threading

            mic_dev = find_device(mic_name, kind="input")
            if mic_dev is None:
                console.print("[bold red]Mic lost[/]")
                break

            chunks: list[np.ndarray] = []
            stop_event = threading.Event()

            def _stopper():
                try:
                    input()
                except EOFError:
                    pass
                stop_event.set()

            stopper_thread = threading.Thread(target=_stopper, daemon=True)
            stopper_thread.start()

            def _cb(indata, frames, time_info, status):
                if status:
                    pass
                chunks.append(indata.copy().flatten())
                if stop_event.is_set():
                    raise sd.CallbackStop

            def _render_banner(elapsed: float, cap: float, phase: int) -> Panel:
                # Alternate two loud styles to fake a blink on terminals that
                # do not honour the ANSI blink attribute (most modern ones).
                if phase % 2 == 0:
                    body_style = "bold white on red"
                    dot = "●"
                else:
                    body_style = "bold yellow on red"
                    dot = "○"
                remaining = max(0.0, cap - elapsed)
                text = Text(
                    f"{dot}  SPEAK NOW   —   {elapsed:0.1f}s elapsed   —   "
                    f"{remaining:0.1f}s left   —   press Enter to stop",
                    style=body_style,
                    justify="center",
                )
                return Panel(text, border_style="bright_red", padding=(0, 1))

            try:
                with sd.InputStream(
                    samplerate=22050,
                    channels=1,
                    dtype="int16",
                    device=mic_dev.index,
                    callback=_cb,
                ):
                    start = _t.time()
                    phase = 0
                    # Transient so the banner clears when the block exits —
                    # final output is just the tidy "saved N.Xs" line.
                    with Live(
                        _render_banner(0.0, float(adaptive_cap), phase),
                        console=console,
                        refresh_per_second=8,
                        transient=True,
                    ) as live:
                        while not stop_event.is_set() and _t.time() - start < adaptive_cap:
                            elapsed = _t.time() - start
                            phase = int(elapsed * 2.5)  # flip twice per second
                            live.update(_render_banner(elapsed, float(adaptive_cap), phase))
                            _t.sleep(0.1)
                    stop_event.set()
            except Exception as e:
                console.print(f"  [red]capture error: {e}[/]")
                continue

            audio = (
                np.concatenate(chunks).astype(np.int16)
                if chunks
                else np.array([], dtype=np.int16)
            )

            # Mic input chain (gain / gate / high-pass / denoise)
            if not processor.is_noop():
                audio = processor.process_int16(audio)

            # Trim silence
            from saymo.audio.recorder import _trim_silence
            audio = _trim_silence(audio)

            # Save
            import wave as wave_mod
            with wave_mod.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(22050)
                wf.writeframes(audio.tobytes())

            dur = len(audio) / 22050
            console.print(
                f"  [green]✓ saved {dur:.1f}s[/] → {wav_path.name}   "
                f"[dim]({len(recorded) + 1}/{len(prompts)})[/]"
            )
            recorded.append(wav_path)

            # Post-save review — allow the user to redo the take they just
            # made without advancing. 'p' replays the file so the user can
            # verify mic calibration by ear. Blank line / Enter accepts
            # and moves on. 'q' quits the whole session.
            redo = False
            while True:
                try:
                    review = input(
                        "  [Enter] keep & next   [p] play back   "
                        "[r] redo this one   [q] quit: "
                    ).strip().lower()
                except EOFError:
                    review = ""
                if review == "p":
                    try:
                        import soundfile as _sf
                        data, sr_play = _sf.read(str(wav_path))
                        # Monitor device if configured, else playback device,
                        # else system default. Matches the same resolution
                        # logic used by `saymo test-voice-sample`.
                        mon_name = (
                            config.audio.monitor_device
                            or config.audio.playback_device
                            or None
                        )
                        out_dev = find_device(mon_name, kind="output") if mon_name else None
                        out_idx = out_dev.index if out_dev else None
                        console.print(
                            f"  [blue]♪ playing {dur:.1f}s on {mon_name or 'default'}[/]"
                        )
                        sd.play(data, samplerate=sr_play, device=out_idx)
                        sd.wait()
                    except Exception as e:
                        console.print(f"  [red]playback error: {e}[/]")
                    continue  # re-ask the review question
                if review == "r":
                    try:
                        wav_path.unlink()
                    except FileNotFoundError:
                        pass
                    if recorded and recorded[-1] == wav_path:
                        recorded.pop()
                    console.print("  [magenta]↶ redo[/]")
                    redo = True
                if review == "q":
                    quit_requested = True
                break
            if redo:
                continue  # do not advance i — loop re-records same prompt
            if quit_requested:
                break

            i += 1

        if quit_requested:
            pass  # fall through to post-loop summary

    except KeyboardInterrupt:
        console.print("\n[yellow]Recording interrupted. Use --resume to continue later.[/]")

    if not recorded:
        console.print("[yellow]No samples recorded.[/]")
        return

    console.print(f"\n[bold green]Recorded {len(recorded)} samples[/]")

    # Build dataset with ground-truth transcriptions (not Whisper!)
    console.print("\n[blue]Building dataset with ground-truth prompts...[/]")
    try:
        builder = DatasetBuilder(
            raw_dir=dataset_root / "raw",
            output_dir=dataset_root,
        )
        # Map each recorded file to its original prompt by filename index.
        # This gives XTTS v2 correct text-audio alignment instead of
        # relying on Whisper which mangles Russian IT vocabulary.
        prompt_texts = [prompts[int(p.stem)] for p in recorded if int(p.stem) < len(prompts)]
        report = builder.build(prompts=prompt_texts)
        console.print(f"\n[bold green]Dataset ready at {dataset_root}![/]")
        console.print(report.summary())
    except Exception as e:
        console.print(f"[bold red]Dataset build failed:[/] {e}")
        console.print(
            f"[dim]You can run 'saymo train-prepare --resume "
            f"--dataset-dir {dataset_root}' to continue.[/]"
        )


@main.command("train-rebuild")
@click.pass_context
def train_rebuild(ctx):
    """Rebuild dataset from existing raw recordings with correct transcriptions.

    Uses the original prompts from prompts.py as ground-truth text instead
    of Whisper (which produces poor transcriptions for Russian IT vocabulary).
    No re-recording needed — just rebuilds metadata.csv from raw/ files.
    """
    from saymo.tts.dataset import DatasetBuilder
    from saymo.tts.prompts import all_prompts
    from pathlib import Path

    raw_dir = Path.home() / ".saymo" / "training_dataset" / "raw"
    raw_files = sorted(raw_dir.glob("*.wav")) if raw_dir.exists() else []

    if not raw_files:
        console.print("[bold red]No raw recordings found. Run 'saymo train-prepare' first.[/]")
        return

    prompts = all_prompts()

    # Match prompts to raw files by index (0000.wav → prompt[0], etc.)
    matched_prompts = []
    for f in raw_files:
        idx = int(f.stem)
        if idx < len(prompts):
            matched_prompts.append(prompts[idx])
        else:
            console.print(f"[yellow]Warning: {f.name} has no matching prompt (idx={idx}), skipping[/]")

    if len(matched_prompts) != len(raw_files):
        console.print(f"[yellow]Matched {len(matched_prompts)}/{len(raw_files)} files to prompts[/]")
        # Filter raw_files to only those with matching prompts
        raw_files = [f for f in raw_files if int(f.stem) < len(prompts)]

    console.print(f"[bold blue]Rebuilding dataset[/]")
    console.print(f"  Raw files: {len(raw_files)}")
    console.print(f"  Prompts: {len(matched_prompts)}")
    console.print(f"  Mode: ground-truth transcriptions (no Whisper)")
    console.print()

    builder = DatasetBuilder()
    try:
        report = builder.build(prompts=matched_prompts)
        console.print(f"\n[bold green]Dataset rebuilt![/]")
        console.print(report.summary())
        console.print()
        console.print("[dim]Now run 'saymo train-voice --epochs 5' to retrain.[/]")
    except Exception as e:
        console.print(f"[bold red]Rebuild failed:[/] {e}")


@main.command("train-status")
@click.pass_context
def train_status(ctx):
    """Show training dataset and model status."""
    from saymo.tts.dataset import DatasetBuilder

    builder = DatasetBuilder()
    status = builder.get_status()

    console.print("[bold blue]Voice Training Status[/]\n")

    # Dataset info
    table = Table(title="Dataset")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Raw recordings", str(status["raw_files"]))
    table.add_row("Segments", str(status["segments"]))
    table.add_row("Duration", f"{status['duration_sec'] / 60:.1f} min")
    table.add_row("Metadata", "Yes" if status["has_metadata"] else "No")
    table.add_row("Fine-tuned model", "Yes" if status["has_model"] else "No")

    console.print(table)

    # Training log
    if "last_report" in status:
        r = status["last_report"]
        console.print(f"\n[dim]Last build: {r.get('good_segments', '?')} good segments, "
                      f"ready: {r.get('ready', '?')}[/]")

    # Training results
    from saymo.tts.trainer import VoiceTrainer
    trainer = VoiceTrainer()
    train_status_data = trainer.get_training_status()

    if "epochs" in train_status_data:
        console.print(f"\n[bold]Last training:[/]")
        console.print(f"  Epochs: {train_status_data['epochs']}")
        console.print(f"  Final loss: {train_status_data.get('final_loss', '?'):.4f}")
        console.print(f"  Duration: {train_status_data.get('duration_sec', 0) / 60:.1f} min")
        console.print(f"  Device: {train_status_data.get('device', '?')}")
        console.print(f"  Timestamp: {train_status_data.get('timestamp', '?')}")

    # Recommendations
    console.print()
    if not status["has_metadata"]:
        console.print("[yellow]Next step: run 'saymo train-prepare' to record training data[/]")
    elif not status["has_model"]:
        if status["segments"] >= 50:
            console.print("[green]Dataset ready! Run 'saymo train-voice' to start fine-tuning[/]")
        else:
            console.print(f"[yellow]Need more data: {status['segments']}/50 segments. "
                          f"Run 'saymo train-prepare --resume' to add more.[/]")
    else:
        console.print("[green]Fine-tuned model available. Run 'saymo train-eval' to evaluate.[/]")


@main.command("train-voice")
@click.option("--epochs", "-e", default=None, type=int, help="Number of training epochs")
@click.option("--batch-size", "-b", default=2, help="Batch size (2 for 16GB RAM)")
@click.option("--resume", "-r", is_flag=True, help="Resume from last checkpoint")
@click.option("--engine", default=None, type=click.Choice(["xtts", "qwen3"]),
              help="Training engine (default: auto-detect from tts.engine)")
@click.pass_context
def train_voice(ctx, epochs, batch_size, resume, engine):
    """Fine-tune voice model on your samples.

    Supports XTTS v2 (GPT decoder) and Qwen3-TTS (LoRA).
    Engine auto-detected from config tts.engine, or specify --engine.
    """
    from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
    from saymo.tts.dataset import DatasetBuilder

    config = ctx.obj["config"]
    tc = config.tts.voice_training

    # Determine engine
    if engine is None:
        engine = "qwen3" if config.tts.engine == "qwen3_clone" else "xtts"

    from pathlib import Path
    dataset_dir = Path(tc.dataset_dir) if tc.dataset_dir else None

    # Validate dataset
    builder = DatasetBuilder(raw_dir=dataset_dir / "raw" if dataset_dir else None,
                             output_dir=dataset_dir)
    status = builder.get_status()

    if status["segments"] < 10:
        console.print(f"[bold red]Insufficient training data: {status['segments']} segments (need 10+)[/]")
        console.print("[yellow]Run 'saymo train-prepare' first.[/]")
        return

    if engine == "qwen3":
        # Qwen3-TTS LoRA fine-tuning
        default_epochs = epochs or config.tts.qwen3.lora_epochs or 10
        console.print("[bold blue]Qwen3-TTS LoRA Fine-Tuning[/]\n")
        console.print(f"  Model: {config.tts.qwen3.model}")
        console.print(f"  Dataset: {status['segments']} segments, {status['duration_sec']/60:.1f} min")
        console.print(f"  Epochs: {default_epochs}")
        console.print(f"  LoRA rank: {config.tts.qwen3.lora_rank}")
        console.print(f"  LoRA scale: {config.tts.qwen3.lora_scale}")
        console.print()

        from saymo.tts.qwen3_trainer import Qwen3VoiceTrainer
        trainer = Qwen3VoiceTrainer(
            model_name=config.tts.qwen3.model,
            dataset_dir=dataset_dir,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            task = progress.add_task("Training", total=default_epochs)
            current_epoch = [0]

            def on_progress(epoch, step, loss):
                if epoch > current_epoch[0]:
                    current_epoch[0] = epoch
                    progress.update(task, advance=1,
                                    description=f"Epoch {epoch}/{default_epochs} loss={loss:.4f}")

            try:
                result = trainer.train(
                    epochs=default_epochs,
                    lora_rank=config.tts.qwen3.lora_rank,
                    lora_scale=config.tts.qwen3.lora_scale,
                    progress_callback=on_progress,
                )
                console.print(f"\n[bold green]{result.summary()}[/]")
                console.print(f"\n[dim]Set tts.qwen3.lora_adapter in config.yaml to use.[/]")
            except Exception as e:
                console.print(f"\n[bold red]Training failed:[/] {e}")
        return

    # XTTS v2 fine-tuning (default)
    default_epochs = epochs or tc.epochs or 5
    model_dir = Path(tc.model_dir) if tc.model_dir else None

    console.print("[bold blue]XTTS v2 Voice Fine-Tuning[/]\n")
    console.print(f"  Dataset: {status['segments']} segments, {status['duration_sec']/60:.1f} min")
    console.print(f"  Epochs: {default_epochs}")
    console.print(f"  Batch size: {batch_size}")
    console.print(f"  Learning rate: {tc.learning_rate}")
    console.print()

    from saymo.tts.trainer import VoiceTrainer
    trainer = VoiceTrainer(dataset_dir=dataset_dir, output_dir=model_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
    ) as progress:
        task = progress.add_task("Training", total=default_epochs)
        current_epoch = [0]

        def on_progress(epoch, step, loss):
            if epoch > current_epoch[0]:
                current_epoch[0] = epoch
                progress.update(task, advance=1,
                                description=f"Epoch {epoch}/{default_epochs} loss={loss:.4f}")

        try:
            result = trainer.train(
                epochs=default_epochs,
                batch_size=batch_size,
                learning_rate=tc.learning_rate,
                resume=resume,
                progress_callback=on_progress,
            )
            console.print(f"\n[bold green]{result.summary()}[/]")
            console.print(f"\n[dim]Run 'saymo train-eval' to evaluate quality.[/]")

        except Exception as e:
            console.print(f"\n[bold red]Training failed:[/] {e}")
            console.print("[dim]Try: --batch-size 1, or check memory with Activity Monitor.[/]")


@main.command("train-eval")
@click.option("--sentences", "-s", default=None, help="Custom test sentences (comma-separated)")
@click.pass_context
def train_eval(ctx, sentences):
    """Evaluate fine-tuned voice model with A/B comparison.

    Generates test sentences with both base and fine-tuned models,
    plays them for blind comparison, and computes similarity metrics.
    """
    from pathlib import Path

    config = ctx.obj["config"]
    tc = config.tts.voice_training
    model_dir = Path(tc.model_dir) if tc.model_dir else Path.home() / ".saymo" / "models" / "xtts_finetuned"

    if not (model_dir / "best_model.pth").exists() and not (model_dir / "model.pth").exists():
        console.print("[bold red]No fine-tuned model found.[/]")
        console.print("[yellow]Run 'saymo train-voice' first.[/]")
        return

    from saymo.tts.quality import QualityEvaluator

    # Test sentences
    if sentences:
        test_sentences = [s.strip() for s in sentences.split(",")]
    else:
        test_sentences = [
            "Добрый день, коллеги. Вчера я работал над автотестами.",
            "Сегодня планирую провести ревью и подготовить релиз.",
            "Блокеров нет, все задачи идут по плану.",
            "Ориентируюсь закончить задачу сегодня к вечеру.",
            "Нужно обновить конфигурацию на стейдже перед деплоем.",
            "Провёл анализ логов, нашёл три паттерна ошибок.",
            "Автотесты прошли успешно на UAT окружении.",
            "Хотфикс уже применён и работает корректно.",
            "Задеплоил новую версию пайплайна на стейдж.",
            "Документация обновлена в конфлюенсе.",
        ]

    evaluator = QualityEvaluator(config=config, model_dir=model_dir)

    console.print("[bold blue]Voice Quality Evaluation[/]\n")
    console.print(f"Test sentences: {len(test_sentences)}")
    console.print("[dim]Generating audio with both models...[/]\n")

    try:
        report = evaluator.evaluate_interactive(test_sentences)
        console.print(f"\n[bold green]Results:[/]")
        console.print(f"  Fine-tuned preferred: {report['finetuned_preferred']}/{report['total']} "
                      f"({100*report['finetuned_preferred']/report['total']:.0f}%)")
        console.print(f"  Base preferred: {report['base_preferred']}/{report['total']}")
        console.print(f"  Same: {report['same']}/{report['total']}")
        if report.get("avg_similarity"):
            console.print(f"  Avg similarity (fine-tuned): {report['avg_similarity']:.3f}")
            console.print(f"  Avg similarity (base): {report['avg_similarity_base']:.3f}")
    except Exception as e:
        console.print(f"[bold red]Evaluation failed:[/] {e}")

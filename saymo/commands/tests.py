"""Diagnostic / info commands: test-devices, test-tts, test-jira, list-plugins,
test-notes, test-compose, test-ollama, prepare-responses, mic-check."""

import click
from rich.table import Table

from saymo.commands import console, main, run_async


@main.command("test-devices")
def test_devices():
    """List all audio devices and check BlackHole availability."""
    from saymo.audio.devices import list_devices, find_blackhole_devices

    table = Table(title="Audio Devices")
    table.add_column("#", style="dim")
    table.add_column("Name")
    table.add_column("In", justify="center")
    table.add_column("Out", justify="center")
    table.add_column("Sample Rate")

    for dev in list_devices():
        table.add_row(
            str(dev.index),
            dev.name,
            str(dev.max_input_channels) if dev.max_input_channels > 0 else "-",
            str(dev.max_output_channels) if dev.max_output_channels > 0 else "-",
            str(int(dev.default_samplerate)),
        )

    console.print(table)

    bh = find_blackhole_devices()
    if bh:
        console.print(f"\n[bold green]BlackHole devices found:[/] {', '.join(bh.keys())}")
    else:
        console.print("\n[bold red]No BlackHole devices found![/]")
        console.print("Install with: brew install blackhole-2ch blackhole-16ch")


@main.command("test-tts")
@click.argument("text", default="Привет, это тестовое сообщение от Saymo.")
@click.option("--engine", "-e", default=None, help="TTS engine: openai, macos_say")
@click.pass_context
def test_tts(ctx, text, engine):
    """Test TTS by speaking a phrase to the configured device."""
    config = ctx.obj["config"]
    if engine:
        config.tts.engine = engine
    run_async(_test_tts(config, text))


async def _test_tts(config, text):
    from saymo.tts.factory import get_tts_engine, UnsupportedTTSEngine

    console.print(f"[blue]TTS engine: {config.tts.engine}[/]")
    console.print(f"[blue]Text: {text}[/]")
    console.print(f"[blue]Device: {config.audio.playback_device}[/]")

    try:
        tts = get_tts_engine(config)
    except UnsupportedTTSEngine as e:
        console.print(f"[bold red]{e}[/]")
        return

    if hasattr(tts, "synthesize_to_device"):
        await tts.synthesize_to_device(text, config.audio.playback_device)
    else:
        from saymo.audio.playback import play_audio_bytes
        audio_bytes = await tts.synthesize(text)
        await play_audio_bytes(audio_bytes, config.audio.playback_device)

    console.print("[green]Done![/]")


@main.command("test-jira")
@click.pass_context
def test_jira(ctx):
    """Test JIRA connection and show recent tasks."""
    run_async(_test_jira(ctx.obj["config"]))


async def _test_jira(config):
    from saymo.jira_source.tasks import fetch_standup_data

    console.print("[blue]Fetching JIRA tasks...[/]")
    try:
        data = await fetch_standup_data(config.jira)
    except Exception as e:
        console.print(f"[bold red]Failed:[/] {e}")
        return

    if not data.tasks:
        console.print("[yellow]No tasks found.[/]")
        return

    table = Table(title=f"JIRA Tasks ({len(data.tasks)})")
    table.add_column("Key")
    table.add_column("Summary")
    table.add_column("Status")
    table.add_column("Type")

    for t in data.tasks:
        table.add_row(t.key, t.summary, t.status, t.issue_type)

    console.print(table)


@main.command("list-plugins")
def list_plugins_cmd():
    """Show available source plugins and call providers."""
    from saymo.plugins.base import discover_plugins
    from saymo.providers.factory import list_providers

    table = Table(title="Source Plugins")
    table.add_column("Name")
    table.add_column("Description")
    for name, cls in sorted(discover_plugins().items()):
        table.add_row(name, getattr(cls, "description", ""))
    console.print(table)

    table2 = Table(title="Call Providers")
    table2.add_column("Name")
    table2.add_column("URL Pattern")
    table2.add_column("Mute Key")
    from saymo.providers.factory import get_provider
    for name in list_providers():
        p = get_provider(name)
        table2.add_row(name, getattr(p, "url_pattern", ""), repr(getattr(p, "mute_key", "")))
    console.print(table2)


@main.command("test-notes")
@click.pass_context
def test_notes(ctx):
    """Show today's and yesterday's Obsidian daily notes."""
    from saymo.obsidian.daily_notes import read_standup_notes

    config = ctx.obj["config"]
    vault = config.obsidian.vault_path

    if not vault:
        console.print("[bold red]Obsidian vault_path not set in config.yaml[/]")
        return

    console.print(f"[blue]Vault: {vault}[/]")
    notes = read_standup_notes(vault, config.obsidian.subfolder, config.obsidian.date_format)

    for label, key in [("Yesterday", "yesterday"), ("Today", "today")]:
        date_key = f"{key}_date"
        console.print(f"\n[bold]{label} ({notes.get(date_key, '?')}):[/]")
        content = notes.get(key)
        if content:
            console.print(content)
        else:
            console.print("[yellow]  (no daily note found)[/]")


@main.command("test-compose")
@click.option("--source", "-s", default=None, help="Source: obsidian or jira")
@click.option("--composer", default=None, help="Composer: ollama or anthropic")
@click.pass_context
def test_compose(ctx, source, composer):
    """Compose standup text without speaking (text only)."""
    config = ctx.obj["config"]
    if source:
        config.speech.source = source
    if composer:
        config.speech.composer = composer
    run_async(_test_compose(config))


async def _test_compose(config):
    from saymo.commands.core import _compose_text, _get_standup_content

    notes = await _get_standup_content(config)
    if notes is None:
        return

    text = await _compose_text(config, notes)
    if text:
        console.print(f"\n[bold]Standup text:[/]\n\n{text}")


@main.command("test-ollama")
@click.pass_context
def test_ollama(ctx):
    """Check Ollama status and available models."""
    run_async(_test_ollama(ctx.obj["config"]))


async def _test_ollama(config):
    from saymo.speech.ollama_composer import check_ollama_health
    import httpx

    url = config.ollama.url
    console.print(f"[blue]Ollama URL: {url}[/]")

    healthy = await check_ollama_health(url)
    if not healthy:
        console.print("[bold red]Ollama is NOT running![/]")
        console.print("Start it with: ollama serve")
        return

    console.print("[bold green]Ollama is running[/]")

    # List models
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{url}/api/tags")
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            table = Table(title="Ollama Models")
            table.add_column("Name")
            table.add_column("Size")
            for m in models:
                size_gb = m.get("size", 0) / (1024**3)
                table.add_row(m["name"], f"{size_gb:.1f} GB")
            console.print(table)
            console.print(f"\n[blue]Configured model: {config.ollama.model}[/]")


# ---------------------------------------------------------------------------
# response cache (Tier-A CPU-only real-time Q&A)
# ---------------------------------------------------------------------------

@main.command("prepare-responses")
@click.option("--force", is_flag=True, help="Regenerate all cached responses (ignore existing files)")
@click.pass_context
def prepare_responses(ctx, force):
    """Pre-synthesise the Tier-A response library for real-time Q&A.

    Synthesises every entry of DEFAULT_RESPONSE_LIBRARY (plus any
    overrides under config.responses.library) through the configured
    tts.engine and writes WAV files to ~/.saymo/audio_cache/responses/.
    Runtime lookup in _auto() then plays these files instantly (no live
    synthesis), which is what makes real-time Q&A work on CPU-only
    machines.
    """
    run_async(_prepare_responses(ctx.obj["config"], force=force))


async def _prepare_responses(config, force: bool = False) -> int:
    from pathlib import Path
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from saymo.analysis.response_cache import ResponseCache, build_library
    from saymo.commands.core import _synthesize

    if not config.responses.enabled:
        console.print("[yellow]config.responses.enabled=false — skipping response cache[/]")
        return 0

    library = build_library(config.responses.library)
    cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None

    cache = ResponseCache(
        library=library,
        cache_dir=cache_dir,
        confidence_threshold=config.responses.confidence_threshold,
    )

    total_variants = sum(len(e.variants) for e in library.values())
    console.print(
        f"[bold blue]Preparing response cache[/] — {len(library)} intents, "
        f"{total_variants} variants, engine: {config.tts.engine}"
    )

    async def synth(text: str) -> bytes:
        audio = await _synthesize(config, text)
        if audio is None:
            raise RuntimeError(f"TTS returned no audio for: {text[:60]}")
        return audio

    columns = [
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
    ]
    with Progress(*columns, console=console) as progress:
        task = progress.add_task("synthesising", total=total_variants)

        def on_progress(key: str, idx: int, total: int):
            progress.update(task, completed=idx, description=f"[dim]{key}")

        written = await cache.build(synth, progress=on_progress, force=force)

    console.print(
        f"[bold green]Done[/] — wrote {len(written)} files "
        f"to {cache.cache_dir} "
        f"(skipped {total_variants - len(written)} already cached)"
    )
    return len(written)


# ---------------------------------------------------------------------------
# extra-prompts helper
# ---------------------------------------------------------------------------

def _read_prompts_file(path) -> list[str]:
    """Read user-supplied training prompts (one per line).

    Used by ``saymo train-prepare --extra <file>`` so people can mix in
    their own domain-specific sentences without forking the repo. Empty
    lines and ``#``-comments are skipped.
    """
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return []
    out: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


# ---------------------------------------------------------------------------
# mic calibration wizard
# ---------------------------------------------------------------------------

def _record_buffer(sd, sample_rate: int, seconds: float, device_index: int):
    import numpy as np

    frames = int(seconds * sample_rate)
    buf = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=device_index,
    )
    sd.wait()
    return np.asarray(buf, dtype=np.float32).flatten()


def _resolve_input_device(config, device_override: str | None):
    import sounddevice as sd
    from saymo.audio.devices import find_device

    name = device_override or config.audio.recording_device or None
    dev = find_device(name, kind="input") if name else None
    if not dev:
        default_dev = sd.query_devices(kind="input")
        if default_dev and isinstance(default_dev, dict):
            name = default_dev["name"]
            dev = find_device(name, kind="input")
    return name, dev


def _write_audio_settings_to_user_config(settings: dict):
    """Merge ``settings`` into the ``audio:`` block of ~/.saymo/config.yaml.

    Creates the file if it does not exist. Preserves every other key of
    the existing config so we never clobber the user's unrelated state.
    """
    from pathlib import Path
    import yaml

    config_path = Path.home() / ".saymo" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    audio_block = data.get("audio")
    if not isinstance(audio_block, dict):
        audio_block = {}
    for k, v in settings.items():
        audio_block[k] = v
    data["audio"] = audio_block

    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return config_path


def _run_mic_autocalibrate(config, device_name, sample_rate, max_passes):
    """Record → autocalibrate → (optionally raise hw volume) → retry loop.

    Stops as soon as the verdict is ``excellent`` or when no further
    hardware-volume bump is possible. Writes the best settings found to
    ~/.saymo/config.yaml regardless of whether we reached ``excellent`` —
    something is always better than the no-op defaults.
    """
    import sounddevice as sd
    from saymo.audio.autocalibrate import autocalibrate
    from saymo.audio import macos_audio

    mic_name, mic = _resolve_input_device(config, device_name)
    if not mic or not mic_name:
        console.print("[bold red]No input device available[/]")
        return

    console.print(
        f"[bold blue]Mic auto-calibration[/] — {mic_name} @ {sample_rate} Hz "
        f"(up to {max_passes} pass{'' if max_passes == 1 else 'es'})"
    )

    initial_sys_volume = macos_audio.get_input_volume()
    if initial_sys_volume is not None:
        console.print(
            f"  system input volume: {initial_sys_volume * 100:.0f}% "
            "(will be raised only if software gain saturates)"
        )

    best_verdict = None
    for pass_num in range(1, max_passes + 1):
        console.print(f"\n[bold]Pass {pass_num}/{max_passes}[/]")
        console.print("[dim]Stay silent for 3 s after countdown.[/]")
        for i in range(3, 0, -1):
            console.print(f"  {i}...")
            import time as _t
            _t.sleep(1)
        console.print("[bold red]Silent...[/]")
        noise = _record_buffer(sd, sample_rate, 3.0, mic.index)

        console.print(
            "[dim]Read this sentence at normal volume for 5 s:[/]"
        )
        console.print(
            '  [bold]«Я провожу калибровку микрофона, чтобы голос звучал '
            'чисто и разборчиво.»[/]'
        )
        for i in range(3, 0, -1):
            console.print(f"  {i}...")
            import time as _t
            _t.sleep(1)
        console.print("[bold red]Speak...[/]")
        voice = _record_buffer(sd, sample_rate, 5.0, mic.index)

        verdict = autocalibrate(noise, voice, sample_rate)
        console.print(
            f"  input: noise {verdict.noise_floor_db:.1f} dB, "
            f"voice rms {verdict.input_voice_rms_db:.1f} dB, "
            f"peak {verdict.input_voice_peak_db:.1f} dB"
        )
        console.print(
            f"  projected after chain: rms {verdict.projected_voice_rms_db:.1f} dB, "
            f"peak {verdict.projected_voice_peak_db:.1f} dB, "
            f"snr {verdict.projected_snr_db:.1f} dB"
        )
        console.print(f"  verdict: [bold]{verdict.quality}[/]")
        for w in verdict.warnings:
            console.print(f"  [yellow]! {w}[/]")

        if best_verdict is None or (
            not best_verdict.excellent() and verdict.quality != "poor"
        ):
            best_verdict = verdict

        if verdict.excellent():
            break
        if not verdict.actionable():
            console.print("[yellow]No further automatic adjustment will help.[/]")
            break
        if initial_sys_volume is None:
            console.print(
                "[yellow]Cannot read macOS input volume — skipping "
                "hardware bump. Raise the mic level manually and re-run.[/]"
            )
            break
        before, after = macos_audio.bump_input_volume(
            verdict.system_volume_recommendation or 0.1
        )
        if after is None or (before is not None and abs(after - before) < 0.01):
            console.print(
                "[yellow]macOS input volume already at max or unchanged.[/]"
            )
            break
        before_pct = f"{before * 100:.0f}%" if before is not None else "?"
        console.print(
            f"  raised macOS input volume {before_pct} "
            f"→ {after * 100:.0f}% — re-recording"
        )

    assert best_verdict is not None
    path = _write_audio_settings_to_user_config(best_verdict.settings)
    console.print()
    console.print(f"[bold green]Wrote settings to {path}[/]")
    console.print(best_verdict.yaml_snippet())
    if best_verdict.excellent():
        console.print(
            "[bold green]Result: excellent — ready for saymo train-prepare.[/]"
        )
    else:
        console.print(
            f"[yellow]Result: {best_verdict.quality}. "
            "Settings written anyway, but consider a quieter room / closer "
            "mic distance before re-running.[/]"
        )


@main.command("mic-check")
@click.option("--device", "-d", default=None, help="Input device name (overrides config)")
@click.option("--sample-rate", "-r", default=22050, type=int, help="Sample rate in Hz")
@click.option("--no-playback", is_flag=True, help="Skip A/B playback step")
@click.option("--auto", is_flag=True, help="Run autocalibration: record, tune, adjust macOS input volume, retry up to 3 times, write config.yaml")
@click.option("--max-passes", default=3, type=int, show_default=True, help="Max record→tune→retry passes in --auto mode")
@click.pass_context
def mic_check(ctx, device, sample_rate, no_playback, auto, max_passes):
    """Interactive microphone calibration.

    Records 3 s of silence to measure the noise floor, 5 s of voice to
    measure signal level, then prints a config.yaml snippet with suggested
    gain + noise-gate values. Optionally plays back the raw and processed
    versions so you can A/B compare before committing to the settings.

    With --auto: no questions asked. Records one silence + one voice
    buffer, runs autocalibration, and if the result is not "excellent"
    because software gain saturated, raises the macOS system input
    volume and re-records — up to --max-passes times. Writes the final
    settings into ~/.saymo/config.yaml.
    """
    if auto:
        _run_mic_autocalibrate(
            ctx.obj["config"],
            device_name=device,
            sample_rate=sample_rate,
            max_passes=max_passes,
        )
        return
    import sounddevice as sd
    from saymo.audio.devices import find_device
    from saymo.audio.mic_processor import (
        MicProcessor,
        recommend_calibration,
        rms_db,
        peak_db,
    )

    config = ctx.obj["config"]
    mic_name = device or config.audio.recording_device or None
    mic = find_device(mic_name, kind="input") if mic_name else None
    if not mic:
        default_dev = sd.query_devices(kind="input")
        if default_dev and isinstance(default_dev, dict):
            mic_name = default_dev["name"]
            console.print(f"[yellow]Using default mic: {mic_name}[/]")
            mic = find_device(mic_name, kind="input")
    if not mic or not mic_name:
        console.print("[bold red]No input device available[/]")
        return

    import numpy as np

    def _record(seconds: float) -> np.ndarray:
        frames = int(seconds * sample_rate)
        buf = sd.rec(
            frames,
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            device=mic.index,
        )
        sd.wait()
        return np.asarray(buf, dtype=np.float32).flatten()

    console.print(f"[bold blue]Mic calibration[/] — {mic_name} @ {sample_rate} Hz")
    console.print(
        "[dim]Step 1/3 — measure ambient noise floor. "
        "Stay silent for 3 seconds after the countdown.[/]"
    )
    for i in range(3, 0, -1):
        console.print(f"  {i}...")
        import time as _t
        _t.sleep(1)
    console.print("[bold red]Silent for 3 s...[/]")
    noise = _record(3.0)
    noise_rms = rms_db(noise)
    noise_peak = peak_db(noise)
    console.print(
        f"  noise floor: rms {noise_rms:.1f} dB, peak {noise_peak:.1f} dB"
    )

    console.print()
    console.print(
        "[dim]Step 2/3 — measure voice level. Read this sentence at your "
        "normal speaking volume for 5 seconds:[/]"
    )
    console.print(
        '  [bold]«Я провожу калибровку микрофона, чтобы голос звучал '
        'чисто и разборчиво.»[/]'
    )
    for i in range(3, 0, -1):
        console.print(f"  {i}...")
        import time as _t
        _t.sleep(1)
    console.print("[bold red]Speak for 5 s...[/]")
    voice = _record(5.0)
    voice_rms = rms_db(voice)
    voice_peak = peak_db(voice)
    console.print(
        f"  voice: rms {voice_rms:.1f} dB, peak {voice_peak:.1f} dB"
    )

    result = recommend_calibration(noise, voice)

    console.print()
    console.print("[bold blue]Step 3/3 — recommendation[/]")
    console.print(f"  suggested input_gain_db:  [bold]{result.suggested_gain_db:+.1f}[/]")
    console.print(f"  suggested noise_gate_db:  [bold]{result.suggested_gate_db:.1f}[/]")
    console.print(f"  signal-to-noise:          [bold]{result.voice_rms_db - result.noise_floor_db:.1f} dB[/]")
    for w in result.warnings:
        console.print(f"  [yellow]! {w}[/]")

    if not no_playback:
        console.print()
        console.print(
            "[dim]Playing back 5 s: raw → processed. "
            "Listen for cleaner tail and steadier level.[/]"
        )
        playback_dev = find_device(config.audio.monitor_device or mic_name, kind="output")
        playback_idx = playback_dev.index if playback_dev else None
        try:
            sd.play(voice, samplerate=sample_rate, device=playback_idx)
            sd.wait()
            processor = MicProcessor(
                sample_rate=sample_rate,
                gain_db=result.suggested_gain_db,
                noise_gate_db=result.suggested_gate_db,
                highpass_cutoff_hz=80.0,
            )
            processed = processor.process(voice)
            sd.play(processed, samplerate=sample_rate, device=playback_idx)
            sd.wait()
        except Exception as e:
            console.print(f"[yellow]Playback skipped: {e}[/]")

    console.print()
    console.print("[bold green]Add this to your config.yaml:[/]")
    console.print()
    console.print(result.yaml_snippet())
    console.print()
    console.print(
        "[dim]Re-run `saymo mic-check` any time the room, mic, or "
        "distance changes.[/]"
    )

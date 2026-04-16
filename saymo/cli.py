"""Saymo CLI — AI-powered standup automation."""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from saymo.config import load_config

console = Console()


def run_async(coro):
    """Run async function in sync click context."""
    return asyncio.run(coro)


def _get_cached_audio_path():
    """Path to today's pre-generated audio file."""
    from datetime import date
    from pathlib import Path
    cache_dir = Path.home() / ".saymo" / "audio_cache"
    return cache_dir / f"{date.today().isoformat()}.wav"


async def _play_cached_audio(config, audio_path, glip_mode: bool = False):
    """Play pre-generated audio file directly — no TTS needed."""
    audio_bytes = audio_path.read_bytes()

    if glip_mode:
        from saymo.glip_control import check_glip_ready, unmute_speak_mute, switch_rc_mic_to_blackhole
        from saymo.audio.devices import find_device

        bh = find_device("BlackHole 2ch", kind="output")
        if not bh:
            console.print("[bold red]BlackHole 2ch not found![/]")
            return

        status = check_glip_ready()
        if not status["glip_tab_found"]:
            console.print("[bold red]RingCentral Video tab not found![/]")
            return

        console.print("[bold blue]Switching mic to BlackHole...[/]")
        switch_rc_mic_to_blackhole()

        import asyncio as _aio
        await _aio.sleep(0.5)

        async def _do_play():
            playback = "BlackHole 2ch"
            monitor = config.audio.monitor_device
            if monitor and monitor.lower() != playback.lower():
                from saymo.audio.multi_play import play_bytes_to_devices
                await play_bytes_to_devices(audio_bytes, [playback, monitor])
            else:
                from saymo.audio.playback import play_audio_bytes
                await play_audio_bytes(audio_bytes, playback)

        console.print("[bold blue]Unmute → Play → Mute[/]")
        await unmute_speak_mute(_do_play)
    else:
        playback = config.audio.playback_device
        monitor = config.audio.monitor_device
        use_multi = (monitor and monitor.lower() != playback.lower()
                     and "blackhole" in playback.lower())
        if use_multi:
            from saymo.audio.multi_play import play_bytes_to_devices
            await play_bytes_to_devices(audio_bytes, [playback, monitor])
        else:
            from saymo.audio.playback import play_audio_bytes
            await play_audio_bytes(audio_bytes, playback)

    console.print("[bold green]Done![/]")


def _load_cached_summary(config) -> str | None:
    """Check if today's Obsidian note already has a Standup Summary section."""
    if not config.obsidian.vault_path:
        return None

    import re
    from datetime import date
    from pathlib import Path

    vault = Path(config.obsidian.vault_path)
    subfolder = config.obsidian.subfolder
    target = vault / subfolder if subfolder else vault
    note_path = target / (date.today().strftime(config.obsidian.date_format) + ".md")

    if not note_path.exists():
        return None

    content = note_path.read_text(encoding="utf-8")
    match = re.search(r'## Standup Summary\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if match:
        text = match.group(1).strip()
        if text:
            return text
    return None


@click.group()
@click.option("--config", "-c", "config_path", default=None, help="Path to config.yaml")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.pass_context
def main(ctx, config_path, verbose):
    """Saymo — AI-powered standup automation for Glip calls."""
    from saymo.utils.logger import setup_logging
    setup_logging(level=logging.DEBUG if verbose else logging.INFO)
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)


# ---------------------------------------------------------------------------
# auto — listen for name trigger and speak automatically
# ---------------------------------------------------------------------------

@main.command()
@click.option("--model", "-m", default="small", help="Whisper model: tiny, small, medium")
@click.pass_context
def auto(ctx, model):
    """Listen to Glip call, detect your name, auto-speak.

    Captures audio from BlackHole 16ch, transcribes with faster-whisper,
    triggers speak --glip when your name is detected.
    Requires: prepare (run beforehand to cache audio).
    """
    config = ctx.obj["config"]
    run_async(_auto(config, model))


async def _auto(config, whisper_model: str):
    import asyncio

    # Pre-checks
    cached_audio = _get_cached_audio_path()
    if not cached_audio.exists():
        console.print("[bold red]No cached audio! Run 'saymo prepare' first.[/]")
        return

    from saymo.audio.devices import find_device
    capture_dev = find_device(config.audio.capture_device, kind="input")
    if not capture_dev:
        console.print(f"[bold red]Capture device not found: {config.audio.capture_device}[/]")
        console.print("[dim]Need BlackHole 16ch for capturing Glip audio[/]")
        return

    from saymo.glip_control import check_glip_ready
    status = check_glip_ready()
    if not status["glip_tab_found"]:
        console.print("[bold red]Glip tab not found in Chrome![/]")
        return

    console.print("[bold green]Saymo AUTO mode[/]")
    console.print(f"  Listening on: {config.audio.capture_device}")
    console.print(f"  Whisper model: {whisper_model}")
    console.print(f"  Triggers: {', '.join(config.user.name_variants)}")
    console.print(f"  Cached audio: {cached_audio.stat().st_size // 1024} KB")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/]")
    console.print("[bold yellow]Listening...[/]\n")

    # Init components
    from saymo.audio.capture import AudioCapture
    from saymo.stt.whisper_local import LocalWhisper
    from saymo.analysis.turn_detector import TurnDetector

    capture = AudioCapture(
        device_name=config.audio.capture_device,
        sample_rate=16000,
        chunk_seconds=3.0,
    )
    whisper = LocalWhisper(model_size=whisper_model, language=config.user.language)
    detector = TurnDetector(
        name_variants=config.user.name_variants,
        cooldown_seconds=60.0,
    )

    capture.start()

    try:
        while True:
            chunk = await asyncio.to_thread(capture.get_chunk, 5.0)
            if chunk is None:
                continue

            # Skip silence (RMS too low)
            rms = float((chunk ** 2).mean() ** 0.5)
            if rms < 0.005:
                continue

            # Transcribe
            text = await asyncio.to_thread(whisper.transcribe, chunk)
            if not text.strip():
                continue

            console.print(f"[dim]{text}[/]")

            # Check trigger
            if detector.check(text):
                console.print("\n[bold red]>>> NAME DETECTED! Speaking...[/]\n")

                # Small delay — let the person finish saying your name
                await asyncio.sleep(1.5)

                # Speak via Glip
                await _play_cached_audio(config, cached_audio, glip_mode=True)

                console.print("\n[bold yellow]Listening again...[/]\n")
                detector.reset_cooldown()

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/]")
    finally:
        capture.stop()


# ---------------------------------------------------------------------------
# dashboard — interactive TUI
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def dashboard(ctx):
    """Interactive control panel with hotkeys.

    Switch devices, engines, prepare & speak — all from one screen.
    """
    from saymo.tui import run_tui
    run_tui(ctx.params.get("config_path"))


# ---------------------------------------------------------------------------
# speak — main command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--source", "-s", default=None, help="Source: obsidian, confluence, or jira")
@click.option("--composer", default=None, help="Composer: ollama or anthropic")
@click.option("--glip/--no-glip", default=False, help="Auto-control Glip mute via Chrome")
@click.pass_context
def speak(ctx, source, composer, glip):
    """Read daily notes, compose standup, and speak it.

    With --glip: auto-switches to Chrome, unmutes, speaks, mutes back.
    Checks that BlackHole 2ch is the playback device for Glip mode.
    """
    config = ctx.obj["config"]
    if source:
        config.speech.source = source
    if composer:
        config.speech.composer = composer
    run_async(_speak(config, glip_mode=glip))


async def _speak(config, glip_mode: bool = False):

    # Step 0: Check for pre-generated audio cache (instant playback)
    cached_audio = _get_cached_audio_path()
    if cached_audio.exists():
        console.print(f"[green]Using cached audio from prepare ({cached_audio.stat().st_size // 1024} KB)[/]")
        await _play_cached_audio(config, cached_audio, glip_mode)
        return

    # Step 0b: Check if today's text summary exists in Obsidian
    standup_text = _load_cached_summary(config)

    if standup_text:
        console.print("[green]Using cached text from Obsidian (generating audio...)[/]")
    else:
        # Step 1: Get standup content
        notes_text = await _get_standup_content(config)
        if notes_text is None:
            return

        # Step 2: Compose standup text with LLM
        standup_text = await _compose_text(config, notes_text)
        if standup_text is None:
            return

    console.print(f"\n[bold green]Standup text:[/]\n{standup_text}\n")

    # Step 3: Glip pre-checks
    if glip_mode:
        from saymo.glip_control import check_glip_ready, unmute_speak_mute, get_mic_setup_instructions
        from saymo.audio.devices import find_device

        # Verify BlackHole 2ch exists
        bh = find_device("BlackHole 2ch", kind="output")
        if not bh:
            console.print("[bold red]BlackHole 2ch not found![/]")
            console.print("Install: brew install blackhole-2ch")
            return

        # Force BlackHole as playback device
        if "blackhole" not in config.audio.playback_device.lower():
            console.print(f"[bold yellow]Switching playback to BlackHole 2ch (was: {config.audio.playback_device})[/]")
            config.audio.playback_device = "BlackHole 2ch"

        # Check Chrome + Glip tab
        status = check_glip_ready()
        if not status["chrome_running"]:
            console.print("[bold red]Chrome is not running![/]")
            return
        if not status["glip_tab_found"]:
            console.print("[bold red]RingCentral Video tab not found in Chrome![/]")
            console.print("[dim]Open v.ringcentral.com/conf/... in Chrome first.[/]")
            return

        console.print(f"[green]RingCentral tab found (window {status['tab_info'][0]}, tab {status['tab_info'][1]})[/]")

        # Auto-switch mic to BlackHole 2ch in RingCentral
        from saymo.glip_control import switch_rc_mic_to_blackhole
        console.print("[bold blue]Switching RingCentral mic to BlackHole 2ch...[/]")
        mic_ok = switch_rc_mic_to_blackhole()
        if mic_ok:
            console.print("[green]Mic switched to BlackHole 2ch[/]")
        else:
            console.print("[bold yellow]Could not auto-switch mic. Please set manually:[/]")
            console.print(get_mic_setup_instructions())
            console.print()

        import asyncio as _aio
        await _aio.sleep(0.5)
        console.print("[bold blue]Unmute → Speak → Mute (auto)[/]")

        # Unmute → speak → mute
        await unmute_speak_mute(_speak_text, config, standup_text)
        return

    # Step 4: Speak without Glip automation
    await _speak_text(config, standup_text)


async def _get_standup_content(config) -> dict | None:
    """Get standup content from configured source (obsidian or jira)."""
    if config.speech.source == "obsidian":
        from saymo.obsidian.daily_notes import read_standup_notes

        vault = config.obsidian.vault_path
        if not vault:
            console.print("[bold red]Obsidian vault_path not configured in config.yaml[/]")
            return None

        console.print(f"[bold blue]Reading Obsidian daily notes from {vault}...[/]")
        notes = read_standup_notes(
            vault, config.obsidian.subfolder, config.obsidian.date_format
        )

        if not notes.get("yesterday") and not notes.get("today"):
            console.print("[yellow]No daily notes found for today or yesterday.[/]")
            console.print(f"  Expected: {vault}/{notes['yesterday_date']}.md or {notes['today_date']}.md")
            return None

        if notes.get("yesterday"):
            console.print(f"[green]Yesterday ({notes['yesterday_date']}):[/] found")
        if notes.get("today"):
            console.print(f"[green]Today ({notes['today_date']}):[/] found")

        return notes

    elif config.speech.source == "confluence":
        from saymo.jira_source.confluence_tasks import fetch_daily_tasks, tasks_to_notes

        console.print("[bold blue]Fetching JIRA tasks (confluence mode)...[/]")
        try:
            daily = await fetch_daily_tasks(config.jira)
        except Exception as e:
            console.print(f"[bold red]JIRA fetch failed:[/] {e}")
            return None

        if not daily.today and not daily.yesterday:
            console.print("[yellow]No tasks found.[/]")
            return None

        if daily.yesterday:
            console.print(f"[green]Yesterday ({daily.yesterday_date}):[/] {len(daily.yesterday)} tasks")
            for t in daily.yesterday:
                console.print(f"  {t.key}: {t.summary} [{t.status}]")
        if daily.today:
            console.print(f"[green]Today ({daily.today_date}):[/] {len(daily.today)} tasks")
            for t in daily.today:
                console.print(f"  {t.key}: {t.summary} [{t.status}]")

        return tasks_to_notes(daily)

    elif config.speech.source == "jira":
        from saymo.jira_source.tasks import fetch_standup_data

        console.print("[bold blue]Fetching JIRA tasks...[/]")
        try:
            standup_data = await fetch_standup_data(config.jira)
        except Exception as e:
            console.print(f"[bold red]JIRA fetch failed:[/] {e}")
            return None

        if not standup_data.tasks:
            console.print("[yellow]No tasks found for the last day.[/]")
            return None

        console.print(f"[green]Found {len(standup_data.tasks)} tasks[/]")
        tasks_text = "\n".join(standup_data.task_summary_lines)
        return {
            "yesterday": tasks_text,
            "today": "(plan based on task statuses)",
            "yesterday_date": "вчера",
            "today_date": "сегодня",
        }
    else:
        console.print(f"[bold red]Unknown source: {config.speech.source}[/]")
        return None


async def _compose_text(config, notes: dict) -> str | None:
    """Compose standup text using configured LLM."""
    console.print(f"\n[bold blue]Composing with {config.speech.composer}...[/]")

    try:
        if config.speech.composer == "ollama":
            from saymo.speech.ollama_composer import compose_standup_ollama, check_ollama_health

            if not await check_ollama_health(config.ollama.url):
                console.print("[bold red]Ollama is not running![/]")
                console.print("Start it with: ollama serve")
                return None

            return await compose_standup_ollama(
                notes,
                model=config.ollama.model,
                ollama_url=config.ollama.url,
                language=config.speech.language,
            )

        elif config.speech.composer == "anthropic":
            from saymo.speech.composer import compose_standup
            from saymo.jira_source.tasks import StandupData, JiraTask

            # Wrap notes into StandupData for legacy composer
            tasks = [JiraTask(key="NOTE", summary=line, status="done", issue_type="note")
                     for line in (notes.get("yesterday") or "").split("\n") if line.strip()]
            data = StandupData(tasks=tasks)
            return await compose_standup(data, config)

        else:
            console.print(f"[bold red]Unknown composer: {config.speech.composer}[/]")
            return None

    except Exception as e:
        console.print(f"[bold red]Composition failed:[/] {e}")
        return None


async def _speak_text(config, text: str) -> None:
    """Synthesize and play speech. Plays to monitor device too if configured."""
    from saymo.tts.text_normalizer import normalize_for_tts

    # Normalize text: expand abbreviations, numbers, versions
    normalized = normalize_for_tts(text)
    if normalized != text:
        console.print("[dim]Normalized for TTS (abbreviations/numbers expanded)[/]")
        text = normalized

    console.print(f"[bold blue]Speaking ({config.tts.engine})...[/]")

    # Build list of output devices
    playback = config.audio.playback_device
    monitor = config.audio.monitor_device
    use_multi = (monitor and monitor.lower() != playback.lower()
                 and "blackhole" in playback.lower())

    if use_multi:
        console.print(f"[dim]Output: {playback} + {monitor} (monitor)[/]")

    try:
        # Step 1: Synthesize to bytes
        audio_bytes = await _synthesize(config, text)
        if audio_bytes is None:
            return

        # Step 2: Play to device(s)
        if use_multi:
            from saymo.audio.multi_play import play_bytes_to_devices
            await play_bytes_to_devices(audio_bytes, [playback, monitor])
        else:
            from saymo.audio.playback import play_audio_bytes
            await play_audio_bytes(audio_bytes, playback)

    except Exception as e:
        console.print(f"[bold red]TTS/playback failed:[/] {e}")
        console.print("[yellow]Falling back to macOS say...[/]")
        from saymo.tts.macos_say import MacOSSay
        say = MacOSSay(config.tts.macos_say)
        try:
            await say.synthesize_to_device(text, playback)
        except Exception as e2:
            console.print(f"[bold red]Fallback also failed:[/] {e2}")


async def _synthesize(config, text: str) -> bytes | None:
    """Synthesize text to audio bytes using configured TTS engine."""
    try:
        if config.tts.engine == "coqui_clone":
            from saymo.tts.coqui_clone import CoquiCloneTTS
            return await CoquiCloneTTS(language=config.speech.language).synthesize(text)

        elif config.tts.engine == "piper":
            from saymo.tts.piper_tts import PiperTTS
            return await PiperTTS(model_path=config.tts.piper.model_path or None).synthesize(text)

        elif config.tts.engine == "macos_say":
            from saymo.tts.macos_say import MacOSSay
            return await MacOSSay(config.tts.macos_say).synthesize(text)

        elif config.tts.engine == "openai":
            from saymo.tts.openai_tts import OpenAITTS
            return await OpenAITTS(config.tts.openai).synthesize(text)

        else:
            console.print(f"[bold red]Unknown TTS engine: {config.tts.engine}[/]")
            return None

    except Exception as e:
        console.print(f"[bold red]TTS synthesis failed:[/] {e}")
        return None

    console.print("[bold green]Done![/]")


# ---------------------------------------------------------------------------
# test commands
# ---------------------------------------------------------------------------

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
    from saymo.tts.macos_say import MacOSSay

    console.print(f"[blue]TTS engine: {config.tts.engine}[/]")
    console.print(f"[blue]Text: {text}[/]")
    console.print(f"[blue]Device: {config.audio.playback_device}[/]")

    if config.tts.engine == "openai":
        from saymo.tts.openai_tts import OpenAITTS
        from saymo.audio.playback import play_audio_bytes
        tts = OpenAITTS(config.tts.openai)
        audio_bytes = await tts.synthesize(text)
        await play_audio_bytes(audio_bytes, config.audio.playback_device)
    elif config.tts.engine == "macos_say":
        say = MacOSSay(config.tts.macos_say)
        await say.synthesize_to_device(text, config.audio.playback_device)
    else:
        console.print(f"[red]Unknown engine: {config.tts.engine}[/]")

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
# prepare — pre-daily standup preparation
# ---------------------------------------------------------------------------

@main.command()
@click.option("--save/--no-save", default=True, help="Save summary to Obsidian daily note")
@click.pass_context
def prepare(ctx, save):
    """Prepare standup summary BEFORE the daily meeting.

    Fetches JIRA tasks (confluence mode), composes summary via Ollama,
    optionally saves to today's Obsidian daily note, and prints the text.
    Run this 5 min before your standup.
    """
    config = ctx.obj["config"]
    # Force confluence source for prepare
    config.speech.source = "confluence"
    run_async(_prepare(config, save))


async def _prepare(config, save: bool):
    notes = await _get_standup_content(config)
    if notes is None:
        return

    text = await _compose_text(config, notes)
    if text is None:
        return

    console.print(f"\n[bold green]Standup summary:[/]\n\n{text}\n")

    if save and config.obsidian.vault_path:
        from datetime import date
        from pathlib import Path

        vault = Path(config.obsidian.vault_path)
        subfolder = config.obsidian.subfolder
        target = vault / subfolder if subfolder else vault
        target.mkdir(parents=True, exist_ok=True)

        note_path = target / (date.today().strftime(config.obsidian.date_format) + ".md")

        # Append standup section to daily note
        standup_section = f"\n\n## Standup Summary\n\n{text}\n"
        if note_path.exists():
            existing = note_path.read_text(encoding="utf-8")
            if "## Standup Summary" in existing:
                # Replace existing section
                import re
                existing = re.sub(
                    r'## Standup Summary\n.*?(?=\n## |\Z)',
                    f"## Standup Summary\n\n{text}\n",
                    existing,
                    flags=re.DOTALL,
                )
                note_path.write_text(existing, encoding="utf-8")
            else:
                with open(note_path, "a", encoding="utf-8") as f:
                    f.write(standup_section)
        else:
            header = f"# {date.today().isoformat()}\n"
            note_path.write_text(header + standup_section, encoding="utf-8")

        console.print(f"[blue]Saved text to: {note_path}[/]")

    # Pre-generate audio file
    console.print("\n[bold blue]Pre-generating audio...[/]")
    from saymo.tts.text_normalizer import normalize_for_tts
    normalized = normalize_for_tts(text)
    audio_bytes = await _synthesize(config, normalized)
    if audio_bytes:
        audio_path = _get_cached_audio_path()
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio_bytes)
        console.print(f"[green]Audio cached: {audio_path} ({len(audio_bytes) // 1024} KB)[/]")
    else:
        console.print("[yellow]Audio pre-generation failed, will generate on speak[/]")

    console.print("\n[dim]Run 'saymo speak' — instant playback from cache![/]")


# ---------------------------------------------------------------------------
# review — listen and fix audio quality
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def review(ctx):
    """Review cached audio sentence-by-sentence.

    Plays each sentence, asks if quality is OK.
    Bad sentences get regenerated with adjusted parameters.
    """
    run_async(_review(ctx.obj["config"]))


async def _review(config):
    import io
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
    from saymo.tts.text_normalizer import normalize_for_tts
    from saymo.tts.coqui_clone import CoquiCloneTTS

    # Load text
    text = _load_cached_summary(config)
    if not text:
        console.print("[yellow]No summary found. Run 'saymo prepare' first.[/]")
        return

    normalized = normalize_for_tts(text)

    # Split into sentences
    import re
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', normalized) if s.strip()]

    console.print(f"[bold blue]Review mode — {len(sentences)} sentences[/]")
    console.print("[dim]For each sentence: [y]=ok  [r]=regenerate  [s]=skip  [q]=quit[/]\n")

    clone = CoquiCloneTTS(language=config.speech.language)
    device_name = config.audio.playback_device
    from saymo.audio.devices import find_device
    dev = find_device(device_name, kind="output")
    device_idx = dev.index if dev else None

    # Generate per-sentence
    console.print("[bold blue]Generating sentences...[/]")
    sentence_audio = await clone.synthesize_sentences(sentences)

    # Review loop
    final_chunks = []
    for i, (sent, audio_bytes) in enumerate(zip(sentences, sentence_audio)):
        console.print(f"\n[bold cyan]Sentence {i+1}/{len(sentences)}:[/]")
        console.print(f"  {sent[:100]}{'...' if len(sent) > 100 else ''}")

        while True:
            # Play
            data, sr = sf.read(io.BytesIO(audio_bytes))
            await asyncio.to_thread(sd.play, data, samplerate=sr, device=device_idx)
            await asyncio.to_thread(sd.wait)

            console.print("  [y]=ok  [r]=regenerate  [p]=replay  [q]=quit")
            key = await asyncio.to_thread(_review_read_key)

            if key == "y":
                final_chunks.append((data, sr))
                console.print("  [green]Accepted[/]")
                break
            elif key == "r":
                console.print("  [yellow]Regenerating...[/]")
                new_audio = await clone.synthesize_sentences([sent])
                if new_audio:
                    audio_bytes = new_audio[0]
                    console.print("  [blue]Regenerated — playing...[/]")
                # Loop back to play
            elif key == "p":
                pass  # replay
            elif key in ("q", "s"):
                if key == "s":
                    final_chunks.append((data, sr))
                    console.print("  [dim]Skipped (kept)[/]")
                break
            elif key == "\x03":
                return

        if key == "q":
            break

    if not final_chunks:
        console.print("[yellow]No audio to save[/]")
        return

    # Concatenate all accepted chunks
    sample_rate = final_chunks[0][1]
    all_audio = np.concatenate([chunk for chunk, _ in final_chunks])

    # Save
    audio_path = _get_cached_audio_path()
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(audio_path), all_audio, sample_rate)

    console.print(f"\n[bold green]Saved reviewed audio: {audio_path} ({audio_path.stat().st_size // 1024} KB)[/]")
    console.print(f"[dim]Accepted {len(final_chunks)}/{len(sentences)} sentences[/]")


def _review_read_key() -> str:
    """Read a single keypress for review mode."""
    import sys
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


# ---------------------------------------------------------------------------
# voice clone commands
# ---------------------------------------------------------------------------

@main.command("record-voice")
@click.option("--duration", "-d", default=30, help="Recording duration in seconds")
@click.option("--output", "-o", default=None, help="Output WAV file path")
@click.pass_context
def record_voice(ctx, duration, output):
    """Record a voice sample for voice cloning.

    Uses the Plantronics mic (or configured capture device).
    Recommended: 30-60 seconds of natural speech in Russian.
    """
    from saymo.audio.recorder import record_sample, VOICE_SAMPLES_DIR
    from saymo.audio.devices import find_device

    config = ctx.obj["config"]

    # Use the input device (mic) — find Plantronics or first available input
    mic_name = "Plantronics"
    mic = find_device(mic_name, kind="input")
    if not mic:
        console.print(f"[yellow]'{mic_name}' not found, using default mic[/]")
        mic_name = "MacBook Pro Microphone"

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
        path = record_sample(
            device_name=mic_name,
            duration=duration,
            sample_rate=22050,
            output_path=output,
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


if __name__ == "__main__":
    main()

"""Saymo CLI — AI-powered standup automation."""

import asyncio
import logging
import os

# Ensure localhost requests bypass corporate proxy (tinyproxy etc.)
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
if "NO_PROXY" in os.environ and "localhost" not in os.environ["NO_PROXY"]:
    os.environ["NO_PROXY"] += ",localhost,127.0.0.1"

import click
from rich.console import Console
from rich.table import Table

from saymo.config import load_config

console = Console()


def run_async(coro):
    """Run async function in sync click context."""
    return asyncio.run(coro)


def _get_cached_audio_path(team: bool = False):
    """Path to today's pre-generated audio file."""
    from datetime import date
    from pathlib import Path
    cache_dir = Path.home() / ".saymo" / "audio_cache"
    suffix = "-team" if team else ""
    return cache_dir / f"{date.today().isoformat()}{suffix}.wav"


def _rotate_audio_cache(max_days: int = 7):
    """Delete audio cache files older than max_days."""
    from datetime import date, timedelta
    from pathlib import Path

    cache_dir = Path.home() / ".saymo" / "audio_cache"
    if not cache_dir.exists():
        return

    cutoff = date.today() - timedelta(days=max_days)
    removed = 0
    for f in cache_dir.glob("*.wav"):
        # Parse date from filename: 2026-04-16.wav or 2026-04-16-team.wav
        try:
            date_str = f.stem.split("-team")[0]  # strip -team suffix
            file_date = date.fromisoformat(date_str)
            if file_date < cutoff:
                f.unlink()
                removed += 1
        except ValueError:
            continue

    if removed:
        logging.getLogger("saymo").info(f"Rotated {removed} old audio cache files")


async def _play_cached_audio(config, audio_path, provider_name: str | None = None):
    """Play pre-generated audio file directly — no TTS needed.

    If provider_name is given, uses that provider to unmute/mute via Chrome.
    """
    audio_bytes = audio_path.read_bytes()

    if provider_name:
        from saymo.providers.factory import get_provider
        from saymo.audio.devices import find_device

        provider = get_provider(provider_name)

        bh = find_device("BlackHole 2ch", kind="output")
        if not bh:
            console.print("[bold red]BlackHole 2ch not found![/]")
            return

        status = provider.check_ready()
        if not status.meeting_found:
            console.print(f"[bold red]{provider.name} tab not found in Chrome![/]")
            return

        # Try mic auto-switch (works for Glip, no-op for others)
        provider.switch_mic("BlackHole 2ch")

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

        console.print(f"[bold blue]{provider.name}: Unmute → Play → Mute[/]")
        await provider.unmute_speak_mute(_do_play)
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
# setup — interactive wizard
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def setup(ctx):
    """Interactive setup wizard — configure name, meetings, devices, TTS."""
    from saymo.wizard import run_wizard
    run_wizard()


# ---------------------------------------------------------------------------
# auto — listen for name trigger and speak automatically
# ---------------------------------------------------------------------------

@main.command()
@click.option("--profile", "-p", default="standup", help="Meeting profile: standup, scrum, retro")
@click.option("--model", "-m", default="small", help="Whisper model: tiny, small, medium")
@click.option("--mic", is_flag=True, help="Listen from microphone (for testing)")
@click.pass_context
def auto(ctx, profile, model, mic):
    """Listen to Glip call, detect your name, auto-speak.

    Use -p to select meeting profile and trigger words.
    Use --mic to listen from your microphone (for testing).
    Requires: prepare (run beforehand to cache audio).
    """
    config = ctx.obj["config"]
    meeting = config.get_meeting(profile)
    if meeting:
        console.print(f"[bold blue]Meeting: {profile} — {meeting.description}[/]")
    if mic:
        config.audio.capture_device = config.audio.recording_device
    run_async(_auto(config, model, profile))


async def _auto(config, whisper_model: str, profile: str = "standup"):
    import asyncio

    # Get meeting profile for trigger phrases
    meeting = config.get_meeting(profile)
    is_team = meeting.team if meeting else False

    # Pre-checks
    cached_audio = _get_cached_audio_path(team=is_team)
    if not cached_audio.exists():
        label = f"'saymo prepare --profile {profile}'" if meeting else "'saymo prepare'"
        console.print(f"[bold red]No cached audio! Run {label} first.[/]")
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

    # Determine trigger phrases from meeting profile or user config
    trigger_phrases = config.user.name_variants
    if meeting and meeting.trigger_phrases:
        trigger_phrases = meeting.trigger_phrases

    console.print(f"[bold green]Saymo AUTO mode — {profile}[/]")
    console.print(f"  Listening on: {config.audio.capture_device}")
    console.print(f"  Whisper model: {whisper_model}")
    console.print(f"  Triggers: {', '.join(trigger_phrases)}")
    console.print(f"  Cached audio: {cached_audio.stat().st_size // 1024} KB")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/]")
    console.print("[bold yellow]Listening...[/]\n")

    from saymo.audio.capture import AudioCapture
    from saymo.stt.whisper_local import LocalWhisper
    from saymo.analysis.turn_detector import TurnDetector

    capture = AudioCapture(
        device_name=config.audio.capture_device,
        sample_rate=16000,
        chunk_seconds=4.0,
        overlap_seconds=2.0,
    )
    whisper = LocalWhisper(model_size=whisper_model, language=config.user.language)
    detector = TurnDetector(
        name_variants=trigger_phrases,
        cooldown_seconds=45.0,
    )

    triggered = asyncio.Event()
    speaking = asyncio.Event()

    async def _transcribe_loop():
        """Continuously transcribe audio — runs parallel to capture."""
        while True:
            if speaking.is_set():
                # Don't transcribe while we're speaking (would hear ourselves)
                await asyncio.sleep(0.5)
                continue

            chunk = await asyncio.to_thread(capture.get_chunk, 3.0)
            if chunk is None:
                continue

            rms = float((chunk ** 2).mean() ** 0.5)
            if rms < 0.001:
                continue

            text = await asyncio.to_thread(whisper.transcribe, chunk)
            if not text.strip():
                continue

            console.print(f"[dim]{text}[/]")

            if detector.check(text):
                console.print("\n[bold red]>>> NAME DETECTED![/]\n")
                triggered.set()

    async def _trigger_loop():
        """Wait for trigger, then speak."""
        while True:
            await triggered.wait()
            triggered.clear()

            # Drain audio queue — don't process stale chunks after trigger
            while not capture.audio_queue.empty():
                try:
                    capture.audio_queue.get_nowait()
                except Exception:
                    break

            console.print("[bold blue]Speaking in 2 seconds...[/]")
            await asyncio.sleep(2.0)

            speaking.set()
            try:
                await _play_cached_audio(config, cached_audio, provider_name="glip")
            finally:
                speaking.clear()
                detector.reset_cooldown()

            console.print("\n[bold yellow]Listening again...[/]\n")

    capture.start()

    try:
        await asyncio.gather(
            _transcribe_loop(),
            _trigger_loop(),
        )

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
@click.option("--profile", "-p", default=None, help="Meeting profile: standup, scrum, retro")
@click.option("--source", "-s", default=None, help="Source: obsidian, confluence, or jira")
@click.option("--composer", default=None, help="Composer: ollama or anthropic")
@click.option("--provider", default=None, help="Call provider: glip, mts-link, zoom, teams, etc.")
@click.option("--glip", is_flag=True, help="Shortcut for --provider glip")
@click.option("--team", is_flag=True, help="Use team scrum audio cache")
@click.pass_context
def speak(ctx, profile, source, composer, provider, glip, team):
    """Read daily notes, compose standup, and speak it.

    Use -p to select meeting profile (standup, scrum, retro).
    Use --provider to auto-control mute via Chrome (e.g. --provider mts-link).
    """
    config = ctx.obj["config"]
    if profile:
        meeting = config.get_meeting(profile)
        if not meeting:
            console.print(f"[bold red]Unknown profile: {profile}[/]")
            console.print(f"[dim]Available: {', '.join(config.list_meetings())}[/]")
            return
        team = meeting.team
        if not provider:
            provider = meeting.provider
        if not source:
            config.speech.source = meeting.source
    if glip:
        provider = "glip"
    if source:
        config.speech.source = source
    if composer:
        config.speech.composer = composer
    run_async(_speak(config, provider_name=provider, team_mode=team))


async def _speak(config, provider_name: str | None = None, team_mode: bool = False):

    # Step 0: Check for pre-generated audio cache (instant playback)
    cached_audio = _get_cached_audio_path(team=team_mode)
    if cached_audio.exists():
        console.print(f"[green]Using cached audio from prepare ({cached_audio.stat().st_size // 1024} KB)[/]")
        await _play_cached_audio(config, cached_audio, provider_name)
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

    # Step 3: Provider pre-checks (unmute → speak → mute via Chrome)
    if provider_name:
        from saymo.providers.factory import get_provider
        from saymo.audio.devices import find_device

        provider = get_provider(provider_name)

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

        # Check Chrome tab
        status = provider.check_ready()
        if not status.meeting_found:
            console.print(f"[bold red]{provider.name} tab not found in Chrome![/]")
            console.print(f"[dim]Open {provider.name} call ({provider.url_pattern}) in Chrome first.[/]")
            return

        console.print(f"[green]{provider.name} tab found (window {status.tab_info[0]}, tab {status.tab_info[1]})[/]")

        # Auto-switch mic (provider-specific, no-op if not supported)
        mic_ok = provider.switch_mic("BlackHole 2ch")
        if mic_ok:
            console.print("[green]Mic switched to BlackHole 2ch[/]")

        import asyncio as _aio
        await _aio.sleep(0.5)
        console.print(f"[bold blue]{provider.name}: Unmute → Speak → Mute[/]")

        await provider.unmute_speak_mute(_speak_text, config, standup_text)
        return

    # Step 4: Speak without call automation
    await _speak_text(config, standup_text)


async def _get_standup_content(config) -> dict | None:
    """Get standup content via plugin system."""
    from saymo.plugins.base import get_plugin, list_plugins

    source = config.speech.source
    console.print(f"[bold blue]Source: {source}[/]")

    try:
        plugin = get_plugin(source)
    except ValueError:
        console.print(f"[bold red]Unknown source plugin: {source}[/]")
        console.print(f"[dim]Available: {', '.join(list_plugins())}[/]")
        return None

    console.print(f"[dim]{plugin.description}[/]")

    try:
        notes = await plugin.fetch(config)
    except Exception as e:
        console.print(f"[bold red]Source '{source}' failed:[/] {e}")
        return None

    if not notes:
        console.print(f"[yellow]No content from '{source}'[/]")
        return None

    if notes.get("yesterday"):
        console.print(f"[green]Yesterday: found[/]")
    if notes.get("today"):
        console.print(f"[green]Today: found[/]")

    return notes


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
    from saymo.tts.factory import get_tts_engine, UnsupportedTTSEngine
    try:
        return await get_tts_engine(config).synthesize(text)
    except UnsupportedTTSEngine as e:
        console.print(f"[bold red]{e}[/]")
        return None
    except Exception as e:
        console.print(f"[bold red]TTS synthesis failed:[/] {e}")
        return None


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
# quick — brief notes → full standup text via Ollama
# ---------------------------------------------------------------------------

@main.command()
@click.argument("notes", nargs=-1)
@click.option("--duration", "-d", default=30, help="Target speech duration in seconds")
@click.option("--file", "-f", "file_path", default=None, type=click.Path(exists=True), help="Read notes from file")
@click.pass_context
def quick(ctx, notes, duration, file_path):
    """Type brief notes, Ollama expands them into a full standup.

    Examples:
        saymo quick "фиксил баги в авторизации, ревью автотестов, сегодня деплой"
        saymo quick -d 60 "вчера разбирался с кафкой, сегодня нагрузочное"
        saymo quick -f notes.txt
        saymo quick -f ~/daily.md -d 45
    """
    config = ctx.obj["config"]

    if file_path:
        from pathlib import Path
        brief = Path(file_path).read_text(encoding="utf-8").strip()
        if not brief:
            console.print(f"[bold red]Файл пустой: {file_path}[/]")
            return
        console.print(f"[dim]Прочитано из {file_path} ({len(brief)} символов)[/]")
    else:
        brief = " ".join(notes).strip()
        if not brief:
            brief = click.prompt("Кратко опиши чем занимался")

    run_async(_quick_expand(config, brief, duration))


async def _quick_expand(config, brief: str, duration: int):
    from saymo.speech.ollama_composer import expand_brief, check_ollama_health

    if not await check_ollama_health(config.ollama.url):
        console.print("[yellow]Ollama не запущена, запускаю...[/]")
        import subprocess, time
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(15):
            time.sleep(1)
            if await check_ollama_health(config.ollama.url):
                break
        else:
            console.print("[bold red]Не удалось запустить Ollama![/]")
            return
        console.print("[green]Ollama запущена[/]")

    console.print(f"[bold blue]Расширяю заметки через Ollama (~{duration}с речи)...[/]\n")

    text = await expand_brief(
        brief=brief,
        duration=duration,
        model=config.ollama.model,
        ollama_url=config.ollama.url,
    )

    console.print(f"[bold green]Готовый текст:[/]\n\n{text}\n")

    # Offer TTS
    if click.confirm("Озвучить?", default=True):
        await _speak_text(config, text)


# ---------------------------------------------------------------------------
# prepare — pre-daily standup preparation
# ---------------------------------------------------------------------------

@main.command()
@click.option("--profile", "-p", default=None, help="Meeting profile: standup, scrum, retro")
@click.option("--save/--no-save", default=True, help="Save summary to Obsidian daily note")
@click.option("--team", is_flag=True, help="Team scrum mode (report on all team members)")
@click.option("--skip-responses", is_flag=True, help="Skip Tier-A response-cache rebuild")
@click.pass_context
def prepare(ctx, profile, save, team, skip_responses):
    """Prepare standup summary BEFORE the daily meeting.

    Use -p to select meeting profile: standup (default), scrum, retro.
    Also rebuilds the Tier-A response cache (pre-synthesised answers
    for common stand-up follow-ups). Pass --skip-responses to disable.
    """
    config = ctx.obj["config"]
    config.speech.source = "confluence"
    if profile:
        meeting = config.get_meeting(profile)
        if not meeting:
            console.print(f"[bold red]Unknown profile: {profile}[/]")
            console.print(f"[dim]Available: {', '.join(config.list_meetings())}[/]")
            return
        team = meeting.team
        config.speech.source = meeting.source
        console.print(f"[bold blue]Meeting: {profile} — {meeting.description}[/]")
    if team:
        run_async(_prepare_team(config, save))
    else:
        run_async(_prepare(config, save))
    if not skip_responses and config.responses.enabled:
        console.print("")
        run_async(_prepare_responses(config, force=False))


async def _prepare(config, save: bool):
    _rotate_audio_cache()
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


async def _prepare_team(config, save: bool):
    """Prepare team scrum report (your team)."""
    _rotate_audio_cache()
    from saymo.jira_source.confluence_tasks import fetch_team_tasks, team_tasks_to_notes
    from saymo.speech.ollama_composer import compose_standup_ollama, check_ollama_health, DEFAULT_TEAM_SCRUM_PROMPT_RU

    console.print("[bold blue]Fetching team tasks (your team)...[/]")
    try:
        team_members = config.jira.team_members or None
        team = await fetch_team_tasks(config.jira, team_members)
    except Exception as e:
        console.print(f"[bold red]JIRA fetch failed:[/] {e}")
        return

    for name, tasks in team.members.items():
        console.print(f"[green]{name}:[/] {len(tasks.today)} today, {len(tasks.yesterday)} yesterday")
        for t in tasks.today:
            console.print(f"  {t.key}: {t.summary} [{t.status}]")

    notes = team_tasks_to_notes(team)

    if not notes.get("yesterday") and not notes.get("today"):
        console.print("[yellow]No team tasks found.[/]")
        return

    # Compose with team prompt
    console.print("\n[bold blue]Composing team scrum report...[/]")
    if not await check_ollama_health(config.ollama.url):
        console.print("[bold red]Ollama not running! Start with: ollama serve[/]")
        return

    text = await compose_standup_ollama(
        notes,
        model=config.ollama.model,
        ollama_url=config.ollama.url,
        language=config.speech.language,
        prompt_override=DEFAULT_TEAM_SCRUM_PROMPT_RU,
    )

    console.print(f"\n[bold green]Team scrum report:[/]\n\n{text}\n")

    # Save to Obsidian
    if save and config.obsidian.vault_path:
        from datetime import date
        from pathlib import Path

        vault = Path(config.obsidian.vault_path)
        subfolder = config.obsidian.subfolder
        target = vault / subfolder if subfolder else vault
        target.mkdir(parents=True, exist_ok=True)
        note_path = target / (date.today().strftime(config.obsidian.date_format) + ".md")

        section = f"\n\n## Team Scrum Report\n\n{text}\n"
        if note_path.exists():
            import re
            existing = note_path.read_text(encoding="utf-8")
            if "## Team Scrum Report" in existing:
                existing = re.sub(
                    r'## Team Scrum Report\n.*?(?=\n## |\Z)',
                    f"## Team Scrum Report\n\n{text}\n",
                    existing, flags=re.DOTALL,
                )
                note_path.write_text(existing, encoding="utf-8")
            else:
                with open(note_path, "a", encoding="utf-8") as f:
                    f.write(section)
        else:
            note_path.write_text(f"# {date.today().isoformat()}\n{section}", encoding="utf-8")
        console.print(f"[blue]Saved to: {note_path}[/]")

    # Pre-generate audio
    console.print("\n[bold blue]Pre-generating team audio...[/]")
    from saymo.tts.text_normalizer import normalize_for_tts
    normalized = normalize_for_tts(text)
    audio_bytes = await _synthesize(config, normalized)
    if audio_bytes:
        audio_path = _get_cached_audio_path(team=True)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio_bytes)
        console.print(f"[green]Audio cached: {audio_path} ({len(audio_bytes) // 1024} KB)[/]")

    console.print("\n[dim]Run 'saymo speak --team' for instant playback![/]")


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


if __name__ == "__main__":
    main()

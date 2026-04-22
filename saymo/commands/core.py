"""Core user-flow commands: auto, speak, quick, prepare, review, dashboard."""

import click

from saymo.commands import (
    _get_cached_audio_path,
    _load_cached_summary,
    _play_cached_audio,
    _resolve_auto_response,
    _rotate_audio_cache,
    console,
    main,
    run_async,
)


# ---------------------------------------------------------------------------
# auto — listen for name trigger and speak automatically
# ---------------------------------------------------------------------------

@main.command()
@click.option("--profile", "-p", default="standup", help="Meeting profile: standup, scrum, retro")
@click.option("--model", "-m", default="small", help="Whisper model: tiny, small, medium")
@click.option("--mic", is_flag=True, help="Listen from microphone (for testing)")
@click.pass_context
def auto(ctx, profile, model, mic):
    """Listen to a live call, detect your name, auto-speak.

    Use -p to select meeting profile (which also picks the call provider).
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

    from saymo.providers.factory import get_provider
    provider_name = meeting.provider if meeting else "glip"
    provider = get_provider(provider_name)
    status = provider.check_ready()
    if not status.meeting_found:
        console.print(f"[bold red]{provider.name} tab not found in Chrome![/]")
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
        fuzzy_expansions=(config.vocabulary or {}).get("fuzzy_expansions"),
    )

    # Initialize response cache (Q&A) if enabled and a library is populated
    response_cache = None
    if config.responses.enabled:
        from saymo.analysis.response_cache import ResponseCache, build_library
        from pathlib import Path
        cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None
        response_cache = ResponseCache(
            library=build_library(config.responses.library),
            cache_dir=cache_dir,
            confidence_threshold=config.responses.confidence_threshold,
        )
        console.print(
            f"[dim]Q&A cache: {len(response_cache.library)} intents"
            f"{' + live fallback' if config.responses.live_fallback else ''}[/]"
        )

    standup_summary = _load_cached_summary(config)

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

            # Snapshot transcript window BEFORE draining — contains the question
            transcript_window = detector.recent_transcript

            # Drain audio queue — don't process stale chunks after trigger
            while not capture.audio_queue.empty():
                try:
                    capture.audio_queue.get_nowait()
                except Exception:
                    break

            audio_to_play = await _resolve_auto_response(
                config,
                transcript_window,
                response_cache,
                standup_summary,
                cached_audio,
            )

            console.print("[bold blue]Speaking in 2 seconds...[/]")
            await asyncio.sleep(2.0)

            speaking.set()
            try:
                await _play_cached_audio(config, audio_to_play, provider_name=provider_name)
            finally:
                speaking.clear()
                detector.reset_cooldown()
                # Clean up live-fallback temp files
                if audio_to_play != cached_audio:
                    try:
                        audio_to_play.unlink(missing_ok=True)
                    except Exception:
                        pass

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
        from saymo.commands.tests import _prepare_responses
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
    import asyncio
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

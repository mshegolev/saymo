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


_QUESTION_STARTERS = (
    "как ", "что ", "где ", "когда ", "почему ", "зачем ", "кто ",
    "сколько ", "какие ", "какой ", "какая ", "расскажи", "поделись", "опиши",
    "what ", "how ", "why ", "when ", "where ", "who ",
    "tell me", "can you", "could you", "do you",
)


def _looks_like_question(text: str) -> bool:
    """Heuristic: does this transcript chunk look like a question?"""
    t = text.strip()
    if not t:
        return False
    if "?" in t:
        return True
    lower = t.lower()
    return any(s in lower for s in _QUESTION_STARTERS)


async def _resolve_auto_response(
    config,
    transcript: str,
    response_cache,
    standup_summary: str | None,
    fallback_standup_path,
):
    """Pick which audio file to play when auto-mode triggers.

    Priority:
    1. Response cache hit (for recognizable questions)
    2. Live Ollama + TTS fallback (when ``responses.live_fallback`` is on)
    3. Generic standup audio (existing behaviour)

    Returns a ``Path`` suitable for ``_play_cached_audio``.
    """
    from pathlib import Path

    if response_cache and _looks_like_question(transcript):
        cached = response_cache.lookup(transcript)
        if cached:
            console.print(
                f"[green]Cache hit:[/] {cached.key} "
                f"(conf={cached.confidence:.2f}) — {cached.text}"
            )
            return Path(cached.audio_path)

        if config.responses.live_fallback:
            console.print("[yellow]Cache miss — generating live answer via Ollama...[/]")
            try:
                from saymo.speech.ollama_composer import answer_question
                from saymo.tts.factory import get_tts_engine
                import tempfile

                answer = await answer_question(
                    question=transcript,
                    standup_summary=standup_summary or "",
                    user_name=config.user.name,
                    user_role=config.user.role,
                    model=config.ollama.model,
                    ollama_url=config.ollama.url,
                    config=config,
                )
                if answer:
                    console.print(f"[green]Live answer:[/] {answer}")
                    audio = await get_tts_engine(config).synthesize(answer)
                    fd, tmp_name = tempfile.mkstemp(suffix=".wav", prefix="saymo_live_")
                    os.close(fd)
                    tmp_path = Path(tmp_name)
                    tmp_path.write_bytes(audio)
                    return tmp_path
            except Exception as e:
                console.print(f"[red]Live answer failed, falling back:[/] {e}")

    return fallback_standup_path


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
    """Saymo — AI-powered standup automation for Chrome-based calls."""
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


# Register command submodules (their @main.command() decorators fire on import).
from saymo.commands import core, tests, voice_train  # noqa: E402, F401

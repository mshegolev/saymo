"""Saymo CLI — AI-powered standup automation."""

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path

# Ensure localhost requests bypass corporate proxy (tinyproxy etc.)
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
if "NO_PROXY" in os.environ and "localhost" not in os.environ["NO_PROXY"]:
    os.environ["NO_PROXY"] += ",localhost,127.0.0.1"

import click
from rich.console import Console

from saymo.config import load_config

console = Console()


@dataclass(frozen=True)
class AutoResponseDecision:
    """Resolved audio plus routing metadata for auto-mode."""

    audio_path: Path
    source: str
    reason: str


@dataclass(frozen=True)
class PlaybackResult:
    """Outcome from a playback attempt."""

    success: bool
    reason: str = ""
    playback_started: bool = False


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


async def _play_cached_audio(
    config,
    audio_path,
    provider_name: str | None = None,
    on_playback_start=None,
):
    """Play pre-generated audio file directly — no TTS needed.

    If provider_name is given, uses that provider to unmute/mute via Chrome.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        reason = f"audio file not found: {audio_path}"
        console.print(f"[bold red]{reason}[/]")
        return PlaybackResult(False, reason=reason)

    audio_bytes = audio_path.read_bytes()
    playback_started = False

    def _mark_playback_started():
        nonlocal playback_started
        if playback_started:
            return
        playback_started = True
        if on_playback_start is not None:
            on_playback_start()

    if provider_name:
        from saymo.providers.factory import get_provider
        from saymo.audio.devices import find_device

        provider = get_provider(provider_name)

        bh = find_device("BlackHole 2ch", kind="output")
        if not bh:
            reason = "BlackHole 2ch output not found"
            console.print(f"[bold red]{reason}![/]")
            return PlaybackResult(False, reason=reason)

        status = provider.check_ready()
        if not status.meeting_found:
            reason = f"{provider.name} tab not found in Chrome"
            console.print(f"[bold red]{reason}![/]")
            return PlaybackResult(False, reason=reason)

        # Try mic auto-switch (works for Glip, no-op for others)
        provider.switch_mic("BlackHole 2ch")

        import asyncio as _aio
        await _aio.sleep(0.5)

        played = False

        async def _do_play():
            nonlocal played
            _mark_playback_started()
            playback = "BlackHole 2ch"
            monitor = config.audio.monitor_device
            if monitor and monitor.lower() != playback.lower():
                from saymo.audio.multi_play import play_bytes_to_devices
                await play_bytes_to_devices(audio_bytes, [playback, monitor])
            else:
                from saymo.audio.playback import play_audio_bytes
                await play_audio_bytes(audio_bytes, playback)
            played = True

        console.print(f"[bold blue]{provider.name}: Unmute → Play → Mute[/]")
        try:
            await provider.unmute_speak_mute(_do_play)
        except Exception as e:
            logging.getLogger("saymo").warning(
                "provider mute flow failed for %s: %s", provider.name, e
            )
            if played:
                console.print(
                    f"[yellow]{provider.name} mute automation failed after playback. "
                    "Check the call mute state manually.[/]"
                )
            else:
                console.print(
                    f"[yellow]{provider.name} mute automation failed; playing to "
                    "BlackHole 2ch without automatic mute control.[/]"
                )
                await _do_play()
    else:
        playback = config.audio.playback_device
        monitor = config.audio.monitor_device
        use_multi = (monitor and monitor.lower() != playback.lower()
                     and "blackhole" in playback.lower())
        if use_multi:
            from saymo.audio.multi_play import play_bytes_to_devices
            _mark_playback_started()
            await play_bytes_to_devices(audio_bytes, [playback, monitor])
        else:
            from saymo.audio.playback import play_audio_bytes
            _mark_playback_started()
            await play_audio_bytes(audio_bytes, playback)

    console.print("[bold green]Done![/]")
    return PlaybackResult(True, playback_started=playback_started)


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
    decision = await _resolve_auto_response_decision(
        config,
        transcript,
        response_cache,
        standup_summary,
        fallback_standup_path,
    )
    return decision.audio_path


async def _resolve_auto_response_decision(
    config,
    transcript: str,
    response_cache,
    standup_summary: str | None,
    fallback_standup_path,
) -> AutoResponseDecision:
    """Resolve auto-mode response with a machine-readable reason."""
    from pathlib import Path

    fallback = Path(fallback_standup_path)

    if response_cache and _looks_like_question(transcript):
        # Optional LLM-based intent classifier — catches rephrasings the
        # keyword matcher would miss. Runs first; on miss/timeout we fall
        # back to the fast keyword path.
        if config.responses.intent_classifier:
            try:
                from saymo.speech.ollama_composer import classify_intent
                intent_key = await classify_intent(
                    transcript,
                    available_keys=response_cache.library_keys(),
                    model=config.ollama.model,
                    ollama_url=config.ollama.url,
                    config=config,
                )
                if intent_key:
                    cached = response_cache.get_variant_by_key(intent_key)
                    if cached:
                        console.print(
                            f"[green]Classifier hit:[/] {cached.key} — {cached.text}"
                        )
                        return AutoResponseDecision(
                            Path(cached.audio_path),
                            source="classifier_cache",
                            reason=f"intent={cached.key}",
                        )
            except Exception as e:
                console.print(f"[dim]classifier skipped: {e}[/]")

        cached = response_cache.lookup(transcript)
        if cached:
            console.print(
                f"[green]Cache hit:[/] {cached.key} "
                f"(conf={cached.confidence:.2f}) — {cached.text}"
            )
            return AutoResponseDecision(
                Path(cached.audio_path),
                source="response_cache",
                reason=f"intent={cached.key} confidence={cached.confidence:.2f}",
            )

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
                    audio = await get_tts_engine(config, realtime=True).synthesize(answer)
                    fd, tmp_name = tempfile.mkstemp(suffix=".wav", prefix="saymo_live_")
                    os.close(fd)
                    tmp_path = Path(tmp_name)
                    tmp_path.write_bytes(audio)
                    return AutoResponseDecision(
                        tmp_path,
                        source="live_fallback",
                        reason="cache miss; generated live answer",
                    )
            except Exception as e:
                console.print(f"[red]Live answer failed, falling back:[/] {e}")
                return AutoResponseDecision(
                    fallback,
                    source="standup_fallback",
                    reason=f"live answer failed: {e}",
                )

        return AutoResponseDecision(
            fallback,
            source="standup_fallback",
            reason="question cache miss; live fallback disabled",
        )

    if response_cache:
        reason = "not question-shaped; using prepared standup"
    else:
        reason = "response cache disabled; using prepared standup"
    return AutoResponseDecision(fallback, source="standup", reason=reason)


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

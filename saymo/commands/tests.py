"""Diagnostic / info commands: test-devices, test-tts, test-jira, list-plugins,
test-notes, test-compose, test-ollama, prepare-responses, trigger-check,
trigger-capture, trigger-learn, trigger-setup, trigger-eval, trigger-samples,
trigger-sessions, auto-preflight, takeover-check, provider-latency, mic-check."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import click
from rich.table import Table

from saymo.analysis.trigger_sessions import SESSION_LEDGER_DIR
from saymo.commands import console, main, run_async


_TRIGGER_SAMPLE_CATEGORIES = (
    "asked_to_speak",
    "mentioned_me",
    "question",
    "speech",
    "silence",
)


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

    playback = config.audio.playback_device
    monitor = config.audio.monitor_device
    devices = [playback]
    if monitor and monitor.lower() != playback.lower():
        devices.append(monitor)

    console.print(f"[blue]TTS engine: {config.tts.engine}[/]")
    console.print(f"[blue]Text: {text}[/]")
    console.print(f"[blue]Devices: {', '.join(devices)}[/]")

    try:
        tts = get_tts_engine(config)
    except UnsupportedTTSEngine as e:
        console.print(f"[bold red]{e}[/]")
        return

    audio_bytes = await tts.synthesize(text)
    if len(devices) > 1:
        from saymo.audio.multi_play import play_bytes_to_devices
        await play_bytes_to_devices(audio_bytes, devices)
    else:
        from saymo.audio.playback import play_audio_bytes
        await play_audio_bytes(audio_bytes, playback)

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


@main.command("diarization-check")
@click.option("--engine", default=None, help="Override configured diarization engine")
@click.option("--model", default=None, help="Override configured diarization model id")
@click.option("--device", default=None, help="Override configured diarization device")
@click.option(
    "--token-env",
    default=None,
    help="Override env var name that contains the backend token",
)
@click.pass_context
def diarization_check(ctx, engine, model, device, token_env):
    """Check optional local diarization backend setup."""
    from dataclasses import replace

    from saymo.analysis.diarization import check_diarization_availability

    config = ctx.obj["config"]
    diarization = config.diarization
    overrides = {}
    if engine is not None:
        overrides["enabled"] = engine.strip().lower() not in {"", "disabled", "off", "none"}
        overrides["engine"] = engine
    if model is not None:
        overrides["model"] = model
    if device is not None:
        overrides["device"] = device
    if token_env is not None:
        overrides["auth_token_env"] = token_env
    if overrides:
        diarization = replace(diarization, **overrides)

    status = check_diarization_availability(diarization)
    console.print(f"diarization: {status.status}")
    console.print(f"engine: {status.engine}")
    console.print(f"model: {status.model}")
    console.print(f"device: {status.device}")
    if status.token_env:
        console.print(f"token env: {status.token_env}")
        console.print(f"token: {'present' if status.token_available else 'missing'}")
    if status.missing:
        console.print(f"missing: {', '.join(status.missing)}")
    console.print(f"available: {'yes' if status.available else 'no'}")
    console.print(f"reason: {status.reason}")


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
# trigger diagnostics
# ---------------------------------------------------------------------------

@main.command("trigger-check")
@click.option("--profile", "-p", default="personal", help="Meeting profile to inspect")
@click.option("--text", default=None, help="Transcript text to inspect without recording")
@click.option("--mic", is_flag=True, help="Record a short microphone sample and transcribe it")
@click.option("--seconds", default=4.0, type=float, show_default=True, help="Seconds to record with --mic")
@click.option("--device", "-d", default=None, help="Input device name for --mic")
@click.option("--classifier-shadow", is_flag=True, help="Show local classifier confidence without changing the decision")
@click.option("--live-assist", is_flag=True, help="Show guarded live-assist classifier diagnostics")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with trigger-classifier artifacts")
@click.pass_context
def trigger_check(ctx, profile, text, mic, seconds, device, classifier_shadow, live_assist, model_dir):
    """Diagnose trigger, addressing, and response-cache routing.

    Use ``--text`` for a deterministic dry-run. Use ``--mic`` to record a
    short local sample through faster-whisper and run the same checks.
    """
    config = ctx.obj["config"]
    if mic:
        text = _trigger_check_record_text(config, device, seconds)
    if text is None:
        text = click.prompt("Transcript text")
    _print_trigger_diagnostics(
        config,
        profile,
        text,
        classifier_shadow=classifier_shadow,
        live_assist=live_assist,
        model_dir=model_dir,
    )


def _trigger_phrases_for_profile(config, profile: str) -> list[str]:
    meeting = config.get_meeting(profile)
    if meeting and meeting.trigger_phrases:
        return meeting.trigger_phrases
    return config.user.name_variants or ([config.user.name] if config.user.name else [])


def _print_trigger_diagnostics(
    config,
    profile: str,
    text: str,
    *,
    classifier_shadow: bool = False,
    live_assist: bool = False,
    model_dir: str | None = None,
) -> None:
    from saymo.analysis.addressing import (
        classify_addressing,
        expand_trigger_phrases,
        should_answer_decision,
    )
    from saymo.analysis.response_cache import ResponseCache, build_library
    from saymo.analysis.turn_detector import TurnDetector
    from saymo.commands.core import _trigger_confirmation_timeout

    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    expanded = expand_trigger_phrases(
        trigger_phrases,
        (config.vocabulary or {}).get("fuzzy_expansions"),
    )
    detector = TurnDetector(
        name_variants=trigger_phrases,
        cooldown_seconds=0,
        fuzzy_expansions=(config.vocabulary or {}).get("fuzzy_expansions"),
    )
    triggered = detector.check(text)
    decision = classify_addressing(text, expanded)
    will_answer = triggered and should_answer_decision(decision)
    confirmation_required = bool(getattr(config.safety, "require_confirmation", False))
    confirmation_timeout = _trigger_confirmation_timeout(config)
    if not will_answer:
        confirmation = "not_applicable"
        auto_action = "skip"
    elif confirmation_required:
        confirmation = f"required within {confirmation_timeout:.1f}s"
        auto_action = "wait_for_confirmation"
    else:
        confirmation = "disabled"
        auto_action = "answer_now"

    console.print(f"transcript: {text}")
    console.print(f"profile: {profile}")
    console.print(f"triggers: {', '.join(trigger_phrases) if trigger_phrases else '(none)'}")
    console.print(f"trigger: {'yes' if triggered else 'no'}")
    console.print(f"addressing: {decision.label} ({decision.reason})")
    console.print(f"question: {'yes' if decision.is_question else 'no'}")
    console.print(f"will answer: {'yes' if will_answer else 'no'}")
    console.print(f"confirmation: {confirmation}")
    console.print(f"auto action: {auto_action}")
    if classifier_shadow:
        _print_trigger_check_classifier_shadow(
            profile=profile,
            text=text,
            speaker="unknown",
            category=_current_trigger_category(text, will_answer, decision.is_question),
            trigger=triggered,
            question=decision.is_question,
            will_answer=will_answer,
            addressing=decision.label,
            model_dir=model_dir,
        )
    if live_assist:
        _print_trigger_check_live_assist(
            profile=profile,
            text=text,
            speaker="unknown",
            category=_current_trigger_category(text, will_answer, decision.is_question),
            trigger=triggered,
            question=decision.is_question,
            will_answer=will_answer,
            addressing=decision.label,
            model_dir=model_dir,
        )

    if not will_answer:
        console.print("response: skipped")
        return

    cache_dir = None
    if config.responses.cache_dir:
        from pathlib import Path
        cache_dir = Path(config.responses.cache_dir)
    cache = ResponseCache(
        library=build_library(config.responses.library),
        cache_dir=cache_dir,
        confidence_threshold=config.responses.confidence_threshold,
    )
    cached = cache.lookup(text)
    if cached:
        console.print(
            f"response: {cached.key} conf={cached.confidence:.2f} file={cached.audio_path}"
        )
    elif config.responses.live_fallback:
        console.print("response: live fallback would run")
    else:
        console.print("response: cache miss; would play generic standup audio")


# ---------------------------------------------------------------------------
# auto preflight
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PreflightCheck:
    name: str
    ok: bool
    detail: str
    blocking: bool = True


@main.command("auto-preflight")
@click.option("--profile", "-p", default="personal", help="Meeting profile to inspect")
@click.option("--provider", default=None, help="Override provider from profile")
@click.pass_context
def auto_preflight(ctx, profile, provider):
    """Check live-call readiness before running auto mode."""
    checks = _collect_auto_preflight(ctx.obj["config"], profile, provider_name=provider)
    _print_auto_preflight(profile, checks)


def _collect_auto_preflight(config, profile: str, provider_name: str | None = None) -> list[PreflightCheck]:
    from saymo.audio.devices import find_device
    from saymo.analysis.response_cache import ResponseCache, build_library
    from saymo.commands import _get_cached_audio_path
    from saymo.config import resolve_live_tuning
    from saymo.providers.factory import get_provider

    meeting = config.get_meeting(profile)
    team_mode = bool(meeting.team) if meeting else False
    resolved_provider = provider_name or (meeting.provider if meeting else "glip")
    checks: list[PreflightCheck] = []

    cached_audio = _get_cached_audio_path(team=team_mode)
    checks.append(
        PreflightCheck(
            "prepared standup",
            cached_audio.exists(),
            str(cached_audio),
        )
    )

    capture_name = config.audio.capture_device
    checks.append(
        PreflightCheck(
            "capture input",
            bool(find_device(capture_name, kind="input")),
            capture_name or "(not configured)",
        )
    )

    playback_name = config.audio.playback_device
    checks.append(
        PreflightCheck(
            "playback output",
            bool(find_device(playback_name, kind="output")),
            playback_name or "(not configured)",
        )
    )

    saymo_output = "BlackHole 2ch"
    checks.append(
        PreflightCheck(
            "provider output",
            bool(find_device(saymo_output, kind="output")),
            saymo_output,
        )
    )

    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    checks.append(
        PreflightCheck(
            "profile triggers",
            bool(trigger_phrases),
            ", ".join(trigger_phrases) if trigger_phrases else "(none)",
        )
    )

    try:
        provider = get_provider(resolved_provider)
        status = provider.check_ready()
        detail = provider.name
        if status.tab_info:
            detail += f" window={status.tab_info[0]} tab={status.tab_info[1]}"
        checks.append(
            PreflightCheck(
                "provider tab",
                bool(status.meeting_found),
                detail,
            )
        )
    except Exception as e:
        checks.append(PreflightCheck("provider tab", False, str(e)))

    if config.responses.enabled:
        cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None
        library = build_library(config.responses.library)
        cache = ResponseCache(
            library=library,
            cache_dir=cache_dir,
            confidence_threshold=config.responses.confidence_threshold,
        )
        total_variants = sum(len(entry.variants) for entry in library.values())
        cached_variants = sum(
            1
            for entry in library.values()
            for idx, text in enumerate(entry.variants)
            if cache._variant_path(entry.key, idx, text).exists()
        )
        checks.append(
            PreflightCheck(
                "response cache",
                cached_variants > 0 if total_variants else True,
                f"{cached_variants}/{total_variants} variants in {cache.cache_dir}",
                blocking=False,
            )
        )
    else:
        checks.append(
            PreflightCheck(
                "response cache",
                True,
                "disabled; prepared standup fallback only",
                blocking=False,
            )
        )

    live_tuning = resolve_live_tuning(config, meeting)
    checks.append(
        PreflightCheck(
            "live tuning",
            True,
            (
                f"window={live_tuning.chunk_seconds:.1f}s "
                f"overlap={live_tuning.overlap_seconds:.1f}s "
                f"cooldown={live_tuning.trigger_cooldown_seconds:.1f}s "
                f"silence_rms={live_tuning.silence_rms_threshold:.4f}"
            ),
            blocking=False,
        )
    )
    checks.append(
        PreflightCheck(
            "fallback",
            True,
            "live fallback enabled" if config.responses.live_fallback else "prepared standup on cache miss",
            blocking=False,
        )
    )
    return checks


def _print_auto_preflight(profile: str, checks: list[PreflightCheck]) -> None:
    ready = all(check.ok or not check.blocking for check in checks)
    console.print(f"profile: {profile}")
    for check in checks:
        if check.ok:
            label = "ok"
        elif check.blocking:
            label = "block"
        else:
            label = "warn"
        console.print(f"{label}: {check.name}: {check.detail}")
    console.print(f"preflight: {'ready' if ready else 'not ready'}")


@main.command("provider-latency")
@click.option("--profile", "-p", default="personal", help="Meeting profile to probe")
@click.option("--provider", default=None, help="Override provider from profile")
@click.option(
    "--text",
    default=None,
    help="Transcript text to use instead of recording call audio",
)
@click.option(
    "--seconds",
    default=4.0,
    type=click.FloatRange(min=0.1),
    show_default=True,
    help="Seconds to record when --text is omitted",
)
@click.option(
    "--device",
    "-d",
    default=None,
    help="Input device for call capture; defaults to audio.capture_device",
)
@click.option(
    "--audio",
    default=None,
    type=click.Path(),
    help="Audio file to play; defaults to today's prepared cache",
)
@click.option("--output-dir", default=None, type=click.Path(), help="Directory for JSON/Markdown history")
@click.option(
    "--settle-seconds",
    default=0.3,
    type=click.FloatRange(min=0.0),
    show_default=True,
    help="Provider settle delay around mute toggles",
)
@click.pass_context
def provider_latency(
    ctx,
    profile,
    provider,
    text,
    seconds,
    device,
    audio,
    output_dir,
    settle_seconds,
):
    """Measure provider call-control and playback latency for one probe."""
    config = ctx.obj["config"]
    if text is None:
        text = ""
    run_async(
        _run_provider_latency_probe(
            config,
            profile=profile,
            provider_name=provider,
            text=text,
            seconds=seconds,
            device_name=device,
            audio=audio,
            output_dir=output_dir,
            settle_seconds=settle_seconds,
        )
    )


async def _run_provider_latency_probe(
    config,
    *,
    profile: str,
    provider_name: str | None,
    text: str,
    seconds: float,
    device_name: str | None,
    audio: str | None,
    output_dir: str | None,
    settle_seconds: float,
) -> None:
    import asyncio
    import time
    from datetime import datetime, timezone

    from saymo.analysis.provider_latency import ProviderLatencySegment
    from saymo.analysis.trigger_capture import classify_trigger_sample
    from saymo.commands import _get_cached_audio_path
    from saymo.providers.factory import get_provider

    segments: list[ProviderLatencySegment] = []
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meeting = config.get_meeting(profile)
    resolved_provider = provider_name or (meeting.provider if meeting else "glip")
    team_mode = bool(meeting.team) if meeting else False
    audio_path = Path(audio).expanduser() if audio else _get_cached_audio_path(team=team_mode)

    console.print(f"provider latency: profile={profile} provider={resolved_provider}")

    if text:
        segments.append(ProviderLatencySegment("capture", 0.0, detail="source=text"))
        segments.append(ProviderLatencySegment("transcription", 0.0, detail="source=text"))
        transcript = " ".join(text.split())
    else:
        transcript, capture_ms, transcription_ms = _provider_latency_record_text(
            config,
            device_name,
            seconds,
        )
        segments.append(ProviderLatencySegment("capture", capture_ms, detail="source=call"))
        segments.append(ProviderLatencySegment("transcription", transcription_ms, detail="local_whisper"))

    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    trigger_t0 = time.monotonic()
    sample = classify_trigger_sample(
        transcript,
        trigger_phrases,
        (config.vocabulary or {}).get("fuzzy_expansions") or {},
    )
    trigger_ms = (time.monotonic() - trigger_t0) * 1000
    action = "answer" if sample.will_answer else "skip"
    segments.append(
        ProviderLatencySegment(
            "trigger",
            trigger_ms,
            detail=(
                f"trigger={'yes' if sample.trigger else 'no'} "
                f"question={'yes' if sample.question else 'no'} "
                f"action={action}"
            ),
        )
    )
    decision_done_t = time.monotonic()

    if not sample.will_answer:
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="trigger",
            blocked_reason="deterministic trigger/addressing gate would skip",
            segments=segments,
            output_dir=output_dir,
        )
        return

    if not audio_path.exists():
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="audio",
            blocked_reason=f"audio file not found: {audio_path}",
            segments=segments,
            output_dir=output_dir,
        )
        return

    provider = get_provider(resolved_provider)
    check_t0 = time.monotonic()
    status = provider.check_ready()
    check_ms = (time.monotonic() - check_t0) * 1000
    segments.append(
        ProviderLatencySegment(
            "provider_check",
            check_ms,
            status="ok" if status.meeting_found else "blocked",
            detail=f"tab={status.tab_info}" if status.tab_info else "tab=not_found",
        )
    )
    if not status.meeting_found:
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="provider_tab",
            blocked_reason=(
                f"{getattr(provider, 'name', resolved_provider)} "
                "tab not found in Chrome"
            ),
            segments=segments,
            output_dir=output_dir,
        )
        return

    from saymo.audio.devices import find_device

    if not find_device("BlackHole 2ch", kind="output"):
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="playback_output",
            blocked_reason="BlackHole 2ch output not found",
            segments=segments,
            output_dir=output_dir,
        )
        return

    switch_t0 = time.monotonic()
    mic_switched = provider.switch_mic("BlackHole 2ch")
    segments.append(
        ProviderLatencySegment(
            "mic_switch",
            (time.monotonic() - switch_t0) * 1000,
            detail="ok" if mic_switched else "not_supported_or_unchanged",
        )
    )

    previous_app = ""
    try:
        previous_app = provider.get_previous_app()
    except Exception:
        previous_app = ""

    try:
        unmute_t0 = time.monotonic()
        if not provider.activate_meeting():
            raise RuntimeError(
                f"Cannot activate {getattr(provider, 'name', resolved_provider)} tab"
            )
        await asyncio.sleep(settle_seconds)
        provider.toggle_mute()
        await asyncio.sleep(settle_seconds)
        segments.append(
            ProviderLatencySegment(
                "provider_unmute",
                (time.monotonic() - unmute_t0) * 1000,
            )
        )
    except Exception as e:
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="provider_unmute",
            blocked_reason=str(e),
            segments=segments,
            output_dir=output_dir,
        )
        return

    audio_bytes = audio_path.read_bytes()
    playback_start_ms: float | None = None
    playback_started_t: float | None = None

    def mark_playback_started() -> None:
        nonlocal playback_start_ms, playback_started_t
        if playback_start_ms is not None:
            return
        playback_started_t = time.monotonic()
        playback_start_ms = (playback_started_t - decision_done_t) * 1000

    try:
        play_t0 = time.monotonic()
        await _provider_latency_play_audio(config, audio_bytes, mark_playback_started)
        playback_end_t = time.monotonic()
        segments.append(
            ProviderLatencySegment(
                "playback_start",
                playback_start_ms if playback_start_ms is not None else 0.0,
                status="ok" if playback_start_ms is not None else "blocked",
                detail="from_trigger_decision",
            )
        )
        duration_base = playback_started_t or play_t0
        segments.append(
            ProviderLatencySegment(
                "playback_duration",
                (playback_end_t - duration_base) * 1000,
            )
        )
    except Exception as e:
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="playback",
            blocked_reason=str(e),
            segments=segments,
            output_dir=output_dir,
        )
        return

    try:
        mute_t0 = time.monotonic()
        provider.activate_meeting()
        await asyncio.sleep(settle_seconds)
        provider.toggle_mute()
        await asyncio.sleep(settle_seconds)
        if previous_app and previous_app != "Google Chrome":
            provider.activate_app(previous_app)
        segments.append(
            ProviderLatencySegment(
                "mute_recovery",
                (time.monotonic() - mute_t0) * 1000,
                detail=f"restored={previous_app}" if previous_app else "",
            )
        )
    except Exception as e:
        await _finalize_provider_latency_report(
            profile=profile,
            provider=resolved_provider,
            created_at=created_at,
            status="blocked",
            transcript=transcript,
            action=action,
            audio_path=audio_path,
            blocked_step="mute_recovery",
            blocked_reason=str(e),
            segments=segments,
            output_dir=output_dir,
        )
        return

    await _finalize_provider_latency_report(
        profile=profile,
        provider=resolved_provider,
        created_at=created_at,
        status="ok",
        transcript=transcript,
        action=action,
        audio_path=audio_path,
        blocked_step="",
        blocked_reason="",
        segments=segments,
        output_dir=output_dir,
    )


def _provider_latency_record_text(config, device_name: str | None, seconds: float) -> tuple[str, float, float]:
    import time
    import sounddevice as sd
    from saymo.stt.whisper_local import LocalWhisper

    mic_name, mic = _resolve_provider_latency_capture_device(config, device_name)
    if not mic or not mic_name:
        raise click.ClickException("No input device available")

    capture_t0 = time.monotonic()
    audio = _record_buffer(sd, 16000, seconds, mic.index)
    capture_ms = (time.monotonic() - capture_t0) * 1000
    transcribe_t0 = time.monotonic()
    whisper = LocalWhisper(
        model_size=config.stt.whisper.model_size,
        language=config.user.language,
    )
    text = whisper.transcribe(audio)
    transcription_ms = (time.monotonic() - transcribe_t0) * 1000
    return text, capture_ms, transcription_ms


def _resolve_provider_latency_capture_device(config, device_override: str | None):
    from saymo.audio.devices import find_device

    name = device_override or config.audio.capture_device or config.audio.recording_device
    if name:
        dev = find_device(name, kind="input")
        if not dev:
            raise click.ClickException(f"Input device not found: {name}")
        return name, dev
    return _resolve_input_device(config, None)


async def _provider_latency_play_audio(config, audio_bytes: bytes, mark_playback_started) -> None:
    playback = "BlackHole 2ch"
    monitor = config.audio.monitor_device
    if monitor and monitor.lower() != playback.lower():
        from saymo.audio.multi_play import play_bytes_to_devices

        mark_playback_started()
        await play_bytes_to_devices(audio_bytes, [playback, monitor])
        return

    from saymo.audio.playback import play_audio_bytes

    mark_playback_started()
    await play_audio_bytes(audio_bytes, playback)


async def _finalize_provider_latency_report(
    *,
    profile: str,
    provider: str,
    created_at: str,
    status: str,
    transcript: str,
    action: str,
    audio_path: Path,
    blocked_step: str,
    blocked_reason: str,
    segments: list,
    output_dir: str | None,
) -> None:
    from saymo.analysis.provider_latency import ProviderLatencyReport, write_latency_history

    report = ProviderLatencyReport(
        profile=profile,
        provider=provider,
        created_at=created_at,
        status=status,
        transcript=transcript,
        action=action,
        audio_path=str(audio_path),
        blocked_step=blocked_step,
        blocked_reason=blocked_reason,
        segments=segments,
    )
    _print_provider_latency_report(report)
    json_path, md_path = write_latency_history(report, output_dir)
    console.print(f"history json: {json_path}")
    console.print(f"history markdown: {md_path}")


def _print_provider_latency_report(report) -> None:
    labels = {
        "provider_unmute": "provider unmute",
        "playback_start": "playback start",
        "playback_duration": "playback duration",
        "mute_recovery": "mute recovery",
    }
    for segment in report.segments:
        label = labels.get(segment.name, segment.name.replace("_", " "))
        detail = f" {segment.detail}" if segment.detail else ""
        console.print(f"{label}: {segment.duration_ms:.0f}ms{detail}")
    console.print(f"probe: {report.status}")
    if report.blocked_step:
        console.print(f"blocked: {report.blocked_step}: {report.blocked_reason}")


@main.command("trigger-capture")
@click.option("--profile", "-p", default="personal", help="Meeting profile to inspect")
@click.option(
    "--window",
    default=8.0,
    type=float,
    show_default=True,
    help="Window length in seconds",
)
@click.option(
    "--duration",
    default=0.0,
    type=float,
    show_default=True,
    help="Total seconds; 0 means until Ctrl+C",
)
@click.option(
    "--device",
    "-d",
    default=None,
    help="Input device name; defaults to audio.capture_device",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(),
    help="Directory for captured samples",
)
@click.option("--save-silence", is_flag=True, help="Also save empty/silent windows")
@click.option(
    "--session",
    "session_name",
    default=None,
    help="Name for this capture session; defaults to the profile name",
)
@click.pass_context
def trigger_capture(
    ctx,
    profile,
    window,
    duration,
    device,
    output_dir,
    save_silence,
    session_name,
):
    """Capture live call audio into classified trigger samples."""
    config = ctx.obj["config"]
    _run_trigger_capture(
        config,
        profile=profile,
        window_seconds=window,
        duration_seconds=duration,
        device_name=device,
        output_dir=output_dir,
        save_silence=save_silence,
        session_name=session_name,
    )


def _run_trigger_capture(
    config,
    *,
    profile: str,
    window_seconds: float,
    duration_seconds: float,
    device_name: str | None,
    output_dir: str | None,
    save_silence: bool,
    session_name: str | None = None,
) -> None:
    from datetime import datetime
    from pathlib import Path
    import queue
    import time

    import numpy as np
    import sounddevice as sd

    from saymo.analysis.trigger_capture import (
        audio_stats,
        classify_trigger_sample,
        save_trigger_sample,
    )
    from saymo.analysis.trigger_sessions import (
        finish_trigger_session,
        start_trigger_session,
    )
    from saymo.stt.whisper_local import LocalWhisper

    if window_seconds <= 0:
        raise click.ClickException("--window must be greater than zero")
    if duration_seconds < 0:
        raise click.ClickException("--duration cannot be negative")

    mic_name, mic = _resolve_trigger_capture_device(config, device_name)
    if not mic or not mic_name:
        raise click.ClickException("No input device available")

    sample_rate = 16000
    target_frames = int(window_seconds * sample_rate)
    base_dir = (
        Path(output_dir).expanduser()
        if output_dir
        else Path.home() / ".saymo" / "trigger_samples"
    )
    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    fuzzy = (config.vocabulary or {}).get("fuzzy_expansions") or {}
    whisper = LocalWhisper(
        model_size=config.stt.whisper.model_size,
        language=config.user.language,
    )
    session = start_trigger_session(
        base_dir=base_dir,
        profile=profile,
        session_name=session_name,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    audio_queue: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            console.print(f"[yellow]{status}[/]")
        audio_queue.put(np.asarray(indata, dtype=np.float32).copy().flatten())

    console.print(f"[bold blue]Capturing {mic_name} → {base_dir}[/]")
    console.print(f"[blue]Session: {session.session_id} ({session.session_name})[/]")
    console.print(
        "[dim]Categories: asked_to_speak, mentioned_me, question, speech"
        + (", silence" if save_silence else "")
        + "[/]"
    )
    console.print("[dim]Stop with Ctrl+C[/]")

    start = time.monotonic()
    chunks: list[np.ndarray] = []
    frames_seen = 0
    sequence = 1
    skipped_silence = 0
    status = "completed"

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            device=mic.index,
            channels=1,
            dtype="float32",
            callback=callback,
        ):
            while duration_seconds == 0 or time.monotonic() - start < duration_seconds:
                try:
                    block = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                chunks.append(block)
                frames_seen += len(block)
                if frames_seen < target_frames:
                    continue

                audio = np.concatenate(chunks).astype(np.float32)
                chunks = []
                frames_seen = 0
                rms, peak = audio_stats(audio)
                text = whisper.transcribe(audio)
                sample = classify_trigger_sample(
                    text,
                    trigger_phrases,
                    fuzzy,
                    rms=rms,
                    peak=peak,
                )
                if sample.category == "silence" and not save_silence:
                    skipped_silence += 1
                    console.print(
                        f"[dim]skip silence rms={rms:.4f} peak={peak:.4f}[/]"
                    )
                    continue

                created_at = datetime.now().isoformat(timespec="seconds")
                wav_path, _ = save_trigger_sample(
                    audio,
                    sample_rate=sample_rate,
                    sample=sample,
                    base_dir=base_dir,
                    profile=profile,
                    sequence=sequence,
                    created_at=created_at,
                    session_id=session.session_id,
                    session_name=session.session_name,
                )
                console.print(
                    f"[bold]{sample.category}[/] "
                    f"trigger={'yes' if sample.trigger else 'no'} "
                    f"question={'yes' if sample.question else 'no'} "
                    f"rms={sample.rms:.4f} peak={sample.peak:.4f} "
                    f"file={wav_path}"
                )
                if sample.transcript:
                    console.print(f"[dim]  {sample.transcript}[/]")
                sequence += 1
    except KeyboardInterrupt:
        status = "stopped"
        console.print("[yellow]Stopped trigger capture[/]")
    except Exception:
        status = "failed"
        raise
    finally:
        finished = finish_trigger_session(
            base_dir=base_dir,
            session=session,
            ended_at=datetime.now().isoformat(timespec="seconds"),
            status=status,
            skipped_silence=skipped_silence,
        )
        _print_trigger_session_summary(finished)


def _resolve_trigger_capture_device(config, device_override: str | None):
    from saymo.audio.devices import find_device

    name = device_override or config.audio.capture_device or config.audio.recording_device
    if name:
        dev = find_device(name, kind="input")
        if not dev:
            raise click.ClickException(f"Input device not found: {name}")
        return name, dev
    return _resolve_input_device(config, None)


def _trigger_check_record_text(config, device_name: str | None, seconds: float) -> str:
    import sounddevice as sd
    from saymo.stt.whisper_local import LocalWhisper

    mic_name, mic = _resolve_input_device(config, device_name)
    if not mic or not mic_name:
        raise click.ClickException("No input device available")

    console.print(f"[bold blue]Recording {seconds:.1f}s from {mic_name}...[/]")
    audio = _record_buffer(sd, 16000, seconds, mic.index)
    whisper = LocalWhisper(
        model_size=config.stt.whisper.model_size,
        language=config.user.language,
    )
    text = whisper.transcribe(audio)
    console.print(f"[dim]transcribed: {text}[/]")
    return text


@main.command("trigger-learn")
@click.option("--profile", "-p", default="personal", help="Meeting profile to update")
@click.option("--heard", default=None, help="Text Whisper heard for your trigger")
@click.option("--trigger", default=None, help="Canonical trigger phrase to extend")
@click.option("--mic", is_flag=True, help="Record and learn from a short microphone sample")
@click.option("--seconds", default=4.0, type=float, show_default=True, help="Seconds to record with --mic")
@click.option("--device", "-d", default=None, help="Input device name for --mic")
@click.pass_context
def trigger_learn(ctx, profile, heard, trigger, mic, seconds, device):
    """Add a heard trigger variant to vocabulary.fuzzy_expansions."""
    config = ctx.obj["config"]
    if mic:
        heard = _trigger_check_record_text(config, device, seconds)
    if heard is None:
        heard = click.prompt("Heard trigger text")
    config_path = _config_path_for_update(ctx)
    canonical = trigger or _default_trigger_for_profile(config, profile)
    learned = _learn_trigger_variant(config_path, canonical, heard)

    console.print(f"config: {config_path}")
    console.print(f"trigger: {canonical}")
    console.print(f"variant: {heard.strip()}")
    console.print(f"learned: {'yes' if learned else 'no'}")


@main.command("trigger-setup")
@click.option("--profile", "-p", default="personal", help="Meeting profile to update")
@click.option("--heard", default=None, help="Text Whisper heard for your trigger")
@click.option("--trigger", default=None, help="Canonical trigger phrase to extend")
@click.option("--mic", is_flag=True, help="Record and learn from a short microphone sample")
@click.option("--seconds", default=4.0, type=float, show_default=True, help="Seconds to record with --mic")
@click.option("--device", "-d", default=None, help="Input device name for --mic")
@click.pass_context
def trigger_setup(ctx, profile, heard, trigger, mic, seconds, device):
    """Learn a trigger variant and verify that auto-mode will catch it."""
    from saymo.config import load_config

    config = ctx.obj["config"]
    if mic:
        heard = _trigger_check_record_text(config, device, seconds)
    if heard is None:
        heard = click.prompt("Heard trigger text")

    config_path = _config_path_for_update(ctx)
    canonical = trigger or _default_trigger_for_profile(config, profile)
    variant = _extract_trigger_variant(heard)
    learned = _learn_trigger_variant(config_path, canonical, variant)
    updated = load_config(str(config_path))
    matches = _trigger_matches(updated, profile, heard)

    console.print(f"config: {config_path}")
    console.print(f"trigger: {canonical}")
    console.print(f"heard: {heard.strip()}")
    console.print(f"variant: {variant}")
    console.print(f"learned: {'yes' if learned else 'no'}")
    console.print(f"trigger after learning: {'yes' if matches else 'no'}")
    if not matches:
        console.print("reason: learned text still does not match trigger detector")


def _default_trigger_for_profile(config, profile: str) -> str:
    phrases = _trigger_phrases_for_profile(config, profile)
    if not phrases:
        raise click.ClickException(f"No trigger phrases configured for profile: {profile}")
    return phrases[0]


def _config_path_for_update(ctx):
    from pathlib import Path

    root = ctx.find_root()
    config_path = root.params.get("config_path") if root else None
    if config_path:
        return Path(config_path).expanduser()
    return Path.home() / ".saymo" / "config.yaml"


def _learn_trigger_variant(config_path, trigger: str, heard: str) -> bool:
    import yaml

    variant = " ".join((heard or "").split()).strip(" ,:;—-")
    if not variant:
        raise click.ClickException("Heard trigger text is empty")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}

    vocabulary = data.get("vocabulary")
    if not isinstance(vocabulary, dict):
        vocabulary = {}
    fuzzy = vocabulary.get("fuzzy_expansions")
    if not isinstance(fuzzy, dict):
        fuzzy = {}

    variants = fuzzy.get(trigger)
    if not isinstance(variants, list):
        variants = []
    existing = {str(v).casefold() for v in variants}
    if variant.casefold() == trigger.casefold() or variant.casefold() in existing:
        fuzzy[trigger] = variants
        vocabulary["fuzzy_expansions"] = fuzzy
        data["vocabulary"] = vocabulary
        config_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return False

    variants.append(variant)
    fuzzy[trigger] = variants
    vocabulary["fuzzy_expansions"] = fuzzy
    data["vocabulary"] = vocabulary
    config_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return True


def _extract_trigger_variant(heard: str) -> str:
    """Extract the likely name variant from a transcribed setup phrase."""
    variant = " ".join((heard or "").split()).strip(" ,:;—-")
    if not variant:
        return ""
    for sep in (",", "?", "!", ":", ";", "—", " - "):
        if sep in variant:
            variant = variant.split(sep, 1)[0].strip(" ,:;—-")
            break
    markers = (
        "что", "как", "где", "когда", "почему", "зачем", "кто",
        "сколько", "какие", "какой", "какая", "расскажи", "поделись",
        "опиши", "what", "how", "why", "when", "where", "who",
        "tell me", "can you", "could you", "do you",
    )
    marker_pattern = "|".join(re.escape(marker) for marker in markers)
    match = re.search(rf"\s+(?:{marker_pattern})(?:\s|$)", variant, re.IGNORECASE)
    if match and match.start() > 0:
        variant = variant[:match.start()].strip(" ,:;—-")
    return variant


def _trigger_matches(config, profile: str, text: str) -> bool:
    from saymo.analysis.turn_detector import TurnDetector

    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    detector = TurnDetector(
        name_variants=trigger_phrases,
        cooldown_seconds=0,
        fuzzy_expansions=(config.vocabulary or {}).get("fuzzy_expansions"),
    )
    return detector.check(text)


# ---------------------------------------------------------------------------
# trigger sample review / evaluation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TriggerSampleRecord:
    path: Path
    profile: str
    category: str
    session_id: str
    session_name: str
    session_sequence: int
    speaker: str
    answer_decision: str
    created_at: str
    transcript: str
    trigger: bool
    question: bool
    will_answer: bool
    addressing: str
    reason: str
    rms: float
    peak: float
    wav: str


@dataclass(frozen=True)
class TriggerEvaluationRow:
    record: TriggerSampleRecord
    current_category: str
    current_trigger: bool
    current_question: bool
    current_will_answer: bool
    current_addressing: str
    miss: bool
    false_positive: bool


_SPEAKER_LABELS = ("me", "other", "unknown")
_ANSWER_DECISION_LABELS = ("accepted", "rejected", "unlabeled")


def _normalize_speaker_label(value) -> str:
    label = str(value or "").strip().lower()
    if label in _SPEAKER_LABELS:
        return label
    return "unknown"


def _normalize_answer_decision(value) -> str:
    from saymo.analysis.trigger_classifier import normalize_decision_label

    return normalize_decision_label(value)


@main.command("trigger-eval")
@click.option("--profile", "-p", default="personal", help="Meeting profile to evaluate")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option(
    "--promote",
    default=None,
    type=click.Path(exists=True),
    help="Learn trigger variant from this sample JSON before evaluation",
)
@click.option("--classifier-shadow", is_flag=True, help="Show local classifier confidence without changing decisions")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with trigger-classifier artifacts")
@click.pass_context
def trigger_eval(ctx, profile, samples_dir, promote, classifier_shadow, model_dir):
    """Evaluate saved trigger samples against current trigger config."""
    config = ctx.obj["config"]
    if promote:
        config = _promote_trigger_sample(ctx, config, profile, Path(promote))
    records = list(_iter_trigger_sample_records(_samples_base_dir(samples_dir), profile))
    rows = _evaluate_trigger_records(config, profile, records)
    _print_trigger_evaluation(rows)
    if classifier_shadow:
        _print_classifier_shadow_evaluation(rows, profile=profile, model_dir=model_dir)


@main.group("trigger-samples")
def trigger_samples():
    """Inspect, replay, and report saved trigger samples."""


@trigger_samples.command("list")
@click.option("--profile", "-p", default=None, help="Profile to list")
@click.option("--category", default=None, help="Category to filter")
@click.option("--session", "session_id", default=None, help="Session id/prefix to filter")
@click.option("--speaker", default=None, type=click.Choice(_SPEAKER_LABELS), help="Speaker label to filter")
@click.option("--decision", default=None, type=click.Choice(_ANSWER_DECISION_LABELS), help="Answer decision to filter")
@click.option("--date-from", default=None, help="Inclusive created_at lower bound")
@click.option("--date-to", default=None, help="Inclusive created_at upper bound")
@click.option("--classifier-disagreement", is_flag=True, help="Only show rows where classifier and deterministic decision disagree")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with trigger-classifier artifacts")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.pass_context
def trigger_samples_list(ctx, profile, category, session_id, speaker, decision, date_from, date_to, classifier_disagreement, model_dir, samples_dir):
    """List captured trigger-sample metadata without opening JSON manually."""
    from saymo.analysis.trigger_review import TriggerReviewFilters

    records = list(
        _iter_trigger_sample_records(
            _samples_base_dir(samples_dir),
            profile=profile,
            category=category,
        )
    )
    filters = TriggerReviewFilters(
        session=session_id,
        speaker=speaker,
        answer_decision=decision,
        date_from=date_from,
        date_to=date_to,
    )
    records = _filter_review_rows_or_fail(records, filters)
    if classifier_disagreement:
        if not profile:
            raise click.ClickException("--classifier-disagreement requires --profile")
        rows = _evaluate_trigger_records(ctx.obj["config"], profile, records)
        records = [
            row.record
            for row in _filter_classifier_disagreements(
                rows,
                profile=profile,
                model_dir=model_dir,
            )
        ]
    console.print(f"samples: {len(records)}")
    for record in records:
        session = f" session={record.session_id}" if record.session_id else ""
        console.print(
            f"{record.path}: profile={record.profile} category={record.category} "
            f"{session} "
            f"speaker={record.speaker} "
            f"decision={record.answer_decision} "
            f"trigger={'yes' if record.trigger else 'no'} "
            f"question={'yes' if record.question else 'no'} "
            f"will_answer={'yes' if record.will_answer else 'no'} "
            f"rms={record.rms:.4f} peak={record.peak:.4f}"
        )
        if record.transcript:
            console.print(f"  transcript: {record.transcript}")


@trigger_samples.command("replay")
@click.argument("sample_json", type=click.Path(exists=True))
@click.option("--profile", "-p", default=None, help="Profile to reclassify with")
@click.option("--play/--no-play", default=True, show_default=True, help="Play adjacent WAV")
@click.pass_context
def trigger_samples_replay(ctx, sample_json, profile, play):
    """Replay one sample and compare stored/current classification."""
    config = ctx.obj["config"]
    record = _load_trigger_sample(Path(sample_json))
    resolved_profile = profile or record.profile
    row = _evaluate_trigger_records(config, resolved_profile, [record])[0]

    console.print(f"sample: {record.path}")
    console.print(
        f"stored: category={record.category} speaker={record.speaker} "
        f"decision={record.answer_decision} "
        f"trigger={'yes' if record.trigger else 'no'} "
        f"question={'yes' if record.question else 'no'} "
        f"will_answer={'yes' if record.will_answer else 'no'}"
    )
    console.print(
        f"current: category={row.current_category} "
        f"trigger={'yes' if row.current_trigger else 'no'} "
        f"question={'yes' if row.current_question else 'no'} "
        f"will_answer={'yes' if row.current_will_answer else 'no'}"
    )
    _print_record_speaker_suggestion(record, samples_dir=None)
    console.print(f"action: {'answer' if row.current_will_answer else 'skip'}")
    if record.transcript:
        console.print(f"transcript: {record.transcript}")

    if play:
        _play_trigger_sample(record)


@trigger_samples.command("label")
@click.argument("sample_json", type=click.Path(exists=True))
@click.option(
    "--speaker",
    required=True,
    type=click.Choice(_SPEAKER_LABELS),
    help="Speaker label to write into sample metadata",
)
def trigger_samples_label(sample_json, speaker):
    """Set or correct the speaker label for one captured sample."""
    previous = _write_trigger_sample_speaker(Path(sample_json), speaker)
    console.print(f"sample: {sample_json}")
    console.print(f"speaker: {previous} -> {speaker}")


@trigger_samples.command("speaker-suggestion")
@click.argument("sample_json", type=click.Path(exists=True))
@click.option("--accept", is_flag=True, help="Apply the suggested speaker label")
@click.option("--reject", is_flag=True, help="Reject the suggestion without changing sample metadata")
@click.option(
    "--label",
    default=None,
    type=click.Choice(_SPEAKER_LABELS),
    help="Override with an explicit speaker label and apply it",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
def trigger_samples_speaker_suggestion(sample_json, accept, reject, label, samples_dir):
    """Show, accept, reject, or override one sample's speaker suggestion."""
    record = _load_trigger_sample(Path(sample_json))
    loaded = _load_record_speaker_suggestion(record, samples_dir, require=True)
    if loaded is None:
        raise click.ClickException("Speaker suggestion not found")
    _, _, _, suggestion = loaded
    _print_speaker_suggestion(record, suggestion)

    requested_actions = sum(1 for enabled in (accept, reject, label is not None) if enabled)
    if requested_actions > 1:
        raise click.ClickException("Choose only one of --accept, --reject, or --label")
    if requested_actions == 0:
        return

    if accept:
        action = "accept"
        override_label = None
    elif reject:
        action = "reject"
        override_label = None
    else:
        action = "override"
        override_label = label
    _apply_record_speaker_suggestion_review(
        record,
        samples_dir,
        action=action,
        label=override_label,
    )


@trigger_samples.command("decision")
@click.argument("sample_json", type=click.Path(exists=True))
@click.option(
    "--decision",
    required=True,
    type=click.Choice(_ANSWER_DECISION_LABELS),
    help="Answer decision label to write into sample metadata",
)
def trigger_samples_decision(sample_json, decision):
    """Set accepted/rejected/unlabeled answer decision for one sample."""
    previous = _write_trigger_sample_decision(Path(sample_json), decision)
    console.print(f"sample: {sample_json}")
    console.print(f"decision: {previous} -> {decision}")


@trigger_samples.command("category")
@click.argument("sample_json", type=click.Path(exists=True))
@click.option(
    "--category",
    required=True,
    type=click.Choice(_TRIGGER_SAMPLE_CATEGORIES),
    help="Target sample category",
)
def trigger_samples_category(sample_json, category):
    """Move a sample JSON/WAV pair to a corrected category."""
    from saymo.analysis.trigger_review import apply_category_relabel

    result = apply_category_relabel(Path(sample_json), category)
    console.print(f"sample: {result.path}")
    console.print(f"category: {result.previous_category} -> {result.category}")
    console.print(f"wav: {result.wav_path if result.wav_moved else 'missing'}")


@trigger_samples.command("review")
@click.option("--profile", "-p", default="personal", help="Profile to review")
@click.option("--category", default=None, help="Category to filter")
@click.option("--session", "session_id", default=None, help="Session id/prefix to filter")
@click.option("--speaker", default=None, type=click.Choice(_SPEAKER_LABELS), help="Speaker label to filter")
@click.option("--decision", default=None, type=click.Choice(_ANSWER_DECISION_LABELS), help="Answer decision to filter")
@click.option("--date-from", default=None, help="Inclusive created_at lower bound")
@click.option("--date-to", default=None, help="Inclusive created_at upper bound")
@click.option("--limit", default=0, type=click.IntRange(min=0), show_default=True, help="Maximum samples; 0 means all")
@click.option("--play/--no-play", default=True, show_default=True, help="Play adjacent WAV before prompting")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.pass_context
def trigger_samples_review(ctx, profile, category, session_id, speaker, decision, date_from, date_to, limit, play, samples_dir):
    """Replay and relabel a filtered trigger-sample queue."""
    from saymo.analysis.trigger_review import TriggerReviewFilters, apply_category_relabel, parse_review_action

    records = list(
        _iter_trigger_sample_records(
            _samples_base_dir(samples_dir),
            profile=profile,
            category=category,
        )
    )
    records = _filter_review_rows_or_fail(
        records,
        TriggerReviewFilters(
            session=session_id,
            speaker=speaker,
            answer_decision=decision,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    if limit:
        records = records[:limit]
    console.print(f"review samples: {len(records)}")
    for index, record in enumerate(records, start=1):
        row = _evaluate_trigger_records(ctx.obj["config"], profile, [record])[0]
        console.print(f"[{index}/{len(records)}] {record.path}")
        console.print(
            f"stored category={record.category} speaker={record.speaker} "
            f"decision={record.answer_decision}"
        )
        console.print(
            f"current category={row.current_category} "
            f"will_answer={'yes' if row.current_will_answer else 'no'}"
        )
        _print_record_speaker_suggestion(record, samples_dir=samples_dir)
        if play:
            _play_trigger_sample(record)
        while True:
            raw_action = click.prompt(
                "action",
                default="skip",
                show_default=True,
            )
            action = parse_review_action(raw_action)
            if action is None:
                console.print("unknown action")
                continue
            if action.kind == "skip":
                break
            if action.kind == "quit":
                console.print("review stopped")
                return
            if action.kind == "category":
                result = apply_category_relabel(record.path, action.value)
                record = _load_trigger_sample(result.path)
                console.print(f"category: {result.previous_category} -> {result.category}")
                continue
            if action.kind == "speaker":
                previous = _write_trigger_sample_speaker(record.path, action.value)
                record = _load_trigger_sample(record.path)
                console.print(f"speaker: {previous} -> {action.value}")
                continue
            if action.kind == "decision":
                previous = _write_trigger_sample_decision(record.path, action.value)
                record = _load_trigger_sample(record.path)
                console.print(f"decision: {previous} -> {action.value}")
                continue
            if action.kind.startswith("speaker_suggestion_"):
                record = _apply_record_speaker_suggestion_review(
                    record,
                    samples_dir,
                    action=action.kind.removeprefix("speaker_suggestion_"),
                    label=action.value,
                )
                continue
    console.print("review complete")


@trigger_samples.command("report")
@click.option("--profile", "-p", default="personal", help="Profile to report")
@click.option("--session", "session_id", default=None, help="Session id/prefix to filter")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option("--output", "-o", default=None, type=click.Path(), help="Markdown output path")
@click.pass_context
def trigger_samples_report(ctx, profile, session_id, samples_dir, output):
    """Export a sanitized trigger-sample report without audio or private config."""
    from saymo.analysis.trigger_review import TriggerReviewFilters, render_grouped_trigger_report

    records = _filter_review_rows_or_fail(
        list(_iter_trigger_sample_records(_samples_base_dir(samples_dir), profile)),
        TriggerReviewFilters(session=session_id),
    )
    rows = _evaluate_trigger_records(ctx.obj["config"], profile, records)
    report = render_grouped_trigger_report(profile, rows)
    if output:
        out_path = Path(output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        console.print(f"report: {out_path}")
    else:
        console.print(report)


@main.group("trigger-sessions")
def trigger_sessions():
    """List and summarize trigger-capture sessions."""


@trigger_sessions.command("list")
@click.option("--profile", "-p", default=None, help="Profile to list")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
def trigger_sessions_list(profile, samples_dir):
    """List prior trigger-capture sessions."""
    from saymo.analysis.trigger_sessions import list_trigger_sessions

    sessions = list_trigger_sessions(_samples_base_dir(samples_dir), profile=profile)
    console.print(f"sessions: {len(sessions)}")
    for session in sessions:
        summary = session.summary
        ended = session.ended_at or "-"
        console.print(
            f"{session.session_id}: profile={session.profile} "
            f"name={session.session_name} status={session.status} "
            f"started={session.started_at or '-'} ended={ended} "
            f"samples={summary.saved_samples} "
            f"skipped_silence={summary.skipped_silence} "
            f"readiness={summary.readiness}"
        )


@trigger_sessions.command("summary")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to summarize; unique prefixes are accepted",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
def trigger_sessions_summary(profile, session_id, samples_dir):
    """Show one trigger-capture session summary."""
    from saymo.analysis.trigger_sessions import list_trigger_sessions

    sessions = [
        s
        for s in list_trigger_sessions(_samples_base_dir(samples_dir), profile=profile)
        if s.session_id == session_id or s.session_id.startswith(session_id)
    ]
    if not sessions:
        raise click.ClickException(f"Session not found: {session_id}")
    if len(sessions) > 1:
        raise click.ClickException(f"Session id is ambiguous: {session_id}")
    _print_trigger_session_summary(sessions[0])


@trigger_sessions.command("diarize")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to diarize; unique prefixes are accepted",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option(
    "--segments-json",
    default=None,
    type=click.Path(exists=True),
    help="Import precomputed diarization segments instead of running a backend",
)
@click.option(
    "--window",
    "window_seconds",
    default=8.0,
    type=float,
    show_default=True,
    help="Seconds represented by one trigger-capture sample window",
)
@click.pass_context
def trigger_sessions_diarize(ctx, profile, session_id, samples_dir, segments_json, window_seconds):
    """Run or import diarization for one completed trigger-capture session."""
    from datetime import datetime

    from saymo.analysis.diarization import (
        DiarizationSessionSidecar,
        build_session_speaker_suggestions,
        diarization_result_from_json,
        run_pyannote_diarization,
        write_session_diarization,
    )

    base_dir = _samples_base_dir(samples_dir)
    resolved_session = _resolve_trigger_session_id(base_dir, profile, session_id)
    records = [
        record
        for record in _iter_trigger_sample_records(base_dir, profile=profile)
        if record.session_id == resolved_session
    ]
    if not records:
        raise click.ClickException(f"No samples found for session: {resolved_session}")

    created_at = datetime.now().isoformat(timespec="seconds")
    if segments_json:
        payload = json.loads(Path(segments_json).read_text(encoding="utf-8"))
        payload = {
            **payload,
            "profile": payload.get("profile") or profile,
            "session_id": payload.get("session_id") or resolved_session,
            "engine": payload.get("engine") or "import",
            "model": payload.get("model") or "segments-json",
            "created_at": payload.get("created_at") or created_at,
        }
        result = diarization_result_from_json(payload)
    else:
        audio_path = _write_session_mixdown(records)
        try:
            result = run_pyannote_diarization(
                audio_path=audio_path,
                config=ctx.obj["config"].diarization,
                profile=profile,
                session_id=resolved_session,
                created_at=created_at,
            )
        finally:
            try:
                audio_path.unlink()
            except OSError:
                pass

    suggestions = build_session_speaker_suggestions(
        records,
        result.segments,
        window_seconds=window_seconds,
    )
    sidecar = DiarizationSessionSidecar(
        profile=profile,
        session_id=resolved_session,
        engine=result.engine,
        model=result.model,
        created_at=result.created_at,
        segments=result.segments,
        speaker_mappings={},
        suggestions=suggestions,
    )
    path = write_session_diarization(base_dir, sidecar)
    console.print("diarization: saved")
    console.print(f"session: {resolved_session}")
    console.print(f"segments: {len(result.segments)}")
    console.print(f"suggestions: {len(suggestions)}")
    console.print(f"sidecar: {path}")


@trigger_sessions.command("speakers")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to summarize; unique prefixes are accepted",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
def trigger_sessions_speakers(profile, session_id, samples_dir):
    """Show diarization speaker clusters for one session."""
    from saymo.analysis.diarization import (
        load_session_diarization,
        session_diarization_path,
        speaker_cluster_summary,
    )

    base_dir = _samples_base_dir(samples_dir)
    resolved_session = _resolve_trigger_session_id(base_dir, profile, session_id)
    path = session_diarization_path(base_dir, profile, resolved_session)
    if not path.exists():
        raise click.ClickException(f"Diarization sidecar not found: {path}")
    sidecar = load_session_diarization(path)
    summary = speaker_cluster_summary(sidecar)
    unresolved = sum(
        1 for suggestion in sidecar.suggestions if suggestion.speaker_id not in sidecar.speaker_mappings
    )
    unknown_samples = sum(1 for suggestion in sidecar.suggestions if suggestion.current_speaker == "unknown")
    console.print(f"session: {resolved_session}")
    console.print(f"speaker clusters: {len(summary)}")
    console.print(f"unresolved suggestions: {unresolved}")
    console.print(f"unknown samples: {unknown_samples}")
    for speaker_id, cluster in summary.items():
        console.print(
            f"{speaker_id}: segments={cluster.segment_count} "
            f"samples={cluster.sample_count} "
            f"start={cluster.start_seconds:.2f}s "
            f"end={cluster.end_seconds:.2f}s "
            f"confidence={cluster.confidence:.2f} "
            f"label={cluster.mapped_label}"
        )


@trigger_sessions.command("map-speaker")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to update; unique prefixes are accepted",
)
@click.option("--speaker-id", required=True, help="Diarization speaker id to map")
@click.option("--label", required=True, type=click.Choice(_SPEAKER_LABELS), help="Saymo speaker label")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
def trigger_sessions_map_speaker(profile, session_id, speaker_id, label, samples_dir):
    """Map a diarization speaker id to me/other/unknown for one session."""
    from saymo.analysis.diarization import (
        apply_speaker_mapping,
        load_session_diarization,
        session_diarization_path,
        write_session_diarization,
    )

    base_dir = _samples_base_dir(samples_dir)
    resolved_session = _resolve_trigger_session_id(base_dir, profile, session_id)
    path = session_diarization_path(base_dir, profile, resolved_session)
    if not path.exists():
        raise click.ClickException(f"Diarization sidecar not found: {path}")
    sidecar = load_session_diarization(path)
    updated = apply_speaker_mapping(sidecar, speaker_id, label)
    write_session_diarization(base_dir, updated)
    console.print(f"session: {resolved_session}")
    console.print(f"mapping: {speaker_id} -> {label}")
    console.print(f"sidecar: {path}")


@trigger_sessions.command("speaker-report")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to report; unique prefixes are accepted",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option("--output", "-o", default=None, type=click.Path(), help="Markdown output path")
def trigger_sessions_speaker_report(profile, session_id, samples_dir, output):
    """Export a sanitized speaker-suggestion quality report."""
    from saymo.analysis.diarization import (
        build_speaker_quality_report,
        load_session_diarization,
        render_speaker_quality_report,
        session_diarization_path,
    )

    base_dir = _samples_base_dir(samples_dir)
    resolved_session = _resolve_trigger_session_id(base_dir, profile, session_id)
    path = session_diarization_path(base_dir, profile, resolved_session)
    if not path.exists():
        raise click.ClickException(f"Diarization sidecar not found: {path}")
    sidecar = load_session_diarization(path)
    records = [
        record
        for record in _iter_trigger_sample_records(base_dir, profile=profile)
        if record.session_id == resolved_session
    ]
    sample_speakers = {str(record.path): record.speaker for record in records}
    report = build_speaker_quality_report(sidecar, sample_speakers=sample_speakers)
    rendered = render_speaker_quality_report(report)
    if output:
        out_path = Path(output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        console.print(f"speaker report: {out_path}")
    else:
        console.print(rendered)


@main.group("meeting-memory")
def meeting_memory():
    """Build and inspect local full-session meeting memory."""


@meeting_memory.command("build")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to build; unique prefixes are accepted",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.option(
    "--window",
    "window_seconds",
    default=None,
    type=float,
    help="Seconds represented by one trigger-capture sample window",
)
@click.option(
    "--retain/--no-retain",
    "retain_transcripts",
    default=None,
    help="Whether to store transcript text in the local ledger",
)
@click.pass_context
def meeting_memory_build(ctx, profile, session_id, samples_dir, window_seconds, retain_transcripts):
    """Build a local transcript ledger for one captured meeting session."""
    ledger, path, base_dir = _build_meeting_memory_ledger(
        ctx,
        profile=profile,
        session_id=session_id,
        samples_dir=samples_dir,
        window_seconds=window_seconds,
        retain_transcripts=retain_transcripts,
    )
    console.print("meeting memory: saved")
    console.print(f"profile: {profile}")
    console.print(f"session: {ledger.session_id}")
    console.print(f"segments: {len(ledger.segments)}")
    console.print(f"incomplete: {ledger.incomplete_segments}")
    console.print(f"retain transcripts: {'yes' if ledger.retain_transcripts else 'no'}")
    console.print(f"base dir: {base_dir}")
    console.print(f"ledger: {path}")


@main.command("meeting-summary")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--session",
    "session_id",
    required=True,
    help="Session id to summarize; unique prefixes are accepted",
)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.option("--build-missing", is_flag=True, help="Build the transcript ledger if it is missing")
@click.option("--output", "-o", default=None, type=click.Path(), help="Markdown output path")
@click.option("--sanitized", is_flag=True, help="Export sanitized summary output")
@click.pass_context
def meeting_summary(ctx, profile, session_id, samples_dir, build_missing, output, sanitized):
    """Show a concise local full-session meeting summary."""
    from saymo.analysis.meeting_memory import (
        load_meeting_ledger,
        meeting_memory_base_dir,
        meeting_transcript_path,
        render_meeting_summary,
        render_sanitized_meeting_export,
        summarize_meeting_ledger,
    )

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    resolved_session = _resolve_trigger_session_id(base_dir, profile, session_id)
    path = meeting_transcript_path(base_dir, profile, resolved_session)
    if not path.exists():
        if not build_missing:
            raise click.ClickException(f"Meeting memory ledger not found: {path}")
        ledger, path, _ = _build_meeting_memory_ledger(
            ctx,
            profile=profile,
            session_id=resolved_session,
            samples_dir=samples_dir,
            window_seconds=None,
            retain_transcripts=None,
        )
    else:
        ledger = load_meeting_ledger(path)
    max_items = int(getattr(ctx.obj["config"].meeting_memory, "summary_max_items", 5) or 5)
    if sanitized:
        rendered = render_sanitized_meeting_export(ledger)
    else:
        rendered = render_meeting_summary(
            summarize_meeting_ledger(ledger, max_items=max_items),
            include_text=ledger.retain_transcripts,
        )
    if output:
        out_path = Path(output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        console.print(f"meeting summary: {out_path}")
    else:
        console.print(rendered)


@main.command("meeting-search")
@click.option("--profile", "-p", default=None, help="Profile to search")
@click.option("--session", "session_id", default=None, help="Session id/prefix to search")
@click.option("--keyword", "-k", default=None, help="Keyword or phrase to search")
@click.option("--speaker", default=None, type=click.Choice(_SPEAKER_LABELS), help="Speaker label filter")
@click.option("--category", default=None, help="Trigger category filter")
@click.option("--date-from", default=None, help="Minimum segment created_at value")
@click.option("--date-to", default=None, help="Maximum segment created_at value")
@click.option("--limit", default=20, type=click.IntRange(min=1), show_default=True)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def meeting_search(ctx, profile, session_id, keyword, speaker, category, date_from, date_to, limit, samples_dir):
    """Search local meeting-memory transcript ledgers."""
    from saymo.analysis.meeting_memory import (
        MeetingSearchFilters,
        meeting_memory_base_dir,
        render_meeting_search_results,
        search_meeting_memory,
    )

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    filters = MeetingSearchFilters(
        profile=profile,
        session_id=session_id,
        date_from=date_from,
        date_to=date_to,
        speaker=speaker,
        category=category,
        keyword=keyword,
    )
    results = search_meeting_memory(base_dir, filters, limit=limit)
    console.print(f"matches: {len(results)}")
    rendered = render_meeting_search_results(results)
    if rendered:
        console.print(rendered)


@main.command("meeting-ask")
@click.argument("question")
@click.option("--profile", "-p", default=None, help="Profile to search")
@click.option("--session", "session_id", default=None, help="Session id/prefix to search")
@click.option("--speaker", default=None, type=click.Choice(_SPEAKER_LABELS), help="Speaker label filter")
@click.option("--category", default=None, help="Trigger category filter")
@click.option("--date-from", default=None, help="Minimum segment created_at value")
@click.option("--date-to", default=None, help="Maximum segment created_at value")
@click.option("--max-citations", default=5, type=click.IntRange(min=1), show_default=True)
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def meeting_ask(ctx, question, profile, session_id, speaker, category, date_from, date_to, max_citations, samples_dir):
    """Ask a question about local meeting-memory transcripts."""
    from saymo.analysis.meeting_memory import (
        MeetingSearchFilters,
        answer_meeting_question,
        meeting_memory_base_dir,
        render_meeting_ask_answer,
    )

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    answer = answer_meeting_question(
        question,
        base_dir=base_dir,
        filters=MeetingSearchFilters(
            profile=profile,
            session_id=session_id,
            date_from=date_from,
            date_to=date_to,
            speaker=speaker,
            category=category,
        ),
        max_citations=max_citations,
    )
    console.print(render_meeting_ask_answer(answer))


@main.command("answer-draft")
@click.argument("question")
@click.option("--profile", "-p", default="personal", help="Meeting profile")
@click.option("--session", "session_id", default=None, help="Session id/prefix to ground from")
@click.option("--source", "sources", multiple=True, help="Source plugin name; repeat for multiple")
@click.option("--compose", is_flag=True, help="Use local Ollama composer instead of deterministic draft text")
@click.option("--strict-compose", is_flag=True, help="Fail if --compose cannot use Ollama")
@click.option("--output", "-o", default=None, type=click.Path(), help="Write draft JSON to this path")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def answer_draft(ctx, question, profile, session_id, sources, compose, strict_compose, output, samples_dir):
    """Generate a reviewable source-grounded answer draft."""
    run_async(
        _answer_draft_async(
            ctx,
            question=question,
            profile=profile,
            session_id=session_id,
            sources=sources,
            compose=compose,
            strict_compose=strict_compose,
            output=output,
            samples_dir=samples_dir,
        )
    )


async def _answer_draft_async(
    ctx,
    *,
    question: str,
    profile: str,
    session_id: str | None,
    sources: tuple[str, ...],
    compose: bool,
    strict_compose: bool,
    output: str | None,
    samples_dir: str | None,
) -> None:
    from saymo.analysis.addressing import (
        classify_addressing,
        expand_trigger_phrases,
        should_answer_decision,
    )
    from saymo.analysis.answer_cockpit import (
        build_answer_draft,
        build_trigger_evidence,
        render_answer_draft,
        source_evidence_error,
        write_answer_draft,
    )
    from saymo.analysis.meeting_memory import (
        MeetingSearchFilters,
        answer_meeting_question,
        meeting_memory_base_dir,
    )
    from saymo.analysis.turn_detector import TurnDetector

    config = ctx.obj["config"]
    base_dir = meeting_memory_base_dir(config, samples_dir)
    meeting_answer = answer_meeting_question(
        question,
        base_dir=base_dir,
        filters=MeetingSearchFilters(profile=profile, session_id=session_id),
    )
    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    fuzzy = (config.vocabulary or {}).get("fuzzy_expansions") or {}
    detector = TurnDetector(
        name_variants=trigger_phrases,
        cooldown_seconds=0,
        fuzzy_expansions=fuzzy,
    )
    expanded = expand_trigger_phrases(trigger_phrases, fuzzy)
    decision = classify_addressing(question, expanded)
    triggered = detector.check(question) if question else False
    will_answer = bool(triggered and should_answer_decision(decision))
    trigger_evidence = build_trigger_evidence(
        transcript=question,
        profile=profile,
        session_id=session_id or "",
        trigger=triggered,
        question=True,
        will_answer=will_answer,
        addressing=decision.label,
        reason=decision.reason,
    )
    source_evidence = await _fetch_answer_source_evidence(
        config,
        _answer_source_names(config, profile, sources),
    )
    composer_text = None
    composer = "deterministic"
    if compose:
        try:
            from saymo.speech.ollama_composer import answer_question as compose_answer

            standup_summary = meeting_answer.answer
            jira_context = "\n".join(
                source.summary for source in source_evidence if source.status == "available"
            )
            composer_text = await compose_answer(
                question,
                standup_summary=standup_summary,
                jira_context=jira_context,
                user_name=config.user.name,
                user_role=config.user.role,
                model=config.ollama.model,
                ollama_url=config.ollama.url,
                config=config,
            )
            composer = "ollama"
        except Exception as e:
            if strict_compose:
                raise click.ClickException(f"composer failed: {e}") from e
            source_evidence = (
                *source_evidence,
                source_evidence_error("ollama", e),
            )
            composer = "deterministic"
    draft = build_answer_draft(
        profile=profile,
        session_id=session_id or "",
        question=question,
        trigger_evidence=trigger_evidence,
        meeting_answer=meeting_answer,
        sources=source_evidence,
        composer_text=composer_text,
        composer=composer,
    )
    if output:
        path = write_answer_draft(Path(output), draft)
        console.print(f"draft json: {path}")
    console.print(render_answer_draft(draft))


def _answer_source_names(config, profile: str, sources: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = tuple(name.strip() for name in sources if name and name.strip())
    if cleaned:
        return tuple(name for name in cleaned if name.lower() != "none")
    meeting = config.get_meeting(profile)
    if meeting and meeting.source:
        return (meeting.source,)
    source = getattr(config.speech, "source", "")
    return (source,) if source else ()


async def _fetch_answer_source_evidence(config, source_names: tuple[str, ...]):
    from saymo.analysis.answer_cockpit import (
        source_evidence_error,
        source_evidence_from_payload,
    )
    from saymo.plugins.base import get_plugin

    evidence = []
    for source_name in source_names:
        try:
            plugin = get_plugin(source_name)
            payload = await plugin.fetch(config)
        except Exception as e:
            evidence.append(source_evidence_error(source_name, e))
            continue
        evidence.append(source_evidence_from_payload(source_name, payload))
    return tuple(evidence)


@main.group("answer-cockpit")
def answer_cockpit():
    """Review answer drafts and choose explicit live-call actions."""


@answer_cockpit.command("show")
@click.option("--draft-json", required=True, type=click.Path(exists=True), help="Answer draft JSON from answer-draft")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def answer_cockpit_show(ctx, draft_json, samples_dir):
    """Show current answer cockpit state for a draft."""
    from saymo.analysis.answer_cockpit import (
        append_audit_event,
        build_cockpit_state,
        draft_created_event,
        load_answer_draft,
        render_cockpit_state,
        write_cockpit_state,
    )
    from saymo.analysis.meeting_memory import meeting_memory_base_dir

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    draft = load_answer_draft(Path(draft_json))
    state = build_cockpit_state(draft)
    state_path = write_cockpit_state(base_dir, state)
    audit_path = append_audit_event(base_dir, draft_created_event(draft))
    console.print(f"cockpit state: {state_path}")
    console.print(f"audit: {audit_path}")
    console.print(render_cockpit_state(state))


@answer_cockpit.command("action")
@click.option("--profile", "-p", required=True, help="Meeting profile")
@click.option("--session", "session_id", required=True, help="Session id")
@click.option(
    "--action",
    "action_name",
    required=True,
    type=click.Choice(["speak", "edit", "skip", "takeover"]),
    help="Explicit cockpit action",
)
@click.option("--text", "edited_text", default=None, help="Edited answer text for --action edit")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def answer_cockpit_action(ctx, profile, session_id, action_name, edited_text, samples_dir):
    """Apply one explicit cockpit action to the current draft."""
    from saymo.analysis.answer_cockpit import (
        append_audit_event,
        apply_cockpit_action,
        cockpit_state_path,
        load_cockpit_state,
        render_cockpit_state,
        write_cockpit_state,
    )
    from saymo.analysis.meeting_memory import meeting_memory_base_dir

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    path = cockpit_state_path(base_dir, profile, session_id)
    if not path.exists():
        raise click.ClickException(f"Cockpit state not found: {path}")
    state = load_cockpit_state(path)
    try:
        updated, event = apply_cockpit_action(
            state,
            action=action_name,
            edited_text=edited_text,
        )
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    state_path = write_cockpit_state(base_dir, updated)
    audit_path = append_audit_event(base_dir, event)
    console.print(f"action: {action_name}")
    console.print(f"state: {updated.state}")
    console.print(f"playback started: no")
    console.print(f"cockpit state: {state_path}")
    console.print(f"audit: {audit_path}")
    console.print(render_cockpit_state(updated))


@main.group("answer-audit")
def answer_audit():
    """Inspect local answer cockpit audit events."""


@answer_audit.command("list")
@click.option("--profile", "-p", required=True, help="Meeting profile")
@click.option("--session", "session_id", required=True, help="Session id")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def answer_audit_list(ctx, profile, session_id, samples_dir):
    """List local answer cockpit audit events."""
    from saymo.analysis.answer_cockpit import (
        answer_audit_path,
        load_audit_events,
        render_audit_events,
    )
    from saymo.analysis.meeting_memory import meeting_memory_base_dir

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    path = answer_audit_path(base_dir, profile, session_id)
    events = load_audit_events(path)
    console.print(f"audit: {path}")
    console.print(f"events: {len(events)}")
    rendered = render_audit_events(events)
    if rendered:
        console.print(rendered)


@answer_audit.command("report")
@click.option("--profile", "-p", required=True, help="Meeting profile")
@click.option("--session", "session_id", required=True, help="Session id")
@click.option("--output", "-o", default=None, type=click.Path(), help="Markdown output path")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to meeting_memory.base_dir or ~/.saymo/trigger_samples",
)
@click.pass_context
def answer_audit_report(ctx, profile, session_id, output, samples_dir):
    """Render sanitized answer cockpit audit report."""
    from saymo.analysis.answer_cockpit import (
        answer_audit_path,
        load_audit_events,
        render_sanitized_audit_report,
    )
    from saymo.analysis.meeting_memory import meeting_memory_base_dir

    base_dir = meeting_memory_base_dir(ctx.obj["config"], samples_dir)
    path = answer_audit_path(base_dir, profile, session_id)
    rendered = render_sanitized_audit_report(load_audit_events(path))
    if output:
        out_path = Path(output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        console.print(f"answer audit report: {out_path}")
    else:
        console.print(rendered)


def _build_meeting_memory_ledger(
    ctx,
    *,
    profile: str,
    session_id: str,
    samples_dir: str | None,
    window_seconds: float | None,
    retain_transcripts: bool | None,
):
    from saymo.analysis.meeting_memory import (
        build_meeting_ledger_from_samples,
        meeting_memory_base_dir,
        write_meeting_ledger,
    )
    from saymo.analysis.trigger_sessions import list_trigger_sessions

    config = ctx.obj["config"]
    memory_cfg = config.meeting_memory
    if not getattr(memory_cfg, "enabled", True):
        raise click.ClickException("meeting_memory.enabled=false")
    base_dir = meeting_memory_base_dir(config, samples_dir)
    resolved_session = _resolve_trigger_session_id(base_dir, profile, session_id)
    sessions = [
        session
        for session in list_trigger_sessions(base_dir, profile=profile)
        if session.session_id == resolved_session
    ]
    resolved_window = (
        float(window_seconds)
        if window_seconds is not None
        else float(getattr(memory_cfg, "default_window_seconds", 8.0) or 8.0)
    )
    retain = (
        bool(retain_transcripts)
        if retain_transcripts is not None
        else bool(getattr(memory_cfg, "retain_transcripts", True))
    )
    ledger = build_meeting_ledger_from_samples(
        base_dir=base_dir,
        profile=profile,
        session_id=resolved_session,
        session=sessions[0] if sessions else None,
        window_seconds=resolved_window,
        retain_transcripts=retain,
    )
    if not ledger.segments:
        raise click.ClickException(f"No transcript samples found for session: {resolved_session}")
    path = write_meeting_ledger(base_dir, ledger)
    return ledger, path, base_dir


@main.group("trigger-classifier")
def trigger_classifier():
    """Train, inspect, and delete the local trigger classifier."""


@trigger_classifier.command("train")
@click.option("--profile", "-p", default="personal", help="Profile to train")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option("--model-dir", default=None, type=click.Path(), help="Directory for classifier artifacts")
@click.option(
    "--min-total",
    default=4,
    type=click.IntRange(min=1),
    show_default=True,
    help="Minimum accepted/rejected labels",
)
@click.option(
    "--min-per-class",
    default=1,
    type=click.IntRange(min=1),
    show_default=True,
    help="Minimum labels for each class",
)
def trigger_classifier_train(profile, samples_dir, model_dir, min_total, min_per_class):
    """Train a local accepted/rejected classifier from labeled samples."""
    from saymo.analysis.trigger_classifier import (
        InsufficientTrainingData,
        classifier_model_path,
        save_model,
        train_classifier,
    )

    records = list(_iter_trigger_sample_records(_samples_base_dir(samples_dir), profile))
    samples = [_classifier_sample_from_record(record) for record in records]
    try:
        model = train_classifier(
            samples,
            profile=profile,
            min_total=min_total,
            min_per_class=min_per_class,
        )
    except InsufficientTrainingData as e:
        raise click.ClickException(str(e)) from e

    model_path = save_model(model, classifier_model_path(profile, model_dir))
    console.print(f"samples: {len(records)}")
    console.print(
        "labeled: "
        f"accepted={model.label_counts.get('accepted', 0)} "
        f"rejected={model.label_counts.get('rejected', 0)}"
    )
    console.print("trained: yes")
    console.print(f"model: {model_path}")


@trigger_classifier.command("inspect")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with classifier artifacts")
def trigger_classifier_inspect(profile, model_dir):
    """Inspect the local classifier artifact for a profile."""
    from saymo.analysis.trigger_classifier import classifier_model_path, load_model

    model_path = classifier_model_path(profile, model_dir)
    if not model_path.exists():
        raise click.ClickException(f"Classifier artifact not found: {model_path}")
    model = load_model(model_path)
    console.print(f"profile: {model.profile}")
    console.print(f"model: {model_path}")
    console.print(f"trained_at: {model.trained_at}")
    console.print(f"version: {model.version}")
    console.print(f"accepted: {model.label_counts.get('accepted', 0)}")
    console.print(f"rejected: {model.label_counts.get('rejected', 0)}")
    console.print(f"vocabulary: {len(model.vocabulary)}")
    console.print(f"thresholds: min_total={model.min_total} min_per_class={model.min_per_class}")


@trigger_classifier.command("readiness")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option("--min-total", default=8, show_default=True, type=click.IntRange(min=1))
@click.option("--min-per-class", default=2, show_default=True, type=click.IntRange(min=1))
def trigger_classifier_readiness(profile, samples_dir, min_total, min_per_class):
    """Check whether local labels are ready for classifier live assist."""
    from saymo.analysis.trigger_readiness import TriggerReadinessThresholds, readiness_metrics

    records = list(_iter_trigger_sample_records(_samples_base_dir(samples_dir), profile))
    report = readiness_metrics(
        records,
        TriggerReadinessThresholds(
            min_labeled=min_total,
            min_accepted=min_per_class,
            min_rejected=min_per_class,
        ),
    )
    _print_readiness_report(report)


@trigger_classifier.command("evaluate")
@click.option("--profile", "-p", default="personal", help="Profile to evaluate")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option("--min-total", default=4, show_default=True, type=click.IntRange(min=1))
@click.option("--min-per-class", default=1, show_default=True, type=click.IntRange(min=1))
@click.option(
    "--holdout-ratio",
    default=0.4,
    show_default=True,
    type=click.FloatRange(min=0.0, max=1.0, min_open=True, max_open=True),
)
def trigger_classifier_evaluate(profile, samples_dir, min_total, min_per_class, holdout_ratio):
    """Run deterministic local holdout evaluation for the trigger classifier."""
    from saymo.analysis.trigger_classifier import InsufficientTrainingData
    from saymo.analysis.trigger_readiness import evaluate_holdout

    records = list(_iter_trigger_sample_records(_samples_base_dir(samples_dir), profile))
    try:
        result = evaluate_holdout(
            [_classifier_sample_from_record(record) for record in records],
            profile=profile,
            min_total=min_total,
            min_per_class=min_per_class,
            holdout_fraction=holdout_ratio,
        )
    except (InsufficientTrainingData, ValueError) as e:
        raise click.ClickException(str(e)) from e
    _print_holdout_report(result)


@trigger_classifier.group("live-assist")
def trigger_classifier_live_assist():
    """Manage guarded classifier live assist for a profile."""


@trigger_classifier_live_assist.command("status")
@click.option("--profile", "-p", default="personal", help="Profile to inspect")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with classifier artifacts")
def trigger_classifier_live_assist_status(profile, model_dir):
    """Show live-assist status for a profile."""
    from saymo.analysis.trigger_readiness import live_assist_status

    status = live_assist_status(profile, model_dir)
    _print_live_assist_status(status)


@trigger_classifier_live_assist.command("enable")
@click.option("--profile", "-p", default="personal", help="Profile to enable")
@click.option(
    "--samples-dir",
    default=None,
    type=click.Path(),
    help="Directory with trigger samples; defaults to ~/.saymo/trigger_samples",
)
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with classifier artifacts")
@click.option("--min-total", default=8, show_default=True, type=click.IntRange(min=1))
@click.option("--min-per-class", default=2, show_default=True, type=click.IntRange(min=1))
def trigger_classifier_live_assist_enable(profile, samples_dir, model_dir, min_total, min_per_class):
    """Enable live assist only when readiness gates pass."""
    from saymo.analysis.trigger_readiness import (
        TriggerReadinessThresholds,
        enable_live_assist,
        live_assist_status,
        readiness_metrics,
    )

    records = list(_iter_trigger_sample_records(_samples_base_dir(samples_dir), profile))
    readiness = readiness_metrics(
        records,
        TriggerReadinessThresholds(
            min_labeled=min_total,
            min_accepted=min_per_class,
            min_rejected=min_per_class,
        ),
    )
    if not readiness.passed:
        _print_readiness_report(readiness)
        raise click.ClickException("readiness failed; live assist not enabled")
    try:
        enable_live_assist(profile, model_dir, readiness)
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e
    _print_live_assist_status(live_assist_status(profile, model_dir))


@trigger_classifier_live_assist.command("disable")
@click.option("--profile", "-p", default="personal", help="Profile to disable")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with classifier artifacts")
def trigger_classifier_live_assist_disable(profile, model_dir):
    """Disable classifier live assist for a profile."""
    from saymo.analysis.trigger_readiness import disable_live_assist, live_assist_status

    disable_live_assist(profile, model_dir)
    _print_live_assist_status(live_assist_status(profile, model_dir))


@trigger_classifier.command("delete")
@click.option("--profile", "-p", default="personal", help="Profile artifact to delete")
@click.option("--model-dir", default=None, type=click.Path(), help="Directory with classifier artifacts")
@click.option("--yes", is_flag=True, help="Delete without confirmation")
def trigger_classifier_delete(profile, model_dir, yes):
    """Delete the local classifier artifact for a profile."""
    from saymo.analysis.trigger_classifier import classifier_model_path

    model_path = classifier_model_path(profile, model_dir)
    if not model_path.exists():
        console.print(f"model: {model_path}")
        console.print("deleted: no")
        return
    if not yes and not click.confirm(f"Delete {model_path}?"):
        console.print("deleted: no")
        return
    model_path.unlink()
    console.print(f"model: {model_path}")
    console.print("deleted: yes")


def _samples_base_dir(samples_dir: str | None) -> Path:
    return Path(samples_dir).expanduser() if samples_dir else Path.home() / ".saymo" / "trigger_samples"


def _samples_base_dir_for_record(
    record: TriggerSampleRecord,
    samples_dir: str | None,
) -> Path:
    if samples_dir:
        return _samples_base_dir(samples_dir)
    try:
        return record.path.parents[2]
    except IndexError:
        return _samples_base_dir(None)


def _load_record_speaker_suggestion(
    record: TriggerSampleRecord,
    samples_dir: str | None,
    *,
    require: bool = False,
):
    from saymo.analysis.diarization import (
        find_sample_speaker_suggestion,
        load_session_diarization,
        session_diarization_path,
    )

    if not record.session_id:
        if require:
            raise click.ClickException("Sample has no session_id")
        return None
    base_dir = _samples_base_dir_for_record(record, samples_dir)
    sidecar_path = session_diarization_path(base_dir, record.profile, record.session_id)
    if not sidecar_path.exists():
        if require:
            raise click.ClickException(f"Diarization sidecar not found: {sidecar_path}")
        return None
    sidecar = load_session_diarization(sidecar_path)
    suggestion = find_sample_speaker_suggestion(
        sidecar,
        record.path,
        session_sequence=record.session_sequence,
    )
    if suggestion is None and require:
        raise click.ClickException(f"Speaker suggestion not found for sample: {record.path}")
    return base_dir, sidecar_path, sidecar, suggestion


def _print_record_speaker_suggestion(
    record: TriggerSampleRecord,
    samples_dir: str | None,
) -> None:
    loaded = _load_record_speaker_suggestion(record, samples_dir)
    if loaded is None:
        return
    _, _, _, suggestion = loaded
    if suggestion is not None:
        _print_speaker_suggestion(record, suggestion)


def _print_speaker_suggestion(record: TriggerSampleRecord, suggestion) -> None:
    console.print(
        f"suggestion: speaker_id={suggestion.speaker_id} "
        f"suggested={suggestion.suggested_speaker} "
        f"status={suggestion.status} "
        f"confidence={suggestion.confidence:.2f} "
        f"reviewed={suggestion.reviewed_speaker}"
    )
    console.print(f"sample speaker: {record.speaker}")


def _apply_record_speaker_suggestion_review(
    record: TriggerSampleRecord,
    samples_dir: str | None,
    *,
    action: str,
    label: str | None,
) -> TriggerSampleRecord:
    from datetime import datetime, timezone

    from saymo.analysis.diarization import (
        review_speaker_suggestion,
        write_session_diarization,
    )

    loaded = _load_record_speaker_suggestion(record, samples_dir, require=True)
    if loaded is None:
        raise click.ClickException("Speaker suggestion not found")
    base_dir, _, sidecar, _ = loaded
    try:
        updated, reviewed = review_speaker_suggestion(
            sidecar,
            sample_path=record.path,
            action=action,
            label=label,
            session_sequence=record.session_sequence,
            reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    write_session_diarization(base_dir, updated)
    console.print(f"review: {reviewed.status}")
    if reviewed.status in {"accepted", "overridden"}:
        previous = _write_trigger_sample_speaker(record.path, reviewed.reviewed_speaker)
        console.print(f"speaker: {previous} -> {reviewed.reviewed_speaker}")
        return _load_trigger_sample(record.path)
    console.print("speaker: unchanged")
    return record


def _resolve_trigger_session_id(base_dir: Path, profile: str, session_id: str) -> str:
    from saymo.analysis.trigger_sessions import list_trigger_sessions

    sessions = [
        session
        for session in list_trigger_sessions(base_dir, profile=profile)
        if session.session_id == session_id or session.session_id.startswith(session_id)
    ]
    if len(sessions) == 1:
        return sessions[0].session_id
    if len(sessions) > 1:
        raise click.ClickException(f"Session id is ambiguous: {session_id}")

    sample_ids = sorted(
        {
            record.session_id
            for record in _iter_trigger_sample_records(base_dir, profile=profile)
            if record.session_id
            and (record.session_id == session_id or record.session_id.startswith(session_id))
        }
    )
    if len(sample_ids) == 1:
        return sample_ids[0]
    if len(sample_ids) > 1:
        raise click.ClickException(f"Session id is ambiguous: {session_id}")
    raise click.ClickException(f"Session not found: {session_id}")


def _write_session_mixdown(records: list[TriggerSampleRecord]) -> Path:
    import tempfile

    import numpy as np
    import soundfile as sf

    chunks = []
    sample_rate = 16000
    for record in sorted(records, key=lambda item: item.session_sequence):
        wav_path = record.path.with_name(record.wav)
        if not wav_path.exists():
            continue
        audio, rate = sf.read(str(wav_path), dtype="float32")
        sample_rate = int(rate)
        chunks.append(np.asarray(audio, dtype=np.float32).reshape(-1))
    if not chunks:
        raise click.ClickException("No session WAV files found for diarization")
    audio = np.concatenate(chunks)
    handle = tempfile.NamedTemporaryFile(prefix="saymo-diarization-", suffix=".wav", delete=False)
    path = Path(handle.name)
    handle.close()
    sf.write(str(path), audio, sample_rate, subtype="PCM_16")
    return path


def _filter_review_rows_or_fail(records, filters):
    from saymo.analysis.trigger_review import filter_review_rows

    try:
        return filter_review_rows(records, filters)
    except ValueError as e:
        raise click.ClickException(str(e)) from e


def _load_trigger_sample(path: Path) -> TriggerSampleRecord:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    p = Path(path)
    return TriggerSampleRecord(
        path=p,
        profile=str(data.get("profile") or _profile_from_sample_path(p)),
        category=str(data.get("category") or p.parent.name),
        session_id=str(data.get("session_id") or ""),
        session_name=str(data.get("session_name") or ""),
        session_sequence=int(data.get("session_sequence") or 0),
        speaker=_normalize_speaker_label(data.get("speaker")),
        answer_decision=_normalize_answer_decision(data.get("answer_decision")),
        created_at=str(data.get("created_at") or ""),
        transcript=str(data.get("transcript") or ""),
        trigger=bool(data.get("trigger")),
        question=bool(data.get("question")),
        will_answer=bool(data.get("will_answer")),
        addressing=str(data.get("addressing") or ""),
        reason=str(data.get("reason") or ""),
        rms=float(data.get("rms") or 0.0),
        peak=float(data.get("peak") or 0.0),
        wav=str(data.get("wav") or p.with_suffix(".wav").name),
    )


def _profile_from_sample_path(path: Path) -> str:
    try:
        return path.parents[1].name
    except IndexError:
        return ""


def _iter_trigger_sample_records(
    base_dir: Path,
    profile: str | None = None,
    category: str | None = None,
) -> list[TriggerSampleRecord]:
    root = Path(base_dir).expanduser()
    if profile and category:
        pattern_root = root / profile / category
        paths = sorted(pattern_root.glob("*.json"))
    elif profile:
        paths = sorted((root / profile).glob("*/*.json"))
    else:
        paths = sorted(root.glob("*/*/*.json"))

    records: list[TriggerSampleRecord] = []
    for path in paths:
        if path.parent.name == SESSION_LEDGER_DIR:
            continue
        try:
            records.append(_load_trigger_sample(path))
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            console.print(f"[yellow]skip invalid sample {path}: {e}[/]")
    return records


def _write_trigger_sample_speaker(path: Path, speaker: str) -> str:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Cannot read sample metadata: {e}") from e
    if not isinstance(data, dict):
        raise click.ClickException(f"Sample metadata is not an object: {path}")

    previous = _normalize_speaker_label(data.get("speaker"))
    data["speaker"] = speaker
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return previous


def _write_trigger_sample_decision(path: Path, decision: str) -> str:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Cannot read sample metadata: {e}") from e
    if not isinstance(data, dict):
        raise click.ClickException(f"Sample metadata is not an object: {path}")

    previous = _normalize_answer_decision(data.get("answer_decision"))
    data["answer_decision"] = decision
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return previous


def _current_trigger_category(text: str, will_answer: bool, is_question: bool) -> str:
    if will_answer:
        return "asked_to_speak"
    if is_question:
        return "question"
    if " ".join((text or "").split()):
        return "speech"
    return "silence"


def _classifier_sample_from_record(record: TriggerSampleRecord):
    from saymo.analysis.trigger_classifier import TriggerClassifierSample

    return TriggerClassifierSample(
        transcript=record.transcript,
        speaker=record.speaker,
        category=record.category,
        trigger=record.trigger,
        question=record.question,
        will_answer=record.will_answer,
        addressing=record.addressing,
        decision=record.answer_decision,
    )


def _classifier_sample_from_row(row: TriggerEvaluationRow):
    from saymo.analysis.trigger_classifier import TriggerClassifierSample

    return TriggerClassifierSample(
        transcript=row.record.transcript,
        speaker=row.record.speaker,
        category=row.current_category,
        trigger=row.current_trigger,
        question=row.current_question,
        will_answer=row.current_will_answer,
        addressing=row.current_addressing,
        decision=row.record.answer_decision,
    )


def _print_trigger_check_classifier_shadow(
    *,
    profile: str,
    text: str,
    speaker: str,
    category: str,
    trigger: bool,
    question: bool,
    will_answer: bool,
    addressing: str,
    model_dir: str | None,
) -> None:
    from saymo.analysis.trigger_classifier import (
        TriggerClassifierSample,
        classifier_model_path,
        load_model,
        predict,
    )

    model_path = classifier_model_path(profile, model_dir)
    if not model_path.exists():
        console.print(f"classifier: not trained ({model_path})")
        return
    model = load_model(model_path)
    prediction = predict(
        model,
        TriggerClassifierSample(
            transcript=text,
            speaker=speaker,
            category=category,
            trigger=trigger,
            question=question,
            will_answer=will_answer,
            addressing=addressing,
            decision="unlabeled",
        ),
    )
    console.print(
        f"classifier: {prediction.label} "
        f"confidence={prediction.confidence:.2f} "
        f"model={model_path}"
    )


def _print_trigger_check_live_assist(
    *,
    profile: str,
    text: str,
    speaker: str,
    category: str,
    trigger: bool,
    question: bool,
    will_answer: bool,
    addressing: str,
    model_dir: str | None,
) -> None:
    from saymo.analysis.trigger_classifier import (
        TriggerClassifierSample,
        classifier_model_path,
        load_model,
        predict_live_assist,
    )
    from saymo.analysis.trigger_readiness import (
        apply_live_assist_decision,
        live_assist_status,
    )

    status = live_assist_status(profile, model_dir)
    model_path = classifier_model_path(profile, model_dir)
    console.print(f"live assist: {'enabled' if status.enabled else 'disabled'}")
    if status.reason:
        console.print(f"live assist status: {status.reason}")
    if not status.enabled:
        console.print(f"live assist action: {'answer' if will_answer else 'skip'}")
        return
    model = load_model(model_path)
    sample = TriggerClassifierSample(
        transcript=text,
        speaker=speaker,
        decision="unlabeled",
    )
    prediction = predict_live_assist(model, sample)
    decision = apply_live_assist_decision(
        deterministic_will_answer=will_answer,
        classifier_prediction=prediction,
    )
    console.print(
        f"live assist classifier: {prediction.label} "
        f"confidence={prediction.confidence:.2f} model={model_path}"
    )
    console.print(f"live assist action: {decision.final_action}")
    console.print(f"live assist reason: {decision.reason}")


def _print_classifier_shadow_evaluation(
    rows: list[TriggerEvaluationRow],
    *,
    profile: str,
    model_dir: str | None,
) -> None:
    from saymo.analysis.trigger_classifier import classifier_model_path, load_model, predict

    model_path = classifier_model_path(profile, model_dir)
    if not model_path.exists():
        console.print(f"classifier shadow: not trained ({model_path})")
        return
    model = load_model(model_path)
    counts = {"accepted": 0, "rejected": 0}
    disagreements: list[tuple[TriggerEvaluationRow, str, object]] = []
    for row in rows:
        prediction = predict(model, _classifier_sample_from_row(row))
        counts[prediction.label] = counts.get(prediction.label, 0) + 1
        deterministic = "accepted" if row.current_will_answer else "rejected"
        if prediction.label != deterministic:
            disagreements.append((row, deterministic, prediction))

    console.print("classifier shadow: model=loaded")
    console.print(f"classifier model: {model_path}")
    console.print(f"classifier accepted: {counts.get('accepted', 0)}")
    console.print(f"classifier rejected: {counts.get('rejected', 0)}")
    console.print(f"classifier disagreements: {len(disagreements)}")
    for row, deterministic, prediction in disagreements[:10]:
        console.print(
            f"  classifier disagreement: {row.record.path} "
            f"deterministic={deterministic} "
            f"classifier={prediction.label} "
            f"conf={prediction.confidence:.2f}"
        )


def _filter_classifier_disagreements(
    rows: list[TriggerEvaluationRow],
    *,
    profile: str,
    model_dir: str | None,
) -> list[TriggerEvaluationRow]:
    from saymo.analysis.trigger_classifier import classifier_model_path, load_model, predict

    model_path = classifier_model_path(profile, model_dir)
    if not model_path.exists():
        raise click.ClickException(f"Classifier artifact not found: {model_path}")
    model = load_model(model_path)
    disagreements: list[TriggerEvaluationRow] = []
    for row in rows:
        prediction = predict(model, _classifier_sample_from_row(row))
        deterministic = "accepted" if row.current_will_answer else "rejected"
        if prediction.label != deterministic:
            disagreements.append(row)
    return disagreements


def _print_readiness_report(report) -> None:
    console.print(f"readiness: {'ready' if report.passed else 'not_ready'}")
    console.print(f"samples: {report.total_samples}")
    console.print(f"labeled: {report.total_labeled}")
    console.print(f"accepted: {report.accepted}")
    console.print(f"rejected: {report.rejected}")
    console.print(f"categories: {', '.join(report.category_counts) or '(none)'}")
    console.print(f"mention coverage: {'yes' if report.has_mentioned_me else 'no'}")
    console.print(f"handoff coverage: {'yes' if report.has_asked_to_speak else 'no'}")
    if report.missing_items:
        console.print("missing:")
        for item in report.missing_items:
            console.print(f"  - {item}")


def _print_holdout_report(result) -> None:
    console.print(f"holdout samples: {result.holdout_count}")
    console.print(f"train samples: {result.train_count}")
    console.print(f"accuracy: {_format_metric(result.accuracy)}")
    console.print(f"accepted precision: {_format_metric(result.precision.get('accepted'))}")
    console.print(f"accepted recall: {_format_metric(result.recall.get('accepted'))}")
    console.print(f"rejected precision: {_format_metric(result.precision.get('rejected'))}")
    console.print(f"rejected recall: {_format_metric(result.recall.get('rejected'))}")
    true_accept = result.confusion_matrix["accepted"]["accepted"]
    false_accept = result.confusion_matrix["rejected"]["accepted"]
    true_reject = result.confusion_matrix["rejected"]["rejected"]
    false_reject = result.confusion_matrix["accepted"]["rejected"]
    console.print(
        "confusion: "
        f"tp={true_accept} fp={false_accept} "
        f"tn={true_reject} fn={false_reject}"
    )


def _print_live_assist_status(status) -> None:
    profile = status.artifact.profile if status.artifact else status.path.stem.replace(".live_assist", "")
    console.print(f"profile: {profile}")
    console.print(f"live assist: {'enabled' if status.enabled else 'disabled'}")
    if status.reason:
        console.print(f"status: {status.reason}")
    console.print(f"updated_at: {status.artifact.updated_at if status.artifact else '-'}")
    if status.artifact and status.artifact.model_sha256:
        console.print(f"model_sha256: {status.artifact.model_sha256[:12]}")
    if status.path:
        console.print(f"artifact: {status.path}")


def _format_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _evaluate_trigger_records(
    config,
    profile: str,
    records: list[TriggerSampleRecord],
) -> list[TriggerEvaluationRow]:
    from saymo.analysis.trigger_capture import classify_trigger_sample

    trigger_phrases = _trigger_phrases_for_profile(config, profile)
    fuzzy = (config.vocabulary or {}).get("fuzzy_expansions") or {}
    rows: list[TriggerEvaluationRow] = []
    for record in records:
        current = classify_trigger_sample(
            record.transcript,
            trigger_phrases,
            fuzzy,
            rms=record.rms,
            peak=record.peak,
        )
        miss = record.category == "asked_to_speak" and not current.will_answer
        false_positive = record.category != "asked_to_speak" and current.will_answer
        rows.append(
            TriggerEvaluationRow(
                record=record,
                current_category=current.category,
                current_trigger=current.trigger,
                current_question=current.question,
                current_will_answer=current.will_answer,
                current_addressing=current.addressing,
                miss=miss,
                false_positive=false_positive,
            )
        )
    return rows


def _print_trigger_evaluation(rows: list[TriggerEvaluationRow]) -> None:
    stored_counts = _count_by_category([row.record.category for row in rows])
    current_counts = _count_by_category([row.current_category for row in rows])
    misses = [row for row in rows if row.miss]
    false_positives = [row for row in rows if row.false_positive]

    console.print(f"records: {len(rows)}")
    for category in _TRIGGER_SAMPLE_CATEGORIES:
        console.print(f"stored {category}: {stored_counts.get(category, 0)}")
    for category in _TRIGGER_SAMPLE_CATEGORIES:
        console.print(f"current {category}: {current_counts.get(category, 0)}")
    console.print(f"misses: {len(misses)}")
    for row in misses[:10]:
        console.print(f"  miss: {row.record.path}")
    console.print(f"false positives: {len(false_positives)}")
    for row in false_positives[:10]:
        console.print(f"  false positive: {row.record.path}")
    for speaker in _SPEAKER_LABELS:
        speaker_rows = [row for row in rows if row.record.speaker == speaker]
        speaker_misses = sum(1 for row in speaker_rows if row.miss)
        speaker_false_positives = sum(1 for row in speaker_rows if row.false_positive)
        speaker_answers = sum(1 for row in speaker_rows if row.current_will_answer)
        console.print(
            f"speaker {speaker}: records={len(speaker_rows)} "
            f"misses={speaker_misses} "
            f"false positives={speaker_false_positives} "
            f"answers={speaker_answers}"
        )


def _count_by_category(categories: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for category in categories:
        counts[category] = counts.get(category, 0) + 1
    return counts


def _promote_trigger_sample(ctx, config, profile: str, sample_path: Path):
    from saymo.config import load_config

    record = _load_trigger_sample(sample_path)
    variant = _extract_trigger_variant(record.transcript)
    if not variant:
        raise click.ClickException(f"No transcript variant to promote in {sample_path}")

    config_path = _config_path_for_update(ctx)
    canonical = _default_trigger_for_profile(config, profile)
    learned = _learn_trigger_variant(config_path, canonical, variant)
    console.print(f"promote sample: {sample_path}")
    console.print(f"trigger: {canonical}")
    console.print(f"variant: {variant}")
    console.print(f"learned: {'yes' if learned else 'no'}")
    return load_config(str(config_path))


def _play_trigger_sample(record: TriggerSampleRecord) -> None:
    import sounddevice as sd
    import soundfile as sf

    wav_path = record.path.with_name(record.wav)
    if not wav_path.exists():
        raise click.ClickException(f"WAV not found: {wav_path}")
    audio, sample_rate = sf.read(str(wav_path), dtype="float32")
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
    console.print("played: yes")


def _render_trigger_report(profile: str, rows: list[TriggerEvaluationRow]) -> str:
    stored_counts = _count_by_category([row.record.category for row in rows])
    current_counts = _count_by_category([row.current_category for row in rows])
    misses = [row for row in rows if row.miss]
    false_positives = [row for row in rows if row.false_positive]

    lines = [
        "# Saymo Trigger Sample Report",
        "",
        f"profile: {profile}",
        f"records: {len(rows)}",
        f"misses: {len(misses)}",
        f"false positives: {len(false_positives)}",
        "",
        "## Stored Categories",
    ]
    for category in _TRIGGER_SAMPLE_CATEGORIES:
        lines.append(f"- {category}: {stored_counts.get(category, 0)}")
    lines.extend(["", "## Current Categories"])
    for category in _TRIGGER_SAMPLE_CATEGORIES:
        lines.append(f"- {category}: {current_counts.get(category, 0)}")
    lines.extend(["", "## Speakers"])
    for speaker in _SPEAKER_LABELS:
        speaker_rows = [row for row in rows if row.record.speaker == speaker]
        lines.append(f"- {speaker}: {len(speaker_rows)}")
    lines.extend(["", "## Answer Decisions"])
    decision_counts = _count_by_category([row.record.answer_decision for row in rows])
    for decision in _ANSWER_DECISION_LABELS:
        lines.append(f"- {decision}: {decision_counts.get(decision, 0)}")
    lines.extend(["", "## Samples"])
    for row in rows:
        lines.append(
            "- "
            f"{row.record.path.name}: stored={row.record.category}, "
            f"current={row.current_category}, "
            f"speaker={row.record.speaker}, "
            f"decision={row.record.answer_decision}, "
            f"trigger={'yes' if row.current_trigger else 'no'}, "
            f"question={'yes' if row.current_question else 'no'}, "
            f"will_answer={'yes' if row.current_will_answer else 'no'}, "
            f"rms={row.record.rms:.4f}, peak={row.record.peak:.4f}"
        )
    return "\n".join(lines) + "\n"


def _print_trigger_session_summary(session) -> None:
    summary = session.summary
    console.print(f"session: {session.session_id}")
    console.print(f"name: {session.session_name}")
    console.print(f"profile: {session.profile}")
    console.print(f"status: {session.status}")
    console.print(f"started: {session.started_at or '-'}")
    console.print(f"ended: {session.ended_at or '-'}")
    if summary.first_sample_at or summary.last_sample_at:
        console.print(
            "sample range: "
            f"{summary.first_sample_at or '-'} -> {summary.last_sample_at or '-'}"
        )
    console.print(
        f"windows: total={summary.total_windows} "
        f"saved={summary.saved_samples} "
        f"skipped_silence={summary.skipped_silence}"
    )
    for category in _TRIGGER_SAMPLE_CATEGORIES:
        console.print(f"category {category}: {summary.categories.get(category, 0)}")
    for speaker in _SPEAKER_LABELS:
        console.print(f"speaker {speaker}: {summary.speakers.get(speaker, 0)}")
    for decision in _ANSWER_DECISION_LABELS:
        console.print(
            f"decision {decision}: {summary.answer_decisions.get(decision, 0)}"
        )
    console.print(f"readiness: {summary.readiness}")
    if session.path:
        console.print(f"ledger: {session.path}")


# ---------------------------------------------------------------------------
# manual takeover diagnostics
# ---------------------------------------------------------------------------

@main.command("takeover-check")
@click.option("--profile", "-p", default="personal", help="Meeting profile to inspect")
@click.option("--provider", default=None, help="Override call provider from the profile")
@click.option("--recording-device", default=None, help="Real microphone to switch to")
@click.option("--saymo-device", default="BlackHole 2ch", show_default=True, help="Saymo virtual mic")
@click.pass_context
def takeover_check(ctx, profile, provider, recording_device, saymo_device):
    """Check whether manual takeover can switch the call microphone."""
    config = ctx.obj["config"]
    _print_takeover_diagnostics(
        config,
        profile=profile,
        provider_name=provider,
        recording_device=recording_device,
        saymo_device=saymo_device,
    )


def _print_takeover_diagnostics(
    config,
    *,
    profile: str,
    provider_name: str | None,
    recording_device: str | None,
    saymo_device: str,
) -> None:
    from saymo.providers.factory import get_provider

    meeting = config.get_meeting(profile)
    resolved_provider = provider_name or (meeting.provider if meeting else "glip")
    real_mic = recording_device or config.audio.recording_device

    console.print(f"profile: {profile}")
    console.print(f"provider: {resolved_provider}")
    console.print(f"recording mic: {real_mic or '(not configured)'}")
    console.print(f"saymo mic: {saymo_device}")

    if not real_mic:
        console.print("takeover: not ready")
        console.print("reason: audio.recording_device is not configured")
        return

    provider = get_provider(resolved_provider)
    status = provider.check_ready()
    console.print(f"meeting: {'yes' if status.meeting_found else 'no'}")
    if status.tab_info:
        console.print(f"tab: window {status.tab_info[0]}, tab {status.tab_info[1]}")
    if not status.meeting_found:
        console.print("takeover: not ready")
        console.print(f"reason: {provider.name} tab not found in Chrome")
        return

    try:
        to_real = provider.switch_mic(real_mic)
    except Exception as e:
        console.print("switch to recording mic: no")
        console.print(f"reason: {e}")
        console.print("takeover: not ready")
        return
    console.print(f"switch to recording mic: {'yes' if to_real else 'no'}")

    try:
        to_saymo = provider.switch_mic(saymo_device)
    except Exception as e:
        console.print("switch back to Saymo mic: no")
        console.print(f"reason: {e}")
        console.print("takeover: not ready")
        return
    console.print(f"switch back to Saymo mic: {'yes' if to_saymo else 'no'}")

    if to_real and to_saymo:
        console.print("takeover: ready")
    else:
        console.print("takeover: not ready")
        console.print("reason: provider could not switch one or both microphones")


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

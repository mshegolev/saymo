"""Core user-flow commands: auto, speak, quick, prepare, review, dashboard."""

import hashlib
import json

import click

from saymo.analysis.realtime_gate import (
    automatic_handbrake_block,
    evaluate_realtime_launch_gate,
    provider_playback_block,
    render_realtime_launch_block,
)
from saymo.analysis.realtime_policy import (
    RealtimeResponseDecision,
    build_realtime_response_cache,
    resolve_realtime_response_decision,
)
from saymo.commands import (
    _get_cached_audio_path,
    _load_cached_summary,
    _play_cached_audio,
    _rotate_audio_cache,
    console,
    main,
    run_async,
)


# ---------------------------------------------------------------------------
# auto — listen for name trigger and speak automatically
# ---------------------------------------------------------------------------

def _classify_trigger_window(
    config,
    transcript_window: str,
    trigger_phrases: list[str],
    meeting=None,
):
    from saymo.analysis.addressing import classify_addressing, expand_trigger_phrases

    expanded = expand_trigger_phrases(
        trigger_phrases,
        (config.vocabulary or {}).get("fuzzy_expansions"),
    )
    return classify_addressing(
        transcript_window,
        expanded,
        **_addressing_pattern_options(meeting),
    )


def _addressing_pattern_options(meeting) -> dict[str, tuple[str, ...]]:
    addressing = getattr(meeting, "addressing", None) if meeting else None
    if not isinstance(addressing, dict):
        return {"handoff_patterns": (), "mention_only_patterns": ()}
    return {
        "handoff_patterns": _config_pattern_list(addressing.get("handoff_patterns")),
        "mention_only_patterns": _config_pattern_list(
            addressing.get("mention_only_patterns")
        ),
    }


def _config_pattern_list(value) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return ()


def _should_answer_trigger_window(
    config,
    transcript_window: str,
    trigger_phrases: list[str],
) -> bool:
    from saymo.analysis.addressing import should_answer_decision

    decision = _classify_trigger_window(config, transcript_window, trigger_phrases)
    return should_answer_decision(decision)


def _trigger_confirmation_timeout(config) -> float:
    try:
        timeout = float(getattr(config.safety, "confirmation_timeout_seconds", 6.0))
    except (TypeError, ValueError):
        timeout = 6.0
    return max(0.1, timeout)


def _prefer_question_window(first_window: str, second_window: str) -> str:
    from saymo.analysis.addressing import looks_like_question

    if looks_like_question(second_window) and not looks_like_question(first_window):
        return second_window
    return first_window or second_window


def _update_trigger_confirmation(
    config,
    *,
    now: float,
    pending: tuple[float, str] | None,
    transcript_window: str,
) -> tuple[bool, tuple[float, str] | None, str, str]:
    """Update optional double-trigger confirmation state.

    Returns ``(confirmed, pending, response_window, state)``. When the first
    trigger is a full question and the second is only the repeated name, the
    stored first transcript remains the response window.
    """
    if not getattr(config.safety, "require_confirmation", False):
        return True, None, transcript_window, "disabled"

    if pending is not None:
        expires_at, first_window = pending
        if now <= expires_at:
            return (
                True,
                None,
                _prefer_question_window(first_window, transcript_window),
                "confirmed",
            )

    timeout = _trigger_confirmation_timeout(config)
    return False, (now + timeout, transcript_window), "", "waiting"


def _toggle_manual_takeover(
    paused,
    stop_playback,
    manual_takeover,
    *,
    provider=None,
    recording_device: str = "",
    saymo_device: str = "BlackHole 2ch",
) -> str:
    """Toggle manual takeover mode for answering in the call yourself."""
    if manual_takeover.is_set():
        mic_failed = False
        if provider is not None:
            try:
                if not provider.switch_mic(saymo_device):
                    mic_failed = True
            except Exception:
                mic_failed = True
        manual_takeover.clear()
        paused.clear()
        if mic_failed:
            return "resumed_mic_failed"
        return "resumed"

    manual_takeover.set()
    paused.set()
    stop_playback.set()
    if provider is not None and recording_device:
        try:
            if not provider.switch_mic(recording_device):
                return "active_mic_failed"
        except Exception:
            return "active_mic_failed"
    if provider is not None and not recording_device:
        return "active_no_recording_device"
    return "active"


def _toggle_auto_pause(paused, manual_takeover) -> str:
    """Toggle ordinary auto-mode pause unless manual takeover owns the pause."""
    if manual_takeover.is_set():
        return "manual_takeover_active"
    if paused.is_set():
        paused.clear()
        return "resumed"
    paused.set()
    return "paused"


def _toggle_auto_answer(auto_answer_enabled, paused, manual_takeover, hard_disabled) -> str:
    """Toggle the handbrake boundary for automatic answers."""
    if manual_takeover.is_set():
        return "manual_takeover_active"
    if auto_answer_enabled.is_set():
        auto_answer_enabled.clear()
        paused.set()
        return "auto_answer_off"
    hard_disabled.clear()
    auto_answer_enabled.set()
    paused.clear()
    return "auto_answer_on"


def _hard_disable_auto_answer(auto_answer_enabled, paused, stop_playback, hard_disabled) -> str:
    """Stop playback and keep automatic answers disabled until re-enabled."""
    auto_answer_enabled.clear()
    hard_disabled.set()
    paused.set()
    stop_playback.set()
    return "hard_disabled"


def _automatic_speaking_allowed(auto_answer_enabled, manual_takeover, hard_disabled) -> bool:
    """Whether an automatic trigger may proceed to playback."""
    return (
        auto_answer_enabled.is_set()
        and not manual_takeover.is_set()
        and not hard_disabled.is_set()
    )


def _request_manual_speak(
    triggered,
    manual_speak,
    speaking,
    manual_takeover,
    hard_disabled=None,
) -> str:
    """Queue an explicit hotkey-triggered prepared playback in auto-mode."""
    if hard_disabled is not None and hard_disabled.is_set():
        return "hard_disabled"
    if manual_takeover.is_set():
        return "manual_takeover_active"
    if speaking.is_set():
        return "already_speaking"
    if manual_speak.is_set():
        return "already_queued"
    manual_speak.set()
    triggered.set()
    return "queued"


def _control_audit_context_from_command(command) -> dict:
    if command is None:
        return {}
    payload = getattr(command, "payload", {}) or {}
    return {
        "command_id": getattr(command, "command_id", "") or "",
        "probe_id": payload.get("probe_id", "") if isinstance(payload, dict) else "",
        "payload": payload if isinstance(payload, dict) else {},
    }


def _append_control_action_audit(
    profile: str,
    *,
    action: str,
    source: str,
    previous_state,
    next_state,
    result: str,
    reason: str = "",
    mic_result: str = "",
    command=None,
    base_dir=None,
):
    """Append action audit, preserving optional command correlation."""
    from saymo.analysis.live_control import append_control_audit

    return append_control_audit(
        profile,
        action=action,
        source=source,
        previous_state=previous_state,
        next_state=next_state,
        result=result,
        reason=reason,
        mic_result=mic_result,
        base_dir=base_dir,
        **_control_audit_context_from_command(command),
    )


def _should_register_local_hotkeys(config, *, disable_local_hotkeys: bool = False) -> bool:
    """Return whether `saymo auto` should own its local hotkey listener."""
    return not disable_local_hotkeys


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
    _run_auto_start(ctx, profile, model, mic)


@main.command("realtime")
@click.option("--profile", "-p", default="standup", help="Meeting profile: standup, scrum, retro")
@click.option("--model", "-m", default="small", help="Whisper model: tiny, small, medium")
@click.option("--mic", is_flag=True, help="Listen from microphone (for testing)")
@click.pass_context
def realtime(ctx, profile, model, mic):
    """Start the realtime meeting loop through the same path as auto."""
    _run_auto_start(ctx, profile, model, mic)


def _run_auto_start(ctx, profile, model, mic):
    """Resolve CLI options shared by auto/realtime before entering _auto."""
    config = ctx.obj["config"]
    meeting = config.get_meeting(profile)
    if meeting:
        console.print(f"[bold blue]Meeting: {profile} — {meeting.description}[/]")
    if mic:
        config.audio.capture_device = config.audio.recording_device
    run_async(_auto(config, model, profile))


async def _auto(
    config,
    whisper_model: str,
    profile: str = "standup",
    *,
    disable_local_hotkeys: bool = False,
):
    import asyncio
    import time
    from dataclasses import dataclass

    # Get meeting profile for trigger phrases
    meeting = config.get_meeting(profile)
    provider_name = meeting.provider if meeting else "glip"
    is_team = meeting.team if meeting else False
    from saymo.config import resolve_live_tuning
    live_tuning = resolve_live_tuning(config, meeting)

    launch_gate = evaluate_realtime_launch_gate(
        config,
        profile=profile,
        provider_name=provider_name,
    )
    if not launch_gate.allowed:
        console.print(
            render_realtime_launch_block(launch_gate),
            markup=False,
            soft_wrap=True,
        )
        return

    @dataclass
    class CatchTiming:
        capture_ms: float = 0.0
        transcription_ms: float = 0.0
        trigger_ms: float = 0.0

        @property
        def total_ms(self) -> float:
            return self.capture_ms + self.transcription_ms + self.trigger_ms

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
    console.print(
        "  Live tuning: "
        f"window={live_tuning.chunk_seconds:.1f}s "
        f"overlap={live_tuning.overlap_seconds:.1f}s "
        f"cooldown={live_tuning.trigger_cooldown_seconds:.1f}s "
        f"silence_rms={live_tuning.silence_rms_threshold:.4f}"
    )
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/]")
    console.print("[bold yellow]Listening...[/]\n")

    from saymo.audio.capture import AudioCapture
    from saymo.stt.whisper_local import LocalWhisper
    from saymo.analysis.addressing import should_answer_decision
    from saymo.analysis.live_control import (
        LiveControlSnapshot,
        append_control_audit,
        command_log_offset,
        effective_hotkey_bindings,
        hotkey_listener_bindings,
        live_control_dir,
        read_control_commands,
        write_live_state,
    )
    from saymo.analysis.turn_detector import TurnDetector

    capture = AudioCapture(
        device_name=config.audio.capture_device,
        sample_rate=16000,
        chunk_seconds=live_tuning.chunk_seconds,
        overlap_seconds=live_tuning.overlap_seconds,
    )
    whisper = LocalWhisper(model_size=whisper_model, language=config.user.language)
    detector = TurnDetector(
        name_variants=trigger_phrases,
        cooldown_seconds=live_tuning.trigger_cooldown_seconds,
        fuzzy_expansions=(config.vocabulary or {}).get("fuzzy_expansions"),
    )

    response_cache = build_realtime_response_cache(config)
    if response_cache is not None:
        console.print(
            f"[dim]Q&A cache: {len(response_cache.library)} intents[/]"
        )

    triggered = asyncio.Event()
    speaking = asyncio.Event()
    stop_playback = asyncio.Event()
    paused = asyncio.Event()
    manual_takeover = asyncio.Event()
    manual_speak = asyncio.Event()
    auto_answer_enabled = asyncio.Event()
    auto_answer_enabled.set()
    hard_disabled = asyncio.Event()
    skip_current = asyncio.Event()
    pending_confirmation: tuple[float, str] | None = None
    last_catch_timing = CatchTiming()
    last_trigger_text = ""
    last_action = "started"
    hotkeys_active = False
    control_offset = command_log_offset(profile)
    control_path = live_control_dir(profile)

    def _snapshot(action: str | None = None) -> LiveControlSnapshot:
        return LiveControlSnapshot(
            profile=profile,
            auto_answer_enabled=auto_answer_enabled.is_set(),
            paused=paused.is_set(),
            speaking=speaking.is_set(),
            manual_takeover=manual_takeover.is_set(),
            hard_disabled=hard_disabled.is_set(),
            hotkeys_active=hotkeys_active,
            last_trigger=last_trigger_text,
            last_action=action or last_action,
        )

    def _publish_state(action: str | None = None) -> LiveControlSnapshot:
        snapshot = _snapshot(action)
        write_live_state(profile, snapshot)
        return snapshot

    def _audit_action(
        action: str,
        source: str,
        previous: LiveControlSnapshot,
        result: str,
        *,
        reason: str = "",
        mic_result: str = "",
        command=None,
    ) -> None:
        _append_control_action_audit(
            profile,
            action=action,
            source=source,
            previous_state=previous,
            next_state=_snapshot(result),
            result=result,
            reason=reason,
            mic_result=mic_result,
            command=command,
        )

    _publish_state("started")

    def _apply_control_action(action: str, source: str = "panel", command=None) -> str:
        nonlocal last_action, pending_confirmation
        previous = _snapshot(last_action)
        result = "ignored"
        reason = ""
        mic_result = ""

        if action == "stop":
            stop_playback.set()
            result = "playback_stop_requested"
            console.print("[bold yellow]STOP — cancelling playback[/]")
        elif action == "toggle_auto_answer":
            result = _toggle_auto_answer(
                auto_answer_enabled,
                paused,
                manual_takeover,
                hard_disabled,
            )
            if result == "auto_answer_on":
                console.print("[bold green]Auto Answer ON — Saymo may answer triggers[/]")
            elif result == "auto_answer_off":
                console.print("[bold yellow]Auto Answer OFF — Saymo will not speak automatically[/]")
            else:
                console.print("[bold yellow]Manual takeover active — finish takeover before toggling auto-answer[/]")
        elif action == "speak":
            result = _request_manual_speak(
                triggered,
                manual_speak,
                speaking,
                manual_takeover,
                hard_disabled,
            )
            if result == "queued":
                console.print("[bold green]SPEAK — queued prepared playback[/]")
            elif result == "hard_disabled":
                console.print("[bold yellow]Hard disabled — enable Auto Answer before speaking[/]")
            elif result == "manual_takeover_active":
                console.print("[bold yellow]Manual takeover active — speak ignored[/]")
            elif result == "already_queued":
                console.print("[dim]Speak already queued[/]")
            else:
                console.print("[dim]Already speaking — speak ignored[/]")
        elif action == "takeover":
            result = _toggle_manual_takeover(
                paused,
                stop_playback,
                manual_takeover,
                provider=provider,
                recording_device=config.audio.recording_device,
            )
            mic_result = result
            if result == "active":
                console.print(
                    "[bold yellow]Manual takeover active — Saymo paused. "
                    f"Call mic switched to {config.audio.recording_device}. "
                    "Answer, then press takeover again.[/]"
                )
            elif result in {"active_mic_failed", "active_no_recording_device"}:
                console.print(
                    "[bold yellow]Manual takeover active — Saymo paused. "
                    "Switch the call mic manually, answer, then press takeover again.[/]"
                )
            elif result == "resumed_mic_failed":
                console.print(
                    "[bold yellow]Manual takeover ended — Saymo resumed, but "
                    "could not switch mic back to BlackHole 2ch.[/]"
                )
            else:
                console.print("[bold green]Manual takeover ended — Saymo resumed[/]")
        elif action == "skip_current":
            skip_current.set()
            triggered.clear()
            manual_speak.clear()
            pending_confirmation = None
            detector.reset_cooldown()
            result = "current_candidate_skipped"
            console.print("[bold yellow]SKIP — current candidate skipped[/]")
        elif action == "capture_marker":
            result = "capture_marker_recorded"
            reason = "operator marker for later review"
            console.print("[bold blue]Capture marker recorded for later review[/]")
        elif action == "status":
            result = "status_printed"
            snapshot = _snapshot(result)
            console.print(
                "[bold blue]status:[/] "
                f"auto={'on' if snapshot.auto_answer_enabled else 'off'} "
                f"paused={snapshot.paused} speaking={snapshot.speaking} "
                f"takeover={snapshot.manual_takeover} hard_disabled={snapshot.hard_disabled}"
            )
            console.print(f"[dim]control: {control_path}[/]")
        elif action == "hard_disable":
            result = _hard_disable_auto_answer(
                auto_answer_enabled,
                paused,
                stop_playback,
                hard_disabled,
            )
            pending_confirmation = None
            manual_speak.clear()
            triggered.clear()
            console.print("[bold red]HARD DISABLE — playback stopped; auto-answer off[/]")
        elif action == "approved_speak":
            result = "approved_speak_requested"
            reason = "approved draft playback must be executed by answer-cockpit action"
            console.print(
                "[bold yellow]Approved draft hotkey recorded. "
                "Use answer-cockpit action for the current approved draft.[/]"
            )

        last_action = result
        _publish_state(result)
        _audit_action(
            action,
            source,
            previous,
            result,
            reason=reason,
            mic_result=mic_result,
            command=command,
        )
        return result

    # Wire global hotkeys for stop/pause. Failures here (e.g., macOS
    # accessibility permissions missing) shouldn't break auto mode — just
    # log and continue without hotkeys.
    hotkey_listener = None
    if not _should_register_local_hotkeys(
        config,
        disable_local_hotkeys=disable_local_hotkeys,
    ):
        console.print("[dim]hotkeys: local listener disabled; using call-control daemon[/]")
    else:
        try:
            from pynput import keyboard as _keyboard
            loop = asyncio.get_running_loop()

            def _hotkey(action: str):
                return lambda: loop.call_soon_threadsafe(_apply_control_action, action, "hotkey")

            bindings = hotkey_listener_bindings(
                config,
                {
                    "toggle_auto_answer": _hotkey("toggle_auto_answer"),
                    "speak": _hotkey("speak"),
                    "stop": _hotkey("stop"),
                    "takeover": _hotkey("takeover"),
                    "approved_speak": _hotkey("approved_speak"),
                    "skip_current": _hotkey("skip_current"),
                    "capture_marker": _hotkey("capture_marker"),
                    "status": _hotkey("status"),
                    "hard_disable": _hotkey("hard_disable"),
                },
            )
            if bindings:
                hotkey_listener = _keyboard.GlobalHotKeys(bindings)
                hotkey_listener.start()
                hotkeys_active = True
                _publish_state("hotkeys_active")
                effective = effective_hotkey_bindings(config)
                console.print(
                    "[dim]hotkeys: "
                    + " ".join(f"{action}={hotkey}" for action, hotkey in effective.items())
                    + "[/]"
                )
        except Exception as e:
            console.print(f"[dim]hotkeys disabled: {e}[/]")

    async def _control_command_loop():
        """Apply commands written by `saymo live-control` or scripts."""
        nonlocal control_offset
        while True:
            commands, control_offset = await asyncio.to_thread(
                read_control_commands,
                profile,
                offset=control_offset,
            )
            for command in commands:
                _apply_control_action(command.action, command.source, command)
            await asyncio.sleep(0.25)

    async def _transcribe_loop():
        """Continuously transcribe audio — runs parallel to capture."""
        nonlocal last_catch_timing, last_trigger_text
        while True:
            if speaking.is_set() or paused.is_set():
                # Don't transcribe while we're speaking or paused
                await asyncio.sleep(0.5)
                continue

            capture_t0 = time.monotonic()
            chunk = await asyncio.to_thread(
                capture.get_chunk,
                live_tuning.read_timeout_seconds,
            )
            capture_ms = (time.monotonic() - capture_t0) * 1000
            if chunk is None:
                continue

            rms = float((chunk ** 2).mean() ** 0.5)
            if rms < live_tuning.silence_rms_threshold:
                continue

            transcribe_t0 = time.monotonic()
            text = await asyncio.to_thread(whisper.transcribe, chunk)
            transcription_ms = (time.monotonic() - transcribe_t0) * 1000
            if not text.strip():
                continue

            console.print(f"[dim]{text}[/]")

            trigger_t0 = time.monotonic()
            if detector.check(text):
                trigger_ms = (time.monotonic() - trigger_t0) * 1000
                last_catch_timing = CatchTiming(
                    capture_ms=capture_ms,
                    transcription_ms=transcription_ms,
                    trigger_ms=trigger_ms,
                )
                last_trigger_text = text
                _publish_state("trigger_detected")
                console.print(
                    "[dim]catch latency: "
                    f"capture={capture_ms:.0f}ms "
                    f"stt={transcription_ms:.0f}ms "
                    f"trigger={trigger_ms:.0f}ms "
                    f"total={last_catch_timing.total_ms:.0f}ms[/]"
                )
                console.print("\n[bold red]>>> NAME DETECTED![/]\n")
                triggered.set()
            else:
                trigger_ms = (time.monotonic() - trigger_t0) * 1000
                console.print(
                    "[dim]catch latency: "
                    f"capture={capture_ms:.0f}ms "
                    f"stt={transcription_ms:.0f}ms "
                    f"trigger={trigger_ms:.0f}ms action=listen[/]"
                )

    async def _trigger_loop():
        """Wait for trigger, then speak."""
        nonlocal pending_confirmation
        while True:
            await triggered.wait()
            triggered.clear()

            # Snapshot transcript window BEFORE draining — contains the question
            transcript_window = detector.recent_transcript
            force_speak = manual_speak.is_set()
            if force_speak:
                manual_speak.clear()

            if skip_current.is_set():
                skip_current.clear()
                detector.reset_cooldown()
                console.print("[dim]Current candidate skipped by control action[/]")
                console.print("\n[bold yellow]Listening again...[/]\n")
                continue

            if force_speak:
                transcript_window = ""
                pending_confirmation = None
                console.print("[dim]Manual speak hotkey: using prepared playback[/]")
            else:
                handbrake_block = automatic_handbrake_block(
                    auto_answer_enabled,
                    manual_takeover,
                    hard_disabled,
                )
                if handbrake_block is not None:
                    append_control_audit(
                        profile,
                        action="toggle_auto_answer",
                        source="auto",
                        previous_state=_snapshot("auto_blocked"),
                        next_state=_snapshot("auto_blocked"),
                        result="automatic_speaking_blocked",
                        reason=handbrake_block.reason,
                    )
                    detector.reset_cooldown()
                    console.print(
                        f"[bold yellow]Auto answer blocked:[/] "
                        f"{handbrake_block.detail}"
                    )
                    console.print("\n[bold yellow]Listening again...[/]\n")
                    continue
                addressing_t0 = time.monotonic()
                addressing = _classify_trigger_window(
                    config,
                    transcript_window,
                    trigger_phrases,
                    meeting,
                )
                addressing_ms = (time.monotonic() - addressing_t0) * 1000
                if not should_answer_decision(addressing):
                    console.print(
                        f"[dim]decision latency: addressing={addressing_ms:.0f}ms "
                        "action=skip[/]"
                    )
                    console.print(
                        f"[yellow]Skipping trigger:[/] {addressing.label} — {addressing.reason}"
                    )
                    if pending_confirmation and time.monotonic() > pending_confirmation[0]:
                        pending_confirmation = None
                    detector.reset_cooldown()
                    console.print("\n[bold yellow]Listening again...[/]\n")
                    continue

                action_t0 = time.monotonic()
                confirmed, pending_confirmation, response_window, confirmation_state = (
                    _update_trigger_confirmation(
                        config,
                        now=time.monotonic(),
                        pending=pending_confirmation,
                        transcript_window=transcript_window,
                    )
                )
                action_ms = (time.monotonic() - action_t0) * 1000
                if not confirmed:
                    console.print(
                        f"[dim]decision latency: addressing={addressing_ms:.0f}ms "
                        f"action={action_ms:.0f}ms final=wait_confirmation[/]"
                    )
                    console.print(
                        "[yellow]Confirmation required:[/] mention the trigger again "
                        f"within {_trigger_confirmation_timeout(config):.1f}s"
                    )
                    detector.reset_cooldown()
                    console.print("\n[bold yellow]Listening again...[/]\n")
                    continue
                if confirmation_state == "confirmed":
                    console.print("[dim]Trigger confirmed by second mention[/]")
                transcript_window = response_window
                console.print(
                    f"[dim]decision latency: addressing={addressing_ms:.0f}ms "
                    f"action={action_ms:.0f}ms final=answer[/]"
                )
                try:
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

                    assist = live_assist_status(profile)
                    model_path = classifier_model_path(profile)
                    if assist.enabled and model_path.exists():
                        prediction = predict_live_assist(
                            load_model(model_path),
                            TriggerClassifierSample(
                                transcript=transcript_window,
                                speaker="unknown",
                                decision="unlabeled",
                            ),
                        )
                        assist_decision = apply_live_assist_decision(
                            deterministic_will_answer=True,
                            classifier_prediction=prediction,
                        )
                        console.print(
                            f"[dim]live assist: {prediction.label} "
                            f"confidence={prediction.confidence:.2f} "
                            f"action={assist_decision.final_action}[/]"
                        )
                        if assist_decision.final_action == "skip":
                            detector.reset_cooldown()
                            console.print("\n[bold yellow]Listening again...[/]\n")
                            continue
                except Exception as e:
                    console.print(f"[dim]live assist skipped: {e}[/]")

            # Drain audio queue — don't process stale chunks after trigger
            while not capture.audio_queue.empty():
                try:
                    capture.audio_queue.get_nowait()
                except Exception:
                    break

            trigger_t = time.monotonic()

            resolve_t0 = time.monotonic()
            if force_speak:
                response_decision = RealtimeResponseDecision(
                    outcome="speak",
                    label="manual-standup-requested",
                    source="standup",
                    reason="manual prepared playback requested",
                    audio_path=cached_audio,
                    automatic=False,
                )
            else:
                response_decision = await resolve_realtime_response_decision(
                    config,
                    transcript_window=transcript_window,
                    response_cache=response_cache,
                )
            resolve_ms = (time.monotonic() - resolve_t0) * 1000

            console.print(
                f"[dim]response route: {response_decision.source} "
                f"({response_decision.label}: {response_decision.reason})[/]"
            )
            if response_decision.outcome != "speak" or response_decision.audio_path is None:
                detector.reset_cooldown()
                console.print("\n[bold yellow]Listening again...[/]\n")
                continue
            audio_to_play = response_decision.audio_path
            console.print(
                f"[bold blue]Speaking in {live_tuning.pre_speak_delay_seconds:.1f} seconds...[/]"
            )
            await asyncio.sleep(live_tuning.pre_speak_delay_seconds)

            handbrake_block = (
                None
                if force_speak
                else automatic_handbrake_block(
                    auto_answer_enabled,
                    manual_takeover,
                    hard_disabled,
                )
            )
            if handbrake_block is not None:
                append_control_audit(
                    profile,
                    action="toggle_auto_answer",
                    source="auto",
                    previous_state=_snapshot("playback_blocked"),
                    next_state=_snapshot("playback_blocked"),
                    result="automatic_playback_blocked",
                    reason=handbrake_block.reason,
                )
                detector.reset_cooldown()
                console.print(
                    f"[bold yellow]Playback blocked by handbrake:[/] "
                    f"{handbrake_block.detail}"
                )
                console.print("\n[bold yellow]Listening again...[/]\n")
                continue

            provider_block = None if force_speak else provider_playback_block(provider)
            if provider_block is not None:
                append_control_audit(
                    profile,
                    action="status",
                    source="auto",
                    previous_state=_snapshot("provider_blocked"),
                    next_state=_snapshot("provider_blocked"),
                    result=provider_block.label,
                    reason=provider_block.reason,
                )
                detector.reset_cooldown()
                console.print(
                    f"[bold yellow]Playback blocked by provider:[/] "
                    f"{provider_block.reason}"
                )
                console.print("\n[bold yellow]Listening again...[/]\n")
                continue

            speaking.set()
            _publish_state("speaking")
            play_t0 = time.monotonic()
            playback_start_ms: float | None = None
            playback_result = None
            max_dur = max(5, int(config.safety.max_speech_duration or 0))
            stop_playback.clear()

            def _mark_playback_start():
                nonlocal playback_start_ms
                if playback_start_ms is None:
                    playback_start_ms = (time.monotonic() - trigger_t) * 1000

            play_task = asyncio.create_task(
                _play_cached_audio(
                    config,
                    audio_to_play,
                    provider_name=provider_name,
                    on_playback_start=_mark_playback_start,
                    allow_provider_fallback=force_speak,
                )
            )
            stop_waiter = asyncio.create_task(stop_playback.wait())
            try:
                done, pending = await asyncio.wait(
                    {play_task, stop_waiter},
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=max_dur,
                )
                if stop_waiter in done:
                    play_task.cancel()
                elif not done:
                    play_task.cancel()
                    console.print(
                        f"[bold red]Playback exceeded {max_dur}s — forcibly stopped "
                        f"(safety.max_speech_duration).[/]"
                    )
                for p in pending:
                    p.cancel()
                try:
                    playback_result = await play_task
                except (asyncio.CancelledError, Exception):
                    playback_result = None
            finally:
                play_ms = (time.monotonic() - play_t0) * 1000
                total_ms = (time.monotonic() - trigger_t) * 1000
                is_cache_hit = (audio_to_play == cached_audio)
                playback_label = (
                    f"{playback_start_ms:.0f}ms"
                    if playback_start_ms is not None
                    else "not_started"
                )
                blocked_reason = ""
                if playback_result is not None and not playback_result.success:
                    blocked_reason = f" blocked={playback_result.reason}"
                console.print(
                    f"[dim]latency: resolve={resolve_ms:.0f}ms "
                    f"play_start={playback_label} play={play_ms:.0f}ms "
                    f"total={total_ms:.0f}ms "
                    f"({'standup' if is_cache_hit else 'Q&A'})"
                    f"{blocked_reason}[/]"
                )
                speaking.clear()
                _publish_state("listening")
                detector.reset_cooldown()
                if response_decision.cleanup_path:
                    try:
                        audio_to_play.unlink(missing_ok=True)
                    except Exception:
                        pass

            console.print("\n[bold yellow]Listening again...[/]\n")

    capture.start()

    try:
        await asyncio.gather(
            _control_command_loop(),
            _transcribe_loop(),
            _trigger_loop(),
        )

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/]")
    finally:
        capture.stop()
        if hotkey_listener is not None:
            try:
                hotkey_listener.stop()
            except Exception:
                pass
        hotkeys_active = False
        _publish_state("stopped")


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


@main.command("live-control")
@click.option("--profile", "-p", default="standup", help="Meeting profile to control")
@click.option(
    "--base-dir",
    default=None,
    type=click.Path(),
    help="Override live-control directory; defaults to ~/.saymo/live_control",
)
@click.pass_context
def live_control(ctx, profile, base_dir):
    """Open the local handbrake panel for a running `saymo auto`."""
    from saymo.live_control_tui import run_live_control_tui

    run_live_control_tui(profile, base_dir=base_dir)


@main.command("live-control-action")
@click.option("--profile", "-p", default="standup", help="Meeting profile to control")
@click.option(
    "--action",
    "action_name",
    required=True,
    help="Action: toggle_auto_answer, speak, stop, takeover, approved_speak, skip_current, capture_marker, status, hard_disable",
)
@click.option(
    "--base-dir",
    default=None,
    type=click.Path(),
    help="Override live-control directory; defaults to ~/.saymo/live_control",
)
def live_control_action(profile, action_name, base_dir):
    """Queue one live-control action for a running `saymo auto` process."""
    from saymo.analysis.live_control import append_control_command, normalize_action

    try:
        action = normalize_action(action_name)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    path = append_control_command(profile, action, source="cli", base_dir=base_dir)
    console.print(f"queued: {action}")
    console.print(f"commands: {path}")


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
        ready, reason = _call_ready_cached_audio(config, cached_audio)
        if ready:
            console.print(f"[green]Using cached audio from prepare ({cached_audio.stat().st_size // 1024} KB)[/]")
            await _play_cached_audio(config, cached_audio, provider_name)
            return
        console.print(f"[yellow]Cached audio ignored: {reason}[/]")

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

        await provider.unmute_speak_mute(_speak_text, config, standup_text, "live_call")
        return

    # Step 4: Speak without call automation
    await _speak_text(config, standup_text, "live_call")


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


async def _speak_text(config, text: str, purpose: str = "preview") -> None:
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
        audio_bytes = await _synthesize(config, text, purpose=purpose)
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


async def _synthesize(config, text: str, *, purpose: str = "prepare") -> bytes | None:
    """Synthesize text to audio bytes using configured TTS engine."""
    from saymo.tts.factory import UnsupportedTTSEngine
    from saymo.tts.selector import VoiceSelectorBlocked, get_selected_tts_engine
    try:
        selected = get_selected_tts_engine(config, purpose=purpose)
        return await selected.synthesize(text)
    except VoiceSelectorBlocked as e:
        console.print(
            f"[bold red]Voice selector blocked {purpose}:[/] "
            f"{e.decision.blocked_reason}"
        )
        return None
    except UnsupportedTTSEngine as e:
        console.print(f"[bold red]{e}[/]")
        return None
    except Exception as e:
        console.print(f"[bold red]TTS synthesis failed:[/] {e}")
        return None


def _call_ready_cached_audio(config, audio_path) -> tuple[bool, str]:
    """Check cached prepare audio before treating it as live-call ready."""
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        check_voice_cache_metadata,
    )
    from saymo.tts.selector import resolve_voice_selector

    live_decision = resolve_voice_selector(config, purpose="live_call")
    if not live_decision.allowed:
        return False, live_decision.blocked_reason

    expected = build_voice_cache_metadata(config, purpose="prepare")
    metadata_check = check_voice_cache_metadata(audio_path, expected)
    if not metadata_check.valid:
        return False, metadata_check.blocked_reason
    return True, ""


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
@click.option("--source", "-s", default=None, help="Source: obsidian, confluence, jira, file")
@click.option("--save/--no-save", default=True, help="Save summary to Obsidian daily note")
@click.option("--team", is_flag=True, help="Team scrum mode (report on all team members)")
@click.option("--skip-responses", is_flag=True, help="Skip Tier-A response-cache rebuild")
@click.pass_context
def prepare(ctx, profile, source, save, team, skip_responses):
    """Prepare standup summary BEFORE the daily meeting.

    Source resolution priority: --source flag > profile.source > config.speech.source.
    Use -p to select meeting profile: standup (default), scrum, retro.
    Also rebuilds the Tier-A response cache (pre-synthesised answers
    for common stand-up follow-ups). Pass --skip-responses to disable.
    """
    config = ctx.obj["config"]
    profile_name = profile or "standup"
    if profile:
        meeting = config.get_meeting(profile)
        if not meeting:
            console.print(f"[bold red]Unknown profile: {profile}[/]")
            console.print(f"[dim]Available: {', '.join(config.list_meetings())}[/]")
            return
        team = meeting.team
        if not source:
            config.speech.source = meeting.source
        console.print(f"[bold blue]Meeting: {profile} — {meeting.description}[/]")
    if source:
        config.speech.source = source
    if team:
        run_async(_prepare_team(config, save, profile_name=profile_name))
    else:
        run_async(_prepare(config, save, profile_name=profile_name))
    if not skip_responses and config.responses.enabled:
        console.print("")
        from saymo.commands.tests import _prepare_responses
        run_async(_prepare_responses(config, force=False))


def _source_notes_sha256(notes: dict) -> str:
    source_digest_material = json.dumps(notes, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(source_digest_material.encode("utf-8")).hexdigest()


async def _prepare(config, save: bool, *, profile_name: str = "standup"):
    _rotate_audio_cache()
    notes = await _get_standup_content(config)
    if notes is None:
        return
    source_sha256 = _source_notes_sha256(notes)

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
    audio_bytes = await _synthesize(config, normalized, purpose="prepare")
    if audio_bytes:
        audio_path = _get_cached_audio_path()
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio_bytes)
        from saymo.analysis.cache_metadata import (
            build_voice_cache_metadata,
            write_voice_cache_metadata,
        )
        write_voice_cache_metadata(
            audio_path,
            build_voice_cache_metadata(
                config,
                purpose="prepare",
                text=normalized,
                source_kind=config.speech.source,
                source_profile=profile_name,
                source_sha256=source_sha256,
            ),
        )
        console.print(f"[green]Audio cached: {audio_path} ({len(audio_bytes) // 1024} KB)[/]")
    else:
        console.print("[yellow]Audio pre-generation failed, will generate on speak[/]")

    console.print("\n[dim]Run 'saymo speak' — instant playback from cache![/]")


async def _prepare_team(config, save: bool, *, profile_name: str = "standup"):
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
    source_sha256 = _source_notes_sha256(notes)

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
    audio_bytes = await _synthesize(config, normalized, purpose="prepare")
    if audio_bytes:
        audio_path = _get_cached_audio_path(team=True)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio_bytes)
        from saymo.analysis.cache_metadata import (
            build_voice_cache_metadata,
            write_voice_cache_metadata,
        )
        write_voice_cache_metadata(
            audio_path,
            build_voice_cache_metadata(
                config,
                purpose="prepare",
                text=normalized,
                source_kind=config.speech.source,
                source_profile=profile_name,
                source_sha256=source_sha256,
            ),
        )
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

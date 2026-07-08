"""Integration tests for the question-detection and response-resolution
flow used by ``saymo auto`` (cli._resolve_auto_response)."""

import asyncio
import contextlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from saymo.cli import (
    _looks_like_question,
    _resolve_auto_response,
    _resolve_auto_response_decision,
)
from saymo.analysis.launch_readiness import (
    LaunchReadinessCheck,
    LaunchReadinessReport,
)
from saymo.commands import main
from saymo.commands import _play_cached_audio
from saymo.config import SaymoConfig
from saymo.commands.core import (
    _automatic_speaking_allowed,
    _append_control_action_audit,
    _should_register_local_hotkeys,
    _hard_disable_auto_answer,
    _request_manual_speak,
    _should_answer_trigger_window,
    _update_trigger_confirmation,
    _toggle_auto_answer,
    _toggle_auto_pause,
    _toggle_manual_takeover,
)
from saymo.analysis.live_control import (
    LiveControlCommand,
    LiveControlSnapshot,
    audit_log_path,
)


def _run(coro):
    """Run an async coroutine synchronously for tests — pytest-asyncio not installed."""
    return asyncio.run(coro)


def _write_auto_config(tmp_path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
user:
  name: "John"
  name_variants: ["John"]
audio:
  capture_device: "BlackHole 16ch"
  playback_device: "BlackHole 2ch"
  recording_device: "MacBook Pro Microphone"
meetings:
  standup:
    description: "Standup"
    provider: glip
    team: false
    source: obsidian
    trigger_phrases: ["John"]
responses:
  enabled: true
  live_fallback: false
""",
        encoding="utf-8",
    )
    return config_path


def _blocked_launch_report() -> LaunchReadinessReport:
    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="block",
                ok=False,
                detail="placeholder_only",
                action="Add usable standup content",
                rerun="saymo call-ready -p standup --provider glip",
            ),
        ),
    )


def _auto_loop_config(tmp_path: Path) -> tuple[SaymoConfig, Path]:
    config = SaymoConfig()
    config.user.name = "John"
    config.user.name_variants = ["John"]
    config.user.language = "en"
    config.audio.capture_device = "BlackHole 16ch"
    config.audio.playback_device = "BlackHole 2ch"
    config.audio.monitor_device = ""
    config.audio.recording_device = "MacBook Pro Microphone"
    config.safety.require_confirmation = False
    config.safety.max_speech_duration = 1
    config.live.chunk_seconds = 0.25
    config.live.overlap_seconds = 0.0
    config.live.read_timeout_seconds = 0.1
    config.live.trigger_cooldown_seconds = 0.0
    config.live.silence_rms_threshold = 0.0
    config.live.pre_speak_delay_seconds = 0.01
    config.meetings = {
        "standup": {
            "description": "Standup",
            "provider": "glip",
            "team": False,
            "source": "obsidian",
            "trigger_phrases": ["John"],
        }
    }
    audio_path = tmp_path / "standup.wav"
    audio_path.write_bytes(b"wav-bytes")
    return config, audio_path


class _AutoLoopChunk:
    def __pow__(self, _power):
        return self

    def mean(self):
        return 1.0


class _EmptyAudioQueue:
    def empty(self):
        return True

    def get_nowait(self):
        raise RuntimeError("empty")


class _FakeDetector:
    recent_transcript = "John, what is the status?"

    def __init__(self):
        self.triggered = False
        self.reset_count = 0

    def check(self, _text: str) -> bool:
        if self.triggered:
            return False
        self.triggered = True
        return True

    def reset_cooldown(self):
        self.reset_count += 1


def _install_auto_loop_fakes(
    monkeypatch,
    tmp_path: Path,
    *,
    provider,
    cached_audio: Path,
    control_commands=None,
    capture_delay: float = 0.0,
):
    import saymo.commands.core as core

    class FakeCapture:
        def __init__(self, *args, **kwargs):
            self.audio_queue = _EmptyAudioQueue()
            self.emitted = False

        def start(self):
            pass

        def stop(self):
            pass

        def get_chunk(self, _timeout):
            if not self.emitted:
                self.emitted = True
                if capture_delay:
                    time.sleep(capture_delay)
                return _AutoLoopChunk()
            time.sleep(0.01)
            return None

    class FakeWhisper:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, _chunk):
            return "John, what is the status?"

    detector = _FakeDetector()

    monkeypatch.setattr(
        core,
        "evaluate_realtime_launch_gate",
        lambda *args, **kwargs: SimpleNamespace(allowed=True),
    )
    monkeypatch.setattr(core, "_get_cached_audio_path", lambda team=False: cached_audio)
    monkeypatch.setattr(core, "_should_register_local_hotkeys", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        core,
        "_classify_trigger_window",
        lambda *args, **kwargs: SimpleNamespace(label="direct-question", reason="direct"),
    )
    monkeypatch.setattr(
        "saymo.analysis.addressing.should_answer_decision",
        lambda decision: True,
    )
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda device_name, kind=None: SimpleNamespace(index=1, name=device_name),
    )
    monkeypatch.setattr("saymo.providers.factory.get_provider", lambda provider_name: provider)
    monkeypatch.setattr("saymo.audio.capture.AudioCapture", FakeCapture)
    monkeypatch.setattr("saymo.stt.whisper_local.LocalWhisper", FakeWhisper)
    monkeypatch.setattr("saymo.analysis.turn_detector.TurnDetector", lambda *a, **k: detector)
    monkeypatch.setattr(core, "build_realtime_response_cache", lambda config: None)
    monkeypatch.setattr("saymo.analysis.live_control.command_log_offset", lambda profile: 0)
    monkeypatch.setattr(
        "saymo.analysis.live_control.live_control_dir",
        lambda profile, base_dir=None: tmp_path,
    )
    monkeypatch.setattr("saymo.analysis.live_control.write_live_state", lambda *a, **k: None)
    monkeypatch.setattr(
        "saymo.analysis.live_control.read_control_commands",
        control_commands or (lambda profile, offset=0: ([], offset)),
    )
    return core, detector


async def _run_auto_until(wait_for_event: asyncio.Event, coro):
    task = asyncio.create_task(coro)
    try:
        await asyncio.wait_for(wait_for_event.wait(), timeout=2.0)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


# ---------------------------------------------------------------------------
# _looks_like_question
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "какой у тебя статус?",
    "what is your eta?",
    "как дела с задачей",
    "расскажи про блокеры",
    "когда будет готово",
    "what is the status",
    "can you give an update",
])
def test_looks_like_question_true(text):
    assert _looks_like_question(text) is True


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "John, скажи",
    "hello world",
])
def test_looks_like_question_false(text):
    assert _looks_like_question(text) is False


def test_should_answer_trigger_window_allows_direct_question():
    config = SaymoConfig()

    assert _should_answer_trigger_window(
        config,
        "John, что по статусу?",
        ["John"],
    ) is True


def test_should_answer_trigger_window_ignores_narrated_mention():
    config = SaymoConfig()

    assert _should_answer_trigger_window(
        config,
        "как John вчера говорил, надо проверить логи",
        ["John"],
    ) is False


def test_trigger_confirmation_disabled_confirms_immediately():
    config = SaymoConfig()
    config.safety.require_confirmation = False

    confirmed, pending, response_window, state = _update_trigger_confirmation(
        config,
        now=100.0,
        pending=None,
        transcript_window="John, что по статусу?",
    )

    assert confirmed is True
    assert pending is None
    assert response_window == "John, что по статусу?"
    assert state == "disabled"


def test_trigger_confirmation_first_trigger_waits_for_second_mention():
    config = SaymoConfig()
    config.safety.require_confirmation = True
    config.safety.confirmation_timeout_seconds = 3.0

    confirmed, pending, response_window, state = _update_trigger_confirmation(
        config,
        now=100.0,
        pending=None,
        transcript_window="John, что по статусу?",
    )

    assert confirmed is False
    assert pending == (103.0, "John, что по статусу?")
    assert response_window == ""
    assert state == "waiting"


def test_trigger_confirmation_second_trigger_reuses_original_question_window():
    config = SaymoConfig()
    config.safety.require_confirmation = True
    config.safety.confirmation_timeout_seconds = 3.0

    confirmed, pending, response_window, state = _update_trigger_confirmation(
        config,
        now=102.0,
        pending=(103.0, "John, что по статусу?"),
        transcript_window="John",
    )

    assert confirmed is True
    assert pending is None
    assert response_window == "John, что по статусу?"
    assert state == "confirmed"


def test_trigger_confirmation_prefers_second_window_when_it_has_question():
    config = SaymoConfig()
    config.safety.require_confirmation = True
    config.safety.confirmation_timeout_seconds = 3.0

    confirmed, pending, response_window, state = _update_trigger_confirmation(
        config,
        now=102.0,
        pending=(103.0, "John"),
        transcript_window="John, что с задачей?",
    )

    assert confirmed is True
    assert pending is None
    assert response_window == "John, что с задачей?"
    assert state == "confirmed"


def test_trigger_confirmation_expired_window_starts_over():
    config = SaymoConfig()
    config.safety.require_confirmation = True
    config.safety.confirmation_timeout_seconds = 3.0

    confirmed, pending, response_window, state = _update_trigger_confirmation(
        config,
        now=104.0,
        pending=(103.0, "John, что по статусу?"),
        transcript_window="John, что с задачей?",
    )

    assert confirmed is False
    assert pending == (107.0, "John, что с задачей?")
    assert response_window == ""
    assert state == "waiting"


def test_manual_takeover_stops_playback_and_pauses_auto_mode():
    paused = asyncio.Event()
    stop_playback = asyncio.Event()
    manual_takeover = asyncio.Event()

    state = _toggle_manual_takeover(paused, stop_playback, manual_takeover)

    assert state == "active"
    assert paused.is_set()
    assert stop_playback.is_set()
    assert manual_takeover.is_set()


def test_manual_takeover_switches_call_mic_to_recording_device():
    paused = asyncio.Event()
    stop_playback = asyncio.Event()
    manual_takeover = asyncio.Event()
    provider = MagicMock()
    provider.switch_mic.return_value = True

    state = _toggle_manual_takeover(
        paused,
        stop_playback,
        manual_takeover,
        provider=provider,
        recording_device="MacBook Pro Microphone",
    )

    assert state == "active"
    provider.switch_mic.assert_called_once_with("MacBook Pro Microphone")


def test_manual_takeover_second_press_resumes_auto_mode():
    paused = asyncio.Event()
    stop_playback = asyncio.Event()
    manual_takeover = asyncio.Event()
    provider = MagicMock()
    provider.switch_mic.return_value = True
    _toggle_manual_takeover(paused, stop_playback, manual_takeover)

    state = _toggle_manual_takeover(
        paused,
        stop_playback,
        manual_takeover,
        provider=provider,
    )

    assert state == "resumed"
    assert not paused.is_set()
    assert manual_takeover.is_set() is False
    provider.switch_mic.assert_called_once_with("BlackHole 2ch")


def test_manual_takeover_resumes_with_warning_when_blackhole_restore_fails():
    paused = asyncio.Event()
    stop_playback = asyncio.Event()
    manual_takeover = asyncio.Event()
    provider = MagicMock()
    provider.switch_mic.return_value = False
    _toggle_manual_takeover(paused, stop_playback, manual_takeover)

    state = _toggle_manual_takeover(
        paused,
        stop_playback,
        manual_takeover,
        provider=provider,
    )

    assert state == "resumed_mic_failed"
    assert not paused.is_set()
    assert not manual_takeover.is_set()


def test_pause_toggle_does_not_resume_during_manual_takeover():
    paused = asyncio.Event()
    paused.set()
    manual_takeover = asyncio.Event()
    manual_takeover.set()

    state = _toggle_auto_pause(paused, manual_takeover)

    assert state == "manual_takeover_active"
    assert paused.is_set()
    assert manual_takeover.is_set()


def test_manual_speak_hotkey_queues_forced_playback():
    triggered = asyncio.Event()
    manual_speak = asyncio.Event()
    speaking = asyncio.Event()
    manual_takeover = asyncio.Event()

    state = _request_manual_speak(triggered, manual_speak, speaking, manual_takeover)

    assert state == "queued"
    assert triggered.is_set()
    assert manual_speak.is_set()


def test_manual_speak_hotkey_queues_when_auto_answer_off():
    triggered = asyncio.Event()
    manual_speak = asyncio.Event()
    speaking = asyncio.Event()
    manual_takeover = asyncio.Event()
    auto_answer_enabled = asyncio.Event()

    state = _request_manual_speak(triggered, manual_speak, speaking, manual_takeover)

    assert state == "queued"
    assert not auto_answer_enabled.is_set()
    assert triggered.is_set()
    assert manual_speak.is_set()


def test_manual_speak_hotkey_ignored_during_takeover():
    triggered = asyncio.Event()
    manual_speak = asyncio.Event()
    speaking = asyncio.Event()
    manual_takeover = asyncio.Event()
    manual_takeover.set()

    state = _request_manual_speak(triggered, manual_speak, speaking, manual_takeover)

    assert state == "manual_takeover_active"
    assert not triggered.is_set()
    assert not manual_speak.is_set()


def test_manual_speak_hotkey_ignored_when_hard_disabled():
    triggered = asyncio.Event()
    manual_speak = asyncio.Event()
    speaking = asyncio.Event()
    manual_takeover = asyncio.Event()
    hard_disabled = asyncio.Event()
    hard_disabled.set()

    state = _request_manual_speak(
        triggered,
        manual_speak,
        speaking,
        manual_takeover,
        hard_disabled,
    )

    assert state == "hard_disabled"
    assert not triggered.is_set()
    assert not manual_speak.is_set()


def test_manual_speak_hotkey_ignored_while_already_speaking():
    triggered = asyncio.Event()
    manual_speak = asyncio.Event()
    speaking = asyncio.Event()
    speaking.set()
    manual_takeover = asyncio.Event()

    state = _request_manual_speak(triggered, manual_speak, speaking, manual_takeover)

    assert state == "already_speaking"
    assert not triggered.is_set()
    assert not manual_speak.is_set()


def test_toggle_auto_answer_sets_handbrake_state():
    auto_answer_enabled = asyncio.Event()
    auto_answer_enabled.set()
    paused = asyncio.Event()
    manual_takeover = asyncio.Event()
    hard_disabled = asyncio.Event()

    state = _toggle_auto_answer(
        auto_answer_enabled,
        paused,
        manual_takeover,
        hard_disabled,
    )

    assert state == "auto_answer_off"
    assert not auto_answer_enabled.is_set()
    assert paused.is_set()
    assert not _automatic_speaking_allowed(
        auto_answer_enabled,
        manual_takeover,
        hard_disabled,
    )

    state = _toggle_auto_answer(
        auto_answer_enabled,
        paused,
        manual_takeover,
        hard_disabled,
    )

    assert state == "auto_answer_on"
    assert auto_answer_enabled.is_set()
    assert not paused.is_set()
    assert _automatic_speaking_allowed(
        auto_answer_enabled,
        manual_takeover,
        hard_disabled,
    )


def test_hard_disable_stops_playback_and_blocks_automatic_speaking():
    auto_answer_enabled = asyncio.Event()
    auto_answer_enabled.set()
    paused = asyncio.Event()
    stop_playback = asyncio.Event()
    manual_takeover = asyncio.Event()
    hard_disabled = asyncio.Event()

    state = _hard_disable_auto_answer(
        auto_answer_enabled,
        paused,
        stop_playback,
        hard_disabled,
    )

    assert state == "hard_disabled"
    assert not auto_answer_enabled.is_set()
    assert paused.is_set()
    assert stop_playback.is_set()
    assert hard_disabled.is_set()
    assert not _automatic_speaking_allowed(
        auto_answer_enabled,
        manual_takeover,
        hard_disabled,
    )


def test_control_command_audit_preserves_command_id_and_probe_id(tmp_path):
    command = LiveControlCommand(
        action="status",
        source="probe",
        command_id="cmd-123",
        payload={
            "probe_id": "probe-456",
            "raw_transcript": "private meeting text",
        },
    )
    previous = LiveControlSnapshot(profile="daily", last_action="started")
    next_state = LiveControlSnapshot(profile="daily", last_action="status_printed")

    _append_control_action_audit(
        "daily",
        action=command.action,
        source=command.source,
        previous_state=previous,
        next_state=next_state,
        result="status_printed",
        command=command,
        base_dir=tmp_path,
    )

    payload = json.loads(audit_log_path("daily", base_dir=tmp_path).read_text())
    assert payload["action"] == "status"
    assert payload["source"] == "probe"
    assert payload["command_id"] == "cmd-123"
    assert payload["probe_id"] == "probe-456"
    assert payload["payload"] == {"probe_id": "probe-456"}
    assert "private meeting text" not in json.dumps(payload)


def test_auto_can_skip_local_hotkeys_when_daemon_controls_are_enabled():
    config = SaymoConfig()

    assert _should_register_local_hotkeys(config) is True
    assert _should_register_local_hotkeys(config, disable_local_hotkeys=True) is False


def test_auto_launch_gate_blocks_before_realtime_setup(monkeypatch, capsys):
    import saymo.commands.core as core

    config = SaymoConfig()
    config.meetings = {
        "standup": {
            "description": "Standup",
            "provider": "glip",
            "team": False,
            "source": "obsidian",
            "trigger_phrases": ["John"],
        }
    }
    report = _blocked_launch_report()
    gate = type(
        "Gate",
        (),
        {
            "profile": "standup",
            "provider": "glip",
            "allowed": False,
            "reason": "launch-readiness-blocked",
            "report": report,
        },
    )()
    forbidden = MagicMock(
        side_effect=AssertionError("blocked gate must return before realtime setup")
    )

    monkeypatch.setattr(
        core,
        "evaluate_realtime_launch_gate",
        lambda config, *, profile, provider_name=None: gate,
        raising=False,
    )
    monkeypatch.setattr(
        core,
        "render_realtime_launch_block",
        lambda gate: "call-ready: not ready\nrealtime: blocked (launch-readiness-blocked)",
        raising=False,
    )
    monkeypatch.setattr(core, "_get_cached_audio_path", forbidden)
    events = []
    monkeypatch.setattr(
        core,
        "append_realtime_decision_event",
        lambda profile, event, **kwargs: events.append(event.to_dict()),
        raising=False,
    )

    _run(core._auto(config, "tiny", "standup"))

    forbidden.assert_not_called()
    output = capsys.readouterr().out
    assert "call-ready: not ready" in output
    assert "launch-readiness-blocked" in output
    assert [event["label"] for event in events] == [
        "launch-start",
        "launch-readiness-blocked",
        "launch-end",
    ]
    assert events[0] == {
        "created_at": events[0]["created_at"],
        "profile": "standup",
        "provider": "glip",
        "outcome": "skipped",
        "label": "launch-start",
        "source": "launch_readiness",
        "automatic": True,
        "intent_key": "",
        "confidence": None,
        "audio_path": "",
        "detail": "realtime launch starting",
    }
    assert events[1] == {
        "created_at": events[1]["created_at"],
        "profile": "standup",
        "provider": "glip",
        "outcome": "blocked",
        "label": "launch-readiness-blocked",
        "source": "launch_readiness",
        "automatic": True,
        "intent_key": "",
        "confidence": None,
        "audio_path": "",
        "detail": "launch-readiness-blocked",
    }
    assert events[2] == {
        "created_at": events[2]["created_at"],
        "profile": "standup",
        "provider": "glip",
        "outcome": "skipped",
        "label": "launch-end",
        "source": "launch_readiness",
        "automatic": True,
        "intent_key": "",
        "confidence": None,
        "audio_path": "",
        "detail": "launch-readiness-blocked",
    }


def test_auto_successful_playback_emits_runtime_evidence_labels(
    tmp_path,
    monkeypatch,
):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        playback_done = asyncio.Event()
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(
                return_value=core.RealtimeResponseDecision(
                    outcome="speak",
                    label="response-cache-hit",
                    source="response_cache",
                    reason="prepared cached response selected",
                    audio_path=audio_path,
                    intent_key="status_ready",
                    confidence=0.91,
                )
            ),
        )

        async def fake_play_cached_audio(*args, **kwargs):
            on_playback_start = kwargs.get("on_playback_start")
            if on_playback_start:
                on_playback_start()
            playback_done.set()
            return SimpleNamespace(
                success=True,
                reason="",
                playback_started=True,
            )

        monkeypatch.setattr(core, "_play_cached_audio", fake_play_cached_audio)
        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            lambda profile, event, **kwargs: events.append(event.to_dict()),
            raising=False,
        )

        await _run_auto_until(
            playback_done,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        assert [event["label"] for event in events] == [
            "launch-start",
            "response-cache-hit",
            "playback-attempted",
            "launch-end",
        ]
        assert events[2] == {
            "created_at": events[2]["created_at"],
            "profile": "standup",
            "provider": "glip",
            "outcome": "spoke",
            "label": "playback-attempted",
            "source": "playback",
            "automatic": True,
            "intent_key": "status_ready",
            "confidence": 0.91,
            "audio_path": str(audio_path),
            "detail": "response-cache-hit",
        }

    _run(scenario())


def test_auto_stop_control_emits_stop_and_cancel_events(
    tmp_path,
    monkeypatch,
):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        playback_started = asyncio.Event()
        playback_cancelled = asyncio.Event()
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True
        stop_sent = False

        def fake_read_control_commands(profile, offset=0):
            nonlocal stop_sent
            if playback_started.is_set() and not stop_sent:
                stop_sent = True
                return [
                    SimpleNamespace(
                        action="stop",
                        source="test",
                        command_id="cmd-stop",
                        payload={},
                    )
                ], 1
            return [], offset

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
            control_commands=fake_read_control_commands,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(
                return_value=core.RealtimeResponseDecision(
                    outcome="speak",
                    label="response-cache-hit",
                    source="response_cache",
                    reason="prepared cached response selected",
                    audio_path=audio_path,
                )
            ),
        )

        async def fake_play_cached_audio(*args, **kwargs):
            on_playback_start = kwargs.get("on_playback_start")
            if on_playback_start:
                on_playback_start()
            playback_started.set()
            await asyncio.sleep(10)
            return SimpleNamespace(
                success=True,
                reason="",
                playback_started=True,
            )

        def fake_append(profile, event, **kwargs):
            payload = event.to_dict()
            events.append(payload)
            if payload["label"] == "cancel-playback":
                playback_cancelled.set()

        monkeypatch.setattr(core, "_play_cached_audio", fake_play_cached_audio)
        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            fake_append,
            raising=False,
        )

        await _run_auto_until(
            playback_cancelled,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        labels = [event["label"] for event in events]
        assert "stop-requested" in labels
        assert "cancel-playback" in labels
        assert events[labels.index("stop-requested")]["source"] == "live_control"
        assert events[labels.index("cancel-playback")]["source"] == "live_control"

    _run(scenario())


def test_auto_playback_timeout_emits_timeout_event(tmp_path, monkeypatch):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        timeout_seen = asyncio.Event()
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(
                return_value=core.RealtimeResponseDecision(
                    outcome="speak",
                    label="response-cache-hit",
                    source="response_cache",
                    reason="prepared cached response selected",
                    audio_path=audio_path,
                )
            ),
        )

        async def fake_play_cached_audio(*args, **kwargs):
            on_playback_start = kwargs.get("on_playback_start")
            if on_playback_start:
                on_playback_start()
            await asyncio.sleep(10)
            return SimpleNamespace(
                success=True,
                reason="",
                playback_started=True,
            )

        def fake_append(profile, event, **kwargs):
            payload = event.to_dict()
            events.append(payload)
            if payload["label"] == "playback-timeout":
                timeout_seen.set()

        monkeypatch.setattr(core, "_play_cached_audio", fake_play_cached_audio)
        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            fake_append,
            raising=False,
        )

        await _run_auto_until(
            timeout_seen,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        labels = [event["label"] for event in events]
        assert "playback-timeout" in labels
        assert events[labels.index("playback-timeout")]["source"] == "live_control"

    _run(scenario())


def test_auto_launch_event_append_is_best_effort(monkeypatch, capsys):
    import saymo.commands.core as core

    config = SaymoConfig()
    config.meetings = {
        "standup": {
            "description": "Standup",
            "provider": "glip",
            "team": False,
            "source": "obsidian",
            "trigger_phrases": ["John"],
        }
    }
    gate = type(
        "Gate",
        (),
        {
            "profile": "standup",
            "provider": "glip",
            "allowed": False,
            "reason": "launch-readiness-blocked",
            "report": _blocked_launch_report(),
        },
    )()
    forbidden = MagicMock(
        side_effect=AssertionError("blocked gate must return before realtime setup")
    )

    monkeypatch.setattr(
        core,
        "evaluate_realtime_launch_gate",
        lambda config, *, profile, provider_name=None: gate,
        raising=False,
    )
    monkeypatch.setattr(
        core,
        "render_realtime_launch_block",
        lambda gate: "call-ready: not ready\nrealtime: blocked (launch-readiness-blocked)",
        raising=False,
    )
    monkeypatch.setattr(core, "_get_cached_audio_path", forbidden)
    monkeypatch.setattr(
        core,
        "append_realtime_decision_event",
        MagicMock(side_effect=RuntimeError("event log unavailable")),
        raising=False,
    )

    _run(core._auto(config, "tiny", "standup"))

    forbidden.assert_not_called()
    output = capsys.readouterr().out
    assert "realtime event skipped" in output


def test_auto_launch_event_uses_allowlisted_event_shape(monkeypatch):
    import saymo.commands.core as core

    config = SaymoConfig()
    config.meetings = {
        "standup": {
            "description": "Standup",
            "provider": "glip",
            "team": False,
            "source": "obsidian",
            "trigger_phrases": ["John"],
        }
    }
    gate = type(
        "Gate",
        (),
        {
            "profile": "standup",
            "provider": "glip",
            "allowed": False,
            "reason": "launch-readiness-blocked",
            "report": _blocked_launch_report(),
        },
    )()
    events = []
    monkeypatch.setattr(
        core,
        "evaluate_realtime_launch_gate",
        lambda config, *, profile, provider_name=None: gate,
        raising=False,
    )
    monkeypatch.setattr(
        core,
        "render_realtime_launch_block",
        lambda gate: "call-ready: not ready\nrealtime: blocked (launch-readiness-blocked)",
        raising=False,
    )
    monkeypatch.setattr(
        core,
        "append_realtime_decision_event",
        lambda profile, event, **kwargs: events.append(event.to_dict()),
        raising=False,
    )

    _run(core._auto(config, "tiny", "standup"))

    serialized = json.dumps(events, ensure_ascii=False)
    assert "raw_transcript" not in serialized
    assert "generated_answer" not in serialized
    assert "daily_note" not in serialized
    assert "audio_bytes" not in serialized
    assert {key for event in events for key in event} == {
        "created_at",
        "profile",
        "provider",
        "outcome",
        "label",
        "source",
        "automatic",
        "intent_key",
        "confidence",
        "audio_path",
        "detail",
    }


def test_realtime_alias_delegates_to_same_auto_path(tmp_path, monkeypatch):
    import saymo.commands.core as core

    calls = []

    async def fake_auto(config, whisper_model, profile="standup", **kwargs):
        calls.append((whisper_model, profile, kwargs))

    monkeypatch.setattr(core, "_auto", fake_auto)

    runner = CliRunner()
    config_path = _write_auto_config(tmp_path)

    auto_result = runner.invoke(
        main,
        ["--config", str(config_path), "auto", "-p", "standup", "--model", "tiny"],
    )
    realtime_result = runner.invoke(
        main,
        ["--config", str(config_path), "realtime", "-p", "standup", "--model", "tiny"],
    )

    assert auto_result.exit_code == 0
    assert realtime_result.exit_code == 0
    assert calls == [
        ("tiny", "standup", {}),
        ("tiny", "standup", {}),
    ]


def test_auto_and_realtime_help_do_not_expose_unsafe_gate_options():
    runner = CliRunner()

    for command in ("auto", "realtime"):
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0
        help_text = result.output.lower()
        assert "unsafe" not in help_text
        assert "bypass" not in help_text
        assert "ignore-readiness" not in help_text
        assert "ignore_readiness" not in help_text
        assert "no-gate" not in help_text
        assert "no_gate" not in help_text


def test_auto_uses_realtime_policy_not_legacy_response_resolver():
    source = Path("saymo/commands/core.py").read_text(encoding="utf-8")

    assert "resolve_realtime_response_decision" in source
    assert "_resolve_auto_response_decision" not in source


@pytest.mark.parametrize(
    "action, expected_reason",
    [
        ("toggle_auto_answer", "auto-answer-off"),
        ("takeover", "manual-takeover"),
        ("hard_disable", "hard-disabled"),
    ],
)
def test_auto_trigger_loop_blocks_handbrake_before_response_resolution(
    tmp_path,
    monkeypatch,
    action,
    expected_reason,
):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        blocked = asyncio.Event()
        audits = []
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True

        read_calls = 0

        def fake_read_control_commands(profile, offset=0):
            nonlocal read_calls
            if read_calls == 0:
                read_calls += 1
                return [
                    SimpleNamespace(
                        action=action,
                        source="test",
                        command_id="cmd-1",
                        payload={},
                    )
                ], 1
            return [], offset

        def fake_append_control_audit(*args, **kwargs):
            audits.append(kwargs)
            if kwargs.get("result") == "automatic_speaking_blocked":
                blocked.set()

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
            control_commands=fake_read_control_commands,
            capture_delay=0.05,
        )
        resolver = AsyncMock(
            side_effect=AssertionError("blocked handbrake must not resolve response")
        )
        monkeypatch.setattr(core, "resolve_realtime_response_decision", resolver)
        monkeypatch.setattr(
            "saymo.analysis.live_control.append_control_audit",
            fake_append_control_audit,
        )
        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            lambda profile, event, **kwargs: events.append(event.to_dict()),
            raising=False,
        )

        await _run_auto_until(
            blocked,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        resolver.assert_not_called()
        assert any(expected_reason in audit.get("reason", "") for audit in audits)
        assert any(
            event["label"] == "handbrake-blocked"
            and event["outcome"] == "blocked"
            and event["detail"] == expected_reason
            for event in events
        )

    _run(scenario())


def test_auto_force_speak_uses_manual_standup_decision_without_automatic_paths(
    tmp_path,
    monkeypatch,
):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        playback_started = asyncio.Event()
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True
        read_calls = 0

        def fake_read_control_commands(profile, offset=0):
            nonlocal read_calls
            if read_calls == 0:
                read_calls += 1
                return [
                    SimpleNamespace(
                        action="speak",
                        source="test",
                        command_id="cmd-manual-speak",
                        payload={},
                    )
                ], 1
            return [], offset

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
            control_commands=fake_read_control_commands,
            capture_delay=0.2,
        )

        forbidden_cache = MagicMock()
        forbidden_cache.library = {}
        forbidden_cache.lookup.side_effect = AssertionError("cache lookup must not run")
        forbidden_cache.get_variant_by_key.side_effect = AssertionError(
            "cache key lookup must not run"
        )
        forbidden_cache.library_keys.side_effect = AssertionError(
            "cache keys must not be read"
        )
        monkeypatch.setattr(
            core,
            "build_realtime_response_cache",
            lambda config: forbidden_cache,
        )
        automatic_resolver = AsyncMock(
            side_effect=AssertionError("automatic resolver must not run")
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            automatic_resolver,
        )
        monkeypatch.setattr(
            "saymo.speech.ollama_composer.classify_intent",
            AsyncMock(side_effect=AssertionError("classifier must not run")),
        )
        monkeypatch.setattr(
            "saymo.speech.ollama_composer.answer_question",
            AsyncMock(side_effect=AssertionError("LLM must not run")),
        )
        monkeypatch.setattr(
            "saymo.tts.selector.get_selected_tts_engine",
            MagicMock(side_effect=AssertionError("TTS selector must not run")),
        )
        manual_calls = []

        def fake_manual_decision(*, prepared_standup_path, handbrake_block=None):
            manual_calls.append((prepared_standup_path, handbrake_block))
            return core.RealtimeResponseDecision(
                outcome="speak",
                label="manual-standup-requested",
                source="manual_standup",
                reason="manual prepared playback requested",
                audio_path=prepared_standup_path,
                automatic=False,
            )

        monkeypatch.setattr(
            core,
            "resolve_manual_standup_decision",
            fake_manual_decision,
            raising=False,
        )
        playback_calls = []

        async def fake_play_cached_audio(*args, **kwargs):
            playback_calls.append((args, kwargs))
            playback_started.set()
            return SimpleNamespace(
                success=True,
                reason="",
                playback_started=True,
            )

        monkeypatch.setattr(core, "_play_cached_audio", fake_play_cached_audio)
        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            lambda profile, event, **kwargs: events.append(event.to_dict()),
            raising=False,
        )

        await _run_auto_until(
            playback_started,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        assert manual_calls == [(audio_path, None)]
        assert playback_calls
        assert playback_calls[0][0][1] == audio_path
        assert playback_calls[0][1]["allow_provider_fallback"] is True
        automatic_resolver.assert_not_called()
        forbidden_cache.lookup.assert_not_called()
        forbidden_cache.get_variant_by_key.assert_not_called()
        forbidden_cache.library_keys.assert_not_called()
        assert any(
            event["label"] == "manual-standup-requested"
            and event["outcome"] == "spoke"
            and event["automatic"] is False
            for event in events
        )

    _run(scenario())


def test_auto_trigger_loop_checks_provider_before_automatic_playback(
    tmp_path,
    monkeypatch,
):
    async def scenario():
        import saymo.commands.core as core_module
        import saymo.commands as commands_module

        config, audio_path = _auto_loop_config(tmp_path)
        provider_rechecked = asyncio.Event()
        playback_calls = []
        events = []

        class Provider:
            name = "FakeMeet"

            def __init__(self):
                self.ready_checks = 0

            def check_ready(self):
                self.ready_checks += 1
                if self.ready_checks == 1:
                    return SimpleNamespace(meeting_found=True)
                provider_rechecked.set()
                return SimpleNamespace(meeting_found=False)

            def switch_mic(self, device_name):
                return True

        provider = Provider()
        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(
                return_value=core.RealtimeResponseDecision(
                    outcome="speak",
                    label="response-cache-hit",
                    source="response_cache",
                    reason="prepared cached response selected",
                    audio_path=audio_path,
                )
            ),
        )
        original_play_cached_audio = commands_module._play_cached_audio

        async def wrapped_play_cached_audio(*args, **kwargs):
            playback_calls.append((args, kwargs))
            return await original_play_cached_audio(*args, **kwargs)

        monkeypatch.setattr(core, "_play_cached_audio", wrapped_play_cached_audio)
        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            lambda profile, event, **kwargs: events.append(event.to_dict()),
            raising=False,
        )

        await _run_auto_until(
            provider_rechecked,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        assert playback_calls == []
        assert [event["label"] for event in events] == [
            "response-cache-hit",
            "provider-blocked",
        ]
        assert events[0]["outcome"] == "spoke"
        assert events[1]["outcome"] == "blocked"

    _run(scenario())


def test_auto_trigger_loop_emits_cache_miss_block_event(tmp_path, monkeypatch):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        blocked = asyncio.Event()
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(
                return_value=core.RealtimeResponseDecision(
                    outcome="block",
                    label="cache-miss-blocked",
                    source="response_cache",
                    reason="no prepared response-cache hit",
                )
            ),
        )

        def fake_append(profile, event, **kwargs):
            payload = event.to_dict()
            events.append(payload)
            if payload["label"] == "cache-miss-blocked":
                blocked.set()

        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            fake_append,
            raising=False,
        )

        await _run_auto_until(
            blocked,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        assert events[-1]["outcome"] == "blocked"
        assert events[-1]["label"] == "cache-miss-blocked"
        assert events[-1]["source"] == "response_cache"

    _run(scenario())


def test_auto_trigger_loop_emits_addressing_skip_before_live_assist(
    tmp_path,
    monkeypatch,
):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        skipped = asyncio.Event()
        events = []
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
        )
        monkeypatch.setattr(
            core,
            "_classify_trigger_window",
            lambda *args, **kwargs: SimpleNamespace(
                label="mention-only",
                reason="not addressed",
            ),
        )
        monkeypatch.setattr(
            "saymo.analysis.addressing.should_answer_decision",
            lambda decision: False,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(side_effect=AssertionError("skip must not resolve response")),
        )

        def fake_append(profile, event, **kwargs):
            payload = event.to_dict()
            events.append(payload)
            if payload["label"] == "addressing-skip":
                skipped.set()

        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            fake_append,
            raising=False,
        )

        await _run_auto_until(
            skipped,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        assert events[-1]["outcome"] == "skipped"
        assert events[-1]["label"] == "addressing-skip"
        assert events[-1]["source"] == "deterministic"

    _run(scenario())


def test_live_assist_can_skip_addressed_candidate_without_speaking(
    tmp_path,
    monkeypatch,
):
    async def scenario():
        import saymo.commands.core as core_module

        config, audio_path = _auto_loop_config(tmp_path)
        skipped = asyncio.Event()
        events = []
        model_path = tmp_path / "live-assist-model.json"
        model_path.write_text("{}", encoding="utf-8")
        provider = MagicMock()
        provider.name = "FakeMeet"
        provider.check_ready.return_value = SimpleNamespace(meeting_found=True)
        provider.switch_mic.return_value = True

        core, _detector = _install_auto_loop_fakes(
            monkeypatch,
            tmp_path,
            provider=provider,
            cached_audio=audio_path,
        )
        monkeypatch.setattr(
            "saymo.analysis.trigger_readiness.live_assist_status",
            lambda profile: SimpleNamespace(enabled=True),
        )
        monkeypatch.setattr(
            "saymo.analysis.trigger_classifier.classifier_model_path",
            lambda profile: model_path,
        )
        monkeypatch.setattr(
            "saymo.analysis.trigger_classifier.load_model",
            lambda path: object(),
        )
        monkeypatch.setattr(
            "saymo.analysis.trigger_classifier.predict_live_assist",
            lambda model, sample: SimpleNamespace(label="reject", confidence=0.96),
        )

        def fake_apply_live_assist_decision(*, deterministic_will_answer, classifier_prediction):
            assert deterministic_will_answer is True
            return SimpleNamespace(final_action="skip")

        monkeypatch.setattr(
            "saymo.analysis.trigger_readiness.apply_live_assist_decision",
            fake_apply_live_assist_decision,
        )
        monkeypatch.setattr(
            core,
            "resolve_realtime_response_decision",
            AsyncMock(side_effect=AssertionError("live assist skip must not speak")),
        )

        def fake_append(profile, event, **kwargs):
            payload = event.to_dict()
            events.append(payload)
            if payload["source"] == "live_assist":
                skipped.set()

        monkeypatch.setattr(
            core,
            "append_realtime_decision_event",
            fake_append,
            raising=False,
        )

        await _run_auto_until(
            skipped,
            core_module._auto(config, "tiny", "standup", disable_local_hotkeys=True),
        )

        assert events[-1]["outcome"] == "skipped"
        assert events[-1]["label"] == "addressing-skip"
        assert events[-1]["source"] == "live_assist"

    _run(scenario())


def test_play_cached_audio_strict_provider_fallback_blocks_direct_blackhole(
    tmp_path,
    monkeypatch,
):
    audio_path = tmp_path / "cached.wav"
    audio_path.write_bytes(b"wav-bytes")
    config = SaymoConfig()
    config.audio.monitor_device = ""

    class FailingProvider:
        name = "FailMeet"

        def check_ready(self):
            return SimpleNamespace(meeting_found=True)

        def switch_mic(self, device_name):
            return True

        async def unmute_speak_mute(self, speak_fn, *args, **kwargs):
            raise RuntimeError("mute automation failed")

    played = []

    async def fake_play_audio_bytes(audio_bytes, device_name):
        played.append((audio_bytes, device_name))

    monkeypatch.setattr(
        "saymo.providers.factory.get_provider",
        lambda provider_name: FailingProvider(),
    )
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda device_name, kind=None: object(),
    )
    monkeypatch.setattr(
        "saymo.audio.playback.play_audio_bytes",
        fake_play_audio_bytes,
    )

    result = _run(
        _play_cached_audio(
            config,
            audio_path,
            provider_name="failmeet",
            allow_provider_fallback=False,
        )
    )

    assert result.success is False
    assert result.reason == "provider-automation-blocked"
    assert result.playback_started is False
    assert played == []


def test_play_cached_audio_default_keeps_non_automatic_provider_fallback(
    tmp_path,
    monkeypatch,
):
    audio_path = tmp_path / "cached.wav"
    audio_path.write_bytes(b"wav-bytes")
    config = SaymoConfig()
    config.audio.monitor_device = ""

    class FailingProvider:
        name = "FailMeet"

        def check_ready(self):
            return SimpleNamespace(meeting_found=True)

        def switch_mic(self, device_name):
            return True

        async def unmute_speak_mute(self, speak_fn, *args, **kwargs):
            raise RuntimeError("mute automation failed")

    played = []

    async def fake_play_audio_bytes(audio_bytes, device_name):
        played.append((audio_bytes, device_name))

    monkeypatch.setattr(
        "saymo.providers.factory.get_provider",
        lambda provider_name: FailingProvider(),
    )
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda device_name, kind=None: object(),
    )
    monkeypatch.setattr(
        "saymo.audio.playback.play_audio_bytes",
        fake_play_audio_bytes,
    )

    result = _run(_play_cached_audio(config, audio_path, provider_name="failmeet"))

    assert result.success is True
    assert result.playback_started is True
    assert played == [(b"wav-bytes", "BlackHole 2ch")]


# ---------------------------------------------------------------------------
# _resolve_auto_response
# ---------------------------------------------------------------------------

def test_returns_fallback_when_no_cache():
    """No response cache → fallback to standup audio."""
    config = SaymoConfig()
    fallback = Path("/tmp/standup.wav")

    result = _run(_resolve_auto_response(
        config, "какой статус?", None, None, fallback
    ))
    assert result == fallback


def test_returns_fallback_when_not_a_question():
    """Trigger on a non-question transcript → standup audio."""
    config = SaymoConfig()
    cache = MagicMock()
    fallback = Path("/tmp/standup.wav")

    result = _run(_resolve_auto_response(
        config, "John, выйди на связь", cache, "", fallback
    ))
    assert result == fallback
    cache.lookup.assert_not_called()


def test_returns_cached_audio_on_hit():
    """Question + cache hit → returns cached audio path."""
    config = SaymoConfig()
    cached_path = Path("/tmp/status_done_0_abc.wav")

    cached = MagicMock()
    cached.key = "status_done"
    cached.confidence = 0.85
    cached.text = "Всё готово"
    cached.audio_path = cached_path

    cache = MagicMock()
    cache.lookup.return_value = cached

    fallback = Path("/tmp/standup.wav")
    result = _run(_resolve_auto_response(
        config, "как у тебя дела?", cache, "", fallback
    ))
    assert result == cached_path
    cache.lookup.assert_called_once()


def test_response_decision_reports_cache_reason():
    config = SaymoConfig()
    cached_path = Path("/tmp/status_done_0_abc.wav")

    cached = MagicMock()
    cached.key = "status_done"
    cached.confidence = 0.85
    cached.text = "Всё готово"
    cached.audio_path = cached_path

    cache = MagicMock()
    cache.lookup.return_value = cached

    fallback = Path("/tmp/standup.wav")
    decision = _run(_resolve_auto_response_decision(
        config, "как у тебя дела?", cache, "", fallback
    ))

    assert decision.audio_path == cached_path
    assert decision.source == "response_cache"
    assert "status_done" in decision.reason


def test_cache_miss_without_live_fallback_returns_standup():
    """Question + cache miss + live_fallback=False → standup audio."""
    config = SaymoConfig()
    config.responses.live_fallback = False

    cache = MagicMock()
    cache.lookup.return_value = None

    fallback = Path("/tmp/standup.wav")
    result = _run(_resolve_auto_response(
        config, "как ты?", cache, "", fallback
    ))
    assert result == fallback


def test_cache_miss_with_live_fallback_invokes_ollama(monkeypatch):
    """Question + cache miss + live_fallback=True → Ollama + TTS + temp WAV."""
    config = SaymoConfig()
    config.responses.live_fallback = True
    config.tts.engine = "f5tts_clone"

    cache = MagicMock()
    cache.lookup.return_value = None

    mock_answer = AsyncMock(return_value="Готово, работаю над задачей")
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.answer_question", mock_answer
    )

    mock_engine = MagicMock()
    mock_engine.synthesize = AsyncMock(return_value=b"RIFF....fake wav bytes")
    class FakeSelectedEngine:
        async def synthesize(self, text):
            return await mock_engine.synthesize(text)

    monkeypatch.setattr(
        "saymo.tts.selector.get_selected_tts_engine",
        lambda cfg, **kw: FakeSelectedEngine(),
    )

    fallback = Path("/tmp/standup.wav")
    result = _run(_resolve_auto_response(
        config, "какой у тебя план?", cache, "вчера закрыл тикет", fallback
    ))

    assert result != fallback
    assert result.exists()
    assert result.read_bytes() == b"RIFF....fake wav bytes"
    mock_answer.assert_awaited_once()
    mock_engine.synthesize.assert_awaited_once_with("Готово, работаю над задачей")

    result.unlink()


def test_cache_miss_with_live_fallback_returns_standup_when_selector_blocks(monkeypatch):
    """Live fallback respects call-ready selector gates."""
    config = SaymoConfig()
    config.responses.live_fallback = True
    config.tts.engine = "macos_say"

    cache = MagicMock()
    cache.lookup.return_value = None

    mock_answer = AsyncMock(return_value="Готово, работаю над задачей")
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.answer_question",
        mock_answer,
    )

    fallback = Path("/tmp/standup.wav")
    result = _run(_resolve_auto_response(
        config, "какой у тебя план?", cache, "вчера закрыл тикет", fallback
    ))

    assert result == fallback
    mock_answer.assert_awaited_once()


def test_intent_classifier_hit_returns_cached_audio(monkeypatch, tmp_path):
    """intent_classifier=True + classifier match → cached audio."""
    config = SaymoConfig()
    config.responses.intent_classifier = True

    cached_path = tmp_path / "eta_generic_0_abc.wav"
    cached_path.write_bytes(b"fake")

    cached = MagicMock()
    cached.key = "eta_generic"
    cached.text = "К пятнице"
    cached.audio_path = cached_path

    cache = MagicMock()
    cache.library_keys.return_value = ["eta_generic", "status_done"]
    cache.get_variant_by_key.return_value = cached
    cache.lookup.return_value = None  # keyword-match would miss

    mock_classify = AsyncMock(return_value="eta_generic")
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.classify_intent", mock_classify
    )

    fallback = tmp_path / "standup.wav"
    result = _run(_resolve_auto_response(
        config, "когда же ты это сдашь?", cache, "", fallback
    ))
    assert result == cached_path
    mock_classify.assert_awaited_once()
    cache.get_variant_by_key.assert_called_once_with("eta_generic")
    # Keyword lookup should NOT be called after classifier succeeded
    cache.lookup.assert_not_called()


def test_intent_classifier_miss_falls_through_to_keyword(monkeypatch, tmp_path):
    """intent_classifier=True + classifier returns None → fall to keyword match."""
    config = SaymoConfig()
    config.responses.intent_classifier = True

    cache = MagicMock()
    cache.library_keys.return_value = ["status_done"]
    cache.lookup.return_value = None  # keyword also misses

    mock_classify = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.classify_intent", mock_classify
    )

    fallback = tmp_path / "standup.wav"
    result = _run(_resolve_auto_response(
        config, "как дела по задаче?", cache, "", fallback
    ))
    assert result == fallback
    mock_classify.assert_awaited_once()
    cache.lookup.assert_called_once()


def test_live_fallback_error_returns_standup(monkeypatch):
    """If Ollama throws, fall back to standup — never crash the loop."""
    config = SaymoConfig()
    config.responses.live_fallback = True

    cache = MagicMock()
    cache.lookup.return_value = None

    mock_answer = AsyncMock(side_effect=RuntimeError("ollama down"))
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.answer_question", mock_answer
    )

    fallback = Path("/tmp/standup.wav")
    result = _run(_resolve_auto_response(
        config, "как дела?", cache, "", fallback
    ))
    assert result == fallback

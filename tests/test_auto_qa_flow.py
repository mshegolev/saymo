"""Integration tests for the question-detection and response-resolution
flow used by ``saymo auto`` (cli._resolve_auto_response)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from saymo.cli import _looks_like_question, _resolve_auto_response
from saymo.config import SaymoConfig
from saymo.commands.core import (
    _should_answer_trigger_window,
    _toggle_auto_pause,
    _toggle_manual_takeover,
)


def _run(coro):
    """Run an async coroutine synchronously for tests — pytest-asyncio not installed."""
    return asyncio.run(coro)


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
    "Миша, скажи",
    "hello world",
])
def test_looks_like_question_false(text):
    assert _looks_like_question(text) is False


def test_should_answer_trigger_window_allows_direct_question():
    config = SaymoConfig()

    assert _should_answer_trigger_window(
        config,
        "Миша, что по статусу?",
        ["Миша"],
    ) is True


def test_should_answer_trigger_window_ignores_narrated_mention():
    config = SaymoConfig()

    assert _should_answer_trigger_window(
        config,
        "как Миша вчера говорил, надо проверить логи",
        ["Миша"],
    ) is False


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
        config, "Миша, выйди на связь", cache, "", fallback
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
    config.tts.engine = "macos_say"

    cache = MagicMock()
    cache.lookup.return_value = None

    mock_answer = AsyncMock(return_value="Готово, работаю над задачей")
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.answer_question", mock_answer
    )

    mock_engine = MagicMock()
    mock_engine.synthesize = AsyncMock(return_value=b"RIFF....fake wav bytes")
    monkeypatch.setattr(
        "saymo.tts.factory.get_tts_engine", lambda cfg, **kw: mock_engine
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

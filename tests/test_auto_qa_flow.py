"""Integration tests for the question-detection and response-resolution
flow used by ``saymo auto`` (cli._resolve_auto_response)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from saymo.cli import _looks_like_question, _resolve_auto_response
from saymo.config import SaymoConfig


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

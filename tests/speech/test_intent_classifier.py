"""Tests for saymo.speech.ollama_composer.classify_intent and
ResponseCache.get_variant_by_key / library_keys."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from saymo.analysis.response_cache import (
    ResponseCache, ResponseEntry, build_library,
)
from saymo.speech.ollama_composer import classify_intent


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# ResponseCache.get_variant_by_key
# ---------------------------------------------------------------------------

def test_library_keys_returns_sorted():
    cache = ResponseCache()
    keys = cache.library_keys()
    assert keys == sorted(keys)
    assert "status_generic" in keys  # smoke: default library present


def test_get_variant_by_key_missing_returns_none():
    cache = ResponseCache()
    assert cache.get_variant_by_key("no_such_intent") is None


def test_get_variant_by_key_no_audio_returns_none(tmp_path):
    # Build cache with a known entry but no cached WAVs on disk
    library = build_library({"dummy": {"triggers": ["foo"], "variants": ["bar"]}})
    cache = ResponseCache(library=library, cache_dir=tmp_path)
    assert cache.get_variant_by_key("dummy") is None


def test_get_variant_by_key_returns_cached_path(tmp_path):
    library = build_library({
        "greeting": {
            "triggers": ["привет"],
            "variants": ["Привет, как дела", "Здарова"],
        },
    })
    cache = ResponseCache(library=library, cache_dir=tmp_path)

    # Simulate a pre-synthesised variant on disk
    path = cache._variant_path("greeting", 0, "Привет, как дела")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF.fake")

    result = cache.get_variant_by_key("greeting")
    assert result is not None
    assert result.key == "greeting"
    assert result.audio_path == path
    assert result.confidence == 1.0


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------

def _mock_ollama_response(monkeypatch, raw_text):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": raw_text}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )
    return mock_client


def test_classify_empty_transcript_returns_none():
    assert _run(classify_intent("", ["foo", "bar"])) is None
    assert _run(classify_intent("   ", ["foo"])) is None


def test_classify_no_keys_returns_none():
    assert _run(classify_intent("как дела?", [])) is None


def test_classify_returns_valid_key(monkeypatch):
    _mock_ollama_response(monkeypatch, "status_done")
    result = _run(classify_intent(
        "закончил задачу", ["status_done", "status_generic", "eta_generic"]
    ))
    assert result == "status_done"


def test_classify_strips_punctuation(monkeypatch):
    _mock_ollama_response(monkeypatch, "  eta_generic.\n")
    result = _run(classify_intent("когда сдашь?", ["status_done", "eta_generic"]))
    assert result == "eta_generic"


def test_classify_returns_none_on_none_response(monkeypatch):
    _mock_ollama_response(monkeypatch, "none")
    result = _run(classify_intent("привет как дела", ["status_done"]))
    assert result is None


def test_classify_returns_none_on_unknown_key(monkeypatch):
    _mock_ollama_response(monkeypatch, "something_weird")
    result = _run(classify_intent("как дела", ["status_done", "eta_generic"]))
    assert result is None


def test_classify_timeout_returns_none(monkeypatch):
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=TimeoutError("timeout"))
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )
    result = _run(classify_intent("как дела?", ["status_done"]))
    assert result is None

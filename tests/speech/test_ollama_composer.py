"""Tests for saymo.speech.ollama_composer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import saymo.speech.ollama_composer as composer
from saymo.speech.ollama_composer import (
    _resolve_prompt,
    compose_standup_ollama,
    answer_question,
    check_ollama_health,
)


def _run(coro):
    """Run an async coroutine synchronously — pytest-asyncio not installed."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client(json_return: dict):
    """Build a reusable mock httpx.AsyncClient context manager."""
    mock_response = MagicMock()
    mock_response.json.return_value = json_return
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client, mock_response


# ---------------------------------------------------------------------------
# 1. _resolve_prompt(None, "key", "default") returns default
# ---------------------------------------------------------------------------

def test_resolve_prompt_none_config_returns_default():
    assert _resolve_prompt(None, "standup_ru", "default_text") == "default_text"


# ---------------------------------------------------------------------------
# 2. _resolve_prompt with override from config.prompts["standup_ru"]
# ---------------------------------------------------------------------------

def test_resolve_prompt_returns_config_override():
    config = MagicMock()
    config.prompts = {"standup_ru": "my custom prompt"}
    assert _resolve_prompt(config, "standup_ru", "default_text") == "my custom prompt"


# ---------------------------------------------------------------------------
# 3. _resolve_prompt returns default when key not in config.prompts
# ---------------------------------------------------------------------------

def test_resolve_prompt_missing_key_returns_default():
    config = MagicMock()
    config.prompts = {"other_key": "something else"}
    assert _resolve_prompt(config, "standup_ru", "fallback") == "fallback"


def test_resolve_prompt_empty_prompts_returns_default():
    config = MagicMock()
    config.prompts = {}
    assert _resolve_prompt(config, "standup_ru", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# 4. compose_standup_ollama — mock httpx, verify response and prompt content
# ---------------------------------------------------------------------------

def test_compose_standup_ollama_returns_response_text(monkeypatch):
    mock_client, mock_response = _make_mock_client({"response": "composed text"})
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    notes = {
        "yesterday": "fixed bug in parser",
        "today": "write tests",
        "yesterday_date": "Mon",
        "today_date": "Tue",
    }
    result = _run(compose_standup_ollama(notes))
    assert result == "composed text"


def test_compose_standup_ollama_prompt_contains_notes(monkeypatch):
    """Verify that yesterday_notes and today_notes are present in the prompt sent."""
    captured_calls = []

    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "ok"}
    mock_response.raise_for_status = MagicMock()

    async def fake_post(url, json=None, **kwargs):
        captured_calls.append(json)
        return mock_response

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = fake_post

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    notes = {
        "yesterday": "closed JIRA-123",
        "today": "review PR-456",
        "yesterday_date": "2026-04-21",
        "today_date": "2026-04-22",
    }
    _run(compose_standup_ollama(notes))

    assert len(captured_calls) == 1
    prompt_text = captured_calls[0]["prompt"]
    assert "closed JIRA-123" in prompt_text
    assert "review PR-456" in prompt_text


def test_compose_standup_ollama_english(monkeypatch):
    mock_client, _ = _make_mock_client({"response": "english text"})
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    notes = {"yesterday": "done", "today": "todo"}
    result = _run(compose_standup_ollama(notes, language="en"))
    assert result == "english text"


# ---------------------------------------------------------------------------
# 5. answer_question — mock httpx, verify system_prompt contains user_name and standup_summary
# ---------------------------------------------------------------------------

def test_answer_question_returns_content(monkeypatch):
    mock_client, _ = _make_mock_client(
        {"message": {"content": "working on it"}}
    )
    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    result = _run(answer_question(
        question="what is your status?",
        standup_summary="Fixed the auth bug",
        user_name="Misha",
    ))
    assert result == "working on it"


def test_answer_question_system_prompt_contains_user_name(monkeypatch):
    """Verify the messages payload includes user_name in system content."""
    captured = []

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "answer"}}
    mock_response.raise_for_status = MagicMock()

    async def fake_post(url, json=None, **kwargs):
        captured.append(json)
        return mock_response

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = fake_post

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    _run(answer_question(
        question="any blockers?",
        standup_summary="Summary: no blockers today",
        user_name="Mikhail",
        user_role="QA Engineer",
    ))

    assert len(captured) == 1
    messages = captured[0]["messages"]
    system_content = messages[0]["content"]
    assert "Mikhail" in system_content
    assert "Summary: no blockers today" in system_content


def test_answer_question_includes_conversation_history(monkeypatch):
    captured = []

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "yes"}}
    mock_response.raise_for_status = MagicMock()

    async def fake_post(url, json=None, **kwargs):
        captured.append(json)
        return mock_response

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = fake_post

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    history = [
        {"role": "user", "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
    ]
    _run(answer_question(
        question="follow-up?",
        standup_summary="summary",
        conversation_history=history,
    ))

    messages = captured[0]["messages"]
    # system + history[0] + history[1] + new user message
    assert len(messages) == 4
    assert messages[-1]["content"] == "follow-up?"


# ---------------------------------------------------------------------------
# 6. check_ollama_health — 200 → True; 500 → False; connection error → False
# ---------------------------------------------------------------------------

def test_check_ollama_health_200_returns_true(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    assert _run(check_ollama_health()) is True


def test_check_ollama_health_500_returns_false(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    assert _run(check_ollama_health()) is False


def test_check_ollama_health_connection_error_returns_false(monkeypatch):
    import httpx

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    assert _run(check_ollama_health()) is False


def test_check_ollama_health_generic_exception_returns_false(monkeypatch):
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=OSError("network error"))

    monkeypatch.setattr(
        "saymo.speech.ollama_composer.httpx.AsyncClient",
        lambda **kw: mock_client,
    )

    assert _run(check_ollama_health()) is False

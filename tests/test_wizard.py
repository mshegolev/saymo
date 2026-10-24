"""Tests for setup-wizard helpers and the end-to-end CLI flow."""

from pathlib import Path
from types import SimpleNamespace

import httpx
import yaml
from click.testing import CliRunner

from saymo.commands import main
from saymo.config import load_config
from saymo.wizard import _build_meeting_profile, _trigger_setup_tip


def test_build_meeting_profile_includes_provider_and_trigger_phrases():
    profile = _build_meeting_profile(
        description="Daily standup",
        team=False,
        source="obsidian",
        provider="zoom",
        trigger_phrases=["John", "John Doe"],
    )

    assert profile == {
        "description": "Daily standup",
        "team": False,
        "source": "obsidian",
        "provider": "zoom",
        "trigger_phrases": ["John", "John Doe"],
    }


def test_trigger_setup_tip_points_to_verified_learning_flow():
    tip = _trigger_setup_tip("personal", "John")

    assert "saymo trigger-check -p personal --mic" in tip
    assert 'saymo trigger-setup -p personal --heard "John, what is the status?"' in tip


def test_setup_cli_completes_six_steps_and_saves_config(tmp_path, monkeypatch):
    config_path = tmp_path / "saymo.yaml"
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr("saymo.audio.devices.list_devices", lambda: [])

    def fake_http_get(url, **_kwargs):
        if url.endswith("/api/tags"):
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"models": [{"name": "test-model"}]},
                raise_for_status=lambda: None,
            )
        return SimpleNamespace(
            status_code=200,
            json=lambda: {},
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(httpx, "get", fake_http_get)
    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "setup"],
        input="Test User\n\n\n\n\n\nn\nn\n\n4\n",
    )

    assert result.exit_code == 0, result.output
    for step in (
        "Step 1: Your info",
        "Step 2: Audio devices",
        "Шаг 3: Голосовой сэмпл",
        "Step 4: Meeting profiles",
        "Шаг 5: Ollama (локальная LLM)",
        "Шаг 6: TTS движок",
    ):
        assert step in result.output

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved["user"]["name"] == "Test User"
    assert saved["audio"]["recording_device"] == "MacBook Pro Microphone"
    assert saved["ollama"]["model"] == "test-model"
    assert saved["tts"]["engine"] == "macos_say"

    loaded = load_config(str(config_path))
    assert loaded.user.name == "Test User"
    assert loaded.audio.playback_device == "BlackHole 2ch"
    assert loaded.ollama.model == "test-model"
    assert loaded.tts.engine == "macos_say"

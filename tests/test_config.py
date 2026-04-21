"""Tests for saymo.config — env-var resolution, YAML loading, dataclass conversion."""

import os
import textwrap

import pytest

from saymo.config import (
    AudioConfig,
    SaymoConfig,
    UserConfig,
    _dict_to_dataclass,
    _resolve_dict,
    _resolve_env_vars,
    load_config,
)


# ---------------------------------------------------------------------------
# _resolve_env_vars
# ---------------------------------------------------------------------------

def test_resolve_env_vars_known_variable(monkeypatch):
    monkeypatch.setenv("SAYMO_TEST_TOKEN", "secret123")
    result = _resolve_env_vars("Bearer ${SAYMO_TEST_TOKEN}")
    assert result == "Bearer secret123"


def test_resolve_env_vars_unknown_variable_becomes_empty():
    result = _resolve_env_vars("${NONEXISTENT_VAR_XYZ}")
    assert result == ""


def test_resolve_env_vars_no_placeholder_unchanged():
    result = _resolve_env_vars("plain text")
    assert result == "plain text"


def test_resolve_env_vars_multiple_placeholders(monkeypatch):
    monkeypatch.setenv("SAYMO_HOST", "localhost")
    monkeypatch.setenv("SAYMO_PORT", "8080")
    result = _resolve_env_vars("${SAYMO_HOST}:${SAYMO_PORT}")
    assert result == "localhost:8080"


def test_resolve_env_vars_empty_string():
    assert _resolve_env_vars("") == ""


# ---------------------------------------------------------------------------
# _resolve_dict
# ---------------------------------------------------------------------------

def test_resolve_dict_resolves_nested_string(monkeypatch):
    monkeypatch.setenv("SAYMO_KEY", "value")
    d = {"outer": {"inner": "${SAYMO_KEY}"}}
    result = _resolve_dict(d)
    assert result["outer"]["inner"] == "value"


def test_resolve_dict_resolves_list_items(monkeypatch):
    monkeypatch.setenv("SAYMO_ITEM", "item_value")
    d = {"items": ["${SAYMO_ITEM}", "literal"]}
    result = _resolve_dict(d)
    assert result["items"] == ["item_value", "literal"]


def test_resolve_dict_passes_non_string_values_through():
    d = {"count": 42, "flag": True, "ratio": 3.14}
    result = _resolve_dict(d)
    assert result["count"] == 42
    assert result["flag"] is True
    assert result["ratio"] == pytest.approx(3.14)


def test_resolve_dict_empty_dict():
    assert _resolve_dict({}) == {}


# ---------------------------------------------------------------------------
# load_config — no file
# ---------------------------------------------------------------------------

def test_load_config_no_file_returns_defaults(tmp_path, monkeypatch):
    """When no config file exists anywhere, defaults are returned."""
    # Point home to a temp dir so ~/.saymo/config.yaml does not exist,
    # and run from a dir with no config.yaml.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    cfg = load_config(config_path="/nonexistent/path/config.yaml")
    assert isinstance(cfg, SaymoConfig)
    assert cfg.user.name == "User"
    assert cfg.audio.sample_rate == 16000


def test_load_config_returns_saymo_config_instance():
    cfg = load_config(config_path="/nonexistent/path/does_not_exist.yaml")
    assert isinstance(cfg, SaymoConfig)


# ---------------------------------------------------------------------------
# load_config — with a YAML file
# ---------------------------------------------------------------------------

def test_load_config_populates_user_section(tmp_path):
    yaml_content = textwrap.dedent("""\
        user:
          name: "Иван"
          language: "ru"
          role: "Engineer"
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_content)

    cfg = load_config(config_path=str(cfg_file))
    assert cfg.user.name == "Иван"
    assert cfg.user.language == "ru"
    assert cfg.user.role == "Engineer"


def test_load_config_populates_audio_section(tmp_path):
    yaml_content = textwrap.dedent("""\
        audio:
          sample_rate: 44100
          channels: 2
          capture_device: "BlackHole 2ch"
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_content)

    cfg = load_config(config_path=str(cfg_file))
    assert cfg.audio.sample_rate == 44100
    assert cfg.audio.channels == 2
    assert cfg.audio.capture_device == "BlackHole 2ch"


def test_load_config_resolves_env_vars_in_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("SAYMO_JIRA_TOKEN", "tok-abc")
    yaml_content = textwrap.dedent("""\
        jira:
          token: "${SAYMO_JIRA_TOKEN}"
          url: "https://jira.example.com"
    """)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_content)

    cfg = load_config(config_path=str(cfg_file))
    assert cfg.jira.token == "tok-abc"
    assert cfg.jira.url == "https://jira.example.com"


# ---------------------------------------------------------------------------
# _dict_to_dataclass
# ---------------------------------------------------------------------------

def test_dict_to_dataclass_simple():
    data = {"name": "Alice", "language": "en", "role": "dev"}
    result = _dict_to_dataclass(UserConfig, data)
    assert isinstance(result, UserConfig)
    assert result.name == "Alice"
    assert result.language == "en"


def test_dict_to_dataclass_nested_audio():
    data = {
        "audio": {
            "sample_rate": 22050,
            "channels": 1,
            "capture_device": "Built-in Microphone",
        }
    }
    result = _dict_to_dataclass(SaymoConfig, data)
    assert isinstance(result.audio, AudioConfig)
    assert result.audio.sample_rate == 22050
    assert result.audio.capture_device == "Built-in Microphone"


def test_dict_to_dataclass_partial_keys_use_defaults():
    """Only provided keys are set; the rest keep dataclass defaults."""
    data = {"name": "Bob"}
    result = _dict_to_dataclass(UserConfig, data)
    assert result.name == "Bob"
    assert result.language == "ru"  # default


def test_dict_to_dataclass_unknown_keys_ignored():
    """Extra keys not present in the dataclass must not raise."""
    data = {"name": "Carol", "nonexistent_field": "ignored"}
    result = _dict_to_dataclass(UserConfig, data)
    assert result.name == "Carol"
    assert not hasattr(result, "nonexistent_field")


def test_dict_to_dataclass_empty_dict_uses_all_defaults():
    result = _dict_to_dataclass(AudioConfig, {})
    assert isinstance(result, AudioConfig)
    assert result.sample_rate == 16000

"""Tests for the hotkey config helper script."""

import yaml

from scripts.add_hotkeys import DEFAULT_HOTKEYS, update_hotkeys


def test_update_hotkeys_creates_safety_block_without_clobbering_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "user:\n  name: Миша\nsafety:\n  max_speech_duration: 90\n",
        encoding="utf-8",
    )

    update_hotkeys(
        config_path,
        {
            "hotkey_stop": "<cmd>+<shift>+x",
            "hotkey_takeover": "<cmd>+<shift>+u",
        },
    )

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["user"]["name"] == "Миша"
    assert data["safety"]["max_speech_duration"] == 90
    assert data["safety"]["hotkey_stop"] == "<cmd>+<shift>+x"
    assert data["safety"]["hotkey_takeover"] == "<cmd>+<shift>+u"


def test_default_hotkeys_include_takeover():
    assert DEFAULT_HOTKEYS["hotkey_takeover"] == "<cmd>+<shift>+u"

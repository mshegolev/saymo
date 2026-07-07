"""Tests for the Obsidian daily-note bootstrap helper."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ensure_obsidian_daily_note.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ensure_obsidian_daily_note", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_obsidian_config_reads_home_config(tmp_path):
    module = _load_module()
    home = tmp_path / "home"
    config_dir = home / ".saymo"
    config_dir.mkdir(parents=True)
    config_dir.joinpath("config.yaml").write_text(
        "\n".join(
            [
                "speech:",
                "  source: obsidian",
                "obsidian:",
                "  vault_path: ~/Documents/Obsidian Vault",
                "  subfolder: Daily",
                "  date_format: \"%Y-%m-%d\"",
                "meetings:",
                "  standup:",
                "    provider: glip",
            ]
        ),
        encoding="utf-8",
    )

    config = module.load_obsidian_config(home=home)

    assert config.vault_path == home / "Documents" / "Obsidian Vault"
    assert config.subfolder == "Daily"
    assert config.date_format == "%Y-%m-%d"


def test_ensure_daily_note_creates_missing_note(tmp_path):
    module = _load_module()
    config = module.ObsidianConfig(
        vault_path=tmp_path / "Vault",
        subfolder="",
        date_format="%Y-%m-%d",
    )

    result = module.ensure_daily_note(config, target_date=date(2026, 7, 7))

    note = tmp_path / "Vault" / "2026-07-07.md"
    assert result == note
    assert note.exists()
    text = note.read_text(encoding="utf-8")
    assert "# 2026-07-07" in text
    assert "## Standup" in text
    assert "### Yesterday" in text
    assert "### Today" in text
    assert "### Blockers" in text


def test_ensure_daily_note_preserves_existing_note(tmp_path):
    module = _load_module()
    config = module.ObsidianConfig(
        vault_path=tmp_path / "Vault",
        subfolder="Daily",
        date_format="%Y-%m-%d",
    )
    existing = tmp_path / "Vault" / "Daily" / "2026-07-07.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("already written\n", encoding="utf-8")

    result = module.ensure_daily_note(config, target_date=date(2026, 7, 7))

    assert result == existing
    assert existing.read_text(encoding="utf-8") == "already written\n"

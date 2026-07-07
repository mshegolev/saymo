#!/usr/bin/env python3
"""Create today's Saymo Obsidian daily note if it is missing."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class ObsidianConfig:
    vault_path: Path
    subfolder: str
    date_format: str


def load_obsidian_config(*, home: Path | None = None) -> ObsidianConfig:
    """Load the small Obsidian section Saymo needs from ~/.saymo/config.yaml."""
    root = (home or Path.home()).expanduser()
    config_path = root / ".saymo" / "config.yaml"
    values = _read_obsidian_section(config_path)
    vault_path = _expand_path(values.get("vault_path", ""), home=root)
    if not vault_path:
        raise SystemExit(f"obsidian.vault_path is missing in {config_path}")
    return ObsidianConfig(
        vault_path=vault_path,
        subfolder=values.get("subfolder", ""),
        date_format=values.get("date_format", "%Y-%m-%d"),
    )


def ensure_daily_note(config: ObsidianConfig, *, target_date: date | None = None) -> Path:
    """Create and return the daily note path, preserving existing content."""
    day = target_date or date.today()
    filename = day.strftime(config.date_format) + ".md"
    root = config.vault_path.expanduser()
    target_dir = root / config.subfolder if config.subfolder else root
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / filename
    if note_path.exists():
        return note_path
    note_path.write_text(_daily_note_template(day), encoding="utf-8")
    return note_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Date to create, in YYYY-MM-DD format.")
    args = parser.parse_args(argv)
    target_date = date.fromisoformat(args.date) if args.date else None
    config = load_obsidian_config()
    note_path = ensure_daily_note(config, target_date=target_date)
    print(note_path)
    return 0


def _read_obsidian_section(config_path: Path) -> dict[str, str]:
    if not config_path.exists():
        raise SystemExit(f"Saymo config not found: {config_path}")
    values: dict[str, str] = {}
    in_section = False
    section_indent = 0
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if stripped == "obsidian:":
            in_section = True
            section_indent = indent
            continue
        if in_section and indent <= section_indent:
            break
        if not in_section or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = _strip_yaml_scalar(value)
    return values


def _strip_yaml_scalar(value: str) -> str:
    scalar = value.split("#", 1)[0].strip()
    if len(scalar) >= 2 and scalar[0] == scalar[-1] and scalar[0] in {"'", '"'}:
        return scalar[1:-1]
    return scalar


def _expand_path(value: str, *, home: Path) -> Path:
    if not value:
        return Path()
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value[2:]
    return Path(value).expanduser()


def _daily_note_template(day: date) -> str:
    iso = day.isoformat()
    return (
        f"# {iso}\n\n"
        "## Standup\n\n"
        "### Yesterday\n"
        "- \n\n"
        "### Today\n"
        "- \n\n"
        "### Blockers\n"
        "- \n"
    )


if __name__ == "__main__":
    sys.exit(main())

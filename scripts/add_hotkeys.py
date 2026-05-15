#!/usr/bin/env python3
"""Add or update Saymo hotkeys in ~/.saymo/config.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


DEFAULT_HOTKEYS = {
    "hotkey_speak": "<cmd>+<shift>+s",
    "hotkey_stop": "<cmd>+<shift>+x",
    "hotkey_toggle": "<cmd>+<shift>+m",
    "hotkey_takeover": "<cmd>+<shift>+u",
}


def update_hotkeys(config_path: Path, hotkeys: dict[str, str]) -> Path:
    """Merge hotkeys into the config safety block without clobbering other keys."""
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}

    safety = data.get("safety")
    if not isinstance(safety, dict):
        safety = {}
    safety.update({key: value for key, value in hotkeys.items() if value})
    data["safety"] = safety

    config_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return config_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add or update Saymo global hotkeys in config.yaml.",
    )
    parser.add_argument(
        "--config",
        default="~/.saymo/config.yaml",
        help="Path to Saymo config.yaml",
    )
    parser.add_argument("--speak", default=DEFAULT_HOTKEYS["hotkey_speak"])
    parser.add_argument("--stop", default=DEFAULT_HOTKEYS["hotkey_stop"])
    parser.add_argument("--toggle", default=DEFAULT_HOTKEYS["hotkey_toggle"])
    parser.add_argument("--takeover", default=DEFAULT_HOTKEYS["hotkey_takeover"])
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the safety YAML block without writing the config file",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    hotkeys = {
        "hotkey_speak": args.speak,
        "hotkey_stop": args.stop,
        "hotkey_toggle": args.toggle,
        "hotkey_takeover": args.takeover,
    }

    if args.print_only:
        print(yaml.safe_dump({"safety": hotkeys}, sort_keys=False, allow_unicode=True))
        return 0

    config_path = update_hotkeys(Path(args.config), hotkeys)
    print(f"Updated {config_path}")
    print("Hotkeys:")
    for key, value in hotkeys.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

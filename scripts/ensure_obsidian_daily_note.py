#!/usr/bin/env python3
"""Create today's Saymo Obsidian daily note if it is missing."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from saymo.obsidian.daily_notes import (
    ObsidianConfig,
    _daily_note_template,
    ensure_daily_note,
    load_obsidian_config,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Date to create, in YYYY-MM-DD format.")
    args = parser.parse_args(argv)
    target_date = date.fromisoformat(args.date) if args.date else None
    config = load_obsidian_config()
    note_path = ensure_daily_note(config, target_date=target_date)
    print(note_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

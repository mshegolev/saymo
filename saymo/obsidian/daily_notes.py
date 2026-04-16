"""Read Obsidian daily notes as standup source."""

import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger("saymo.obsidian")


def find_daily_note(
    vault_path: str,
    target_date: date | None = None,
    subfolder: str = "",
    date_format: str = "%Y-%m-%d",
) -> Path | None:
    """Find a daily note file in the Obsidian vault.

    Searches for files matching the date pattern.
    If not found in subfolder, also checks vault root.
    """
    if target_date is None:
        target_date = date.today()

    filename = target_date.strftime(date_format) + ".md"
    vault = Path(vault_path)

    # Check subfolder first (e.g., "Daily Notes/")
    if subfolder:
        path = vault / subfolder / filename
        if path.exists():
            return path

    # Check vault root
    path = vault / filename
    if path.exists():
        return path

    return None


def read_daily_note(
    vault_path: str,
    target_date: date | None = None,
    subfolder: str = "",
    date_format: str = "%Y-%m-%d",
) -> str | None:
    """Read content of a daily note for a given date."""
    path = find_daily_note(vault_path, target_date, subfolder, date_format)
    if path is None:
        logger.warning(f"Daily note not found for {target_date or date.today()}")
        return None

    content = path.read_text(encoding="utf-8")
    logger.info(f"Read daily note: {path} ({len(content)} chars)")
    return content


def read_standup_notes(
    vault_path: str,
    subfolder: str = "",
    date_format: str = "%Y-%m-%d",
) -> dict[str, str | None]:
    """Read today's and yesterday's daily notes for standup context.

    Returns dict with keys 'today' and 'yesterday'.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Skip weekends for "yesterday"
    if today.weekday() == 0:  # Monday
        yesterday = today - timedelta(days=3)  # Friday

    return {
        "today": read_daily_note(vault_path, today, subfolder, date_format),
        "yesterday": read_daily_note(vault_path, yesterday, subfolder, date_format),
        "today_date": today.isoformat(),
        "yesterday_date": yesterday.isoformat(),
    }

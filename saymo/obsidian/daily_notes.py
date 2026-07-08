"""Read and prepare Obsidian daily notes as standup source."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from saymo.config import ObsidianConfig

logger = logging.getLogger("saymo.obsidian")

_PLACEHOLDER_LINES = {"", "-", "TODO", "TBD", "todo", "tbd", "<placeholder>"}


@dataclass(frozen=True)
class DailyNoteReadiness:
    """Privacy-safe readiness summary for one daily note."""

    path: Path
    exists: bool
    line_count: int
    usable_line_count: int
    source_sha256: str
    reason: str


def daily_note_path(
    config: ObsidianConfig,
    target_date: date | None = None,
) -> Path:
    """Return the configured daily-note path without creating it."""
    day = target_date or date.today()
    filename = day.strftime(config.date_format) + ".md"
    root = Path(config.vault_path).expanduser()
    target_dir = root / config.subfolder if config.subfolder else root
    return target_dir / filename


def ensure_daily_note(
    config: ObsidianConfig,
    target_date: date | None = None,
) -> Path:
    """Create and return the daily note path, preserving existing content."""
    day = target_date or date.today()
    note_path = daily_note_path(config, day)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if note_path.exists():
        return note_path
    note_path.write_text(_daily_note_template(day), encoding="utf-8")
    return note_path


def inspect_standup_source(path: Path) -> DailyNoteReadiness:
    """Inspect note presence and usable source lines without exposing content."""
    if not path.exists():
        return DailyNoteReadiness(
            path=path,
            exists=False,
            line_count=0,
            usable_line_count=0,
            source_sha256="",
            reason="missing",
        )

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    usable = 0
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("#"):
            continue
        if line in _PLACEHOLDER_LINES:
            continue
        usable += 1
    return DailyNoteReadiness(
        path=path,
        exists=True,
        line_count=len(lines),
        usable_line_count=usable,
        source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        reason="ready" if usable else "placeholder_only",
    )


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

"""Local handbrake control surface for a running Saymo auto process."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from saymo.analysis.live_control import (
    ACTION_CATALOG,
    ACTION_ORDER,
    append_control_command,
    command_log_path,
    load_live_state,
    state_path,
)


console = Console()
logger = logging.getLogger("saymo.live_control_tui")


KEY_ACTIONS = {
    "a": "toggle_auto_answer",
    "s": "speak",
    "x": "stop",
    "u": "takeover",
    "d": "approved_speak",
    "k": "skip_current",
    "c": "capture_marker",
    "i": "status",
    "h": "hard_disable",
}


def _read_key() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _build_panel(profile: str, base_dir: Path | str | None, status: str) -> Panel:
    snapshot = load_live_state(profile, base_dir=base_dir)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="bold cyan", width=16)
    table.add_column("value")
    if snapshot is None:
        table.add_row("State:", "[yellow]No running saymo auto state detected[/]")
        table.add_row("Auto Answer:", "unknown")
        table.add_row("Speaking:", "unknown")
        table.add_row("Takeover:", "unknown")
        table.add_row("Hotkeys:", "unknown")
    else:
        table.add_row("State:", snapshot.last_action or "ready")
        table.add_row("Auto Answer:", "[green]ON[/]" if snapshot.auto_answer_enabled else "[red]OFF[/]")
        table.add_row("Paused:", "yes" if snapshot.paused else "no")
        table.add_row("Speaking:", "yes" if snapshot.speaking else "no")
        table.add_row("Takeover:", "yes" if snapshot.manual_takeover else "no")
        table.add_row("Hard Disable:", "yes" if snapshot.hard_disabled else "no")
        table.add_row("Hotkeys:", "active" if snapshot.hotkeys_active else "inactive")
        table.add_row("Last Trigger:", snapshot.last_trigger[:80] or "-")
    table.add_row("Status:", f"[bold yellow]{status}[/]")
    table.add_row("Commands:", str(command_log_path(profile, base_dir=base_dir)))
    table.add_row("State file:", str(state_path(profile, base_dir=base_dir)))

    controls = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    controls.add_column("Key", style="cyan", width=6)
    controls.add_column("Control", style="bold")
    controls.add_column("What it does")
    key_by_action = {action: key for key, action in KEY_ACTIONS.items()}
    for action in ACTION_ORDER:
        entry = ACTION_CATALOG[action]
        controls.add_row(key_by_action.get(action, "-"), entry.label, entry.description)

    help_text = Text.from_markup("[cyan]q[/] quit  [cyan]Ctrl+C[/] quit")
    grid = Table.grid(padding=1)
    grid.add_row(table)
    grid.add_row(controls)
    grid.add_row(help_text)
    return Panel(
        grid,
        title=f"[bold]Saymo Live Control Handbrake — {profile}[/]",
        border_style="yellow",
    )


def run_live_control_tui(profile: str, *, base_dir: Path | str | None = None) -> None:
    """Run a terminal button/keyboard control surface."""
    status = "Ready"
    console.clear()
    with Live(
        _build_panel(profile, base_dir, status),
        console=console,
        refresh_per_second=4,
        screen=False,
    ) as live:
        while True:
            try:
                key = _read_key()
            except (EOFError, KeyboardInterrupt):
                break
            if key in {"q", "\x03"}:
                break
            action = KEY_ACTIONS.get(key)
            if action:
                path = append_control_command(
                    profile,
                    action,
                    source="panel",
                    base_dir=base_dir,
                )
                status = f"queued {action} -> {path.name}"
            live.update(_build_panel(profile, base_dir, status))
    console.print("[dim]Bye![/]")

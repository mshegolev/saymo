"""Saymo interactive TUI — control panel for standup automation."""

import asyncio
import logging
import sys
import threading

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from saymo.config import load_config

console = Console()
logger = logging.getLogger("saymo.tui")

HELP_TEXT = """\
[bold]Hotkeys:[/]
  [cyan]p[/] — Prepare (fetch JIRA → compose summary)
  [cyan]s[/] — Speak (voice the prepared summary)
  [cyan]d[/] — Switch output device (cycle)
  [cyan]e[/] — Switch TTS engine (cycle)
  [cyan]t[/] — Test TTS (short phrase)
  [cyan]r[/] — Re-compose (regenerate text)
  [cyan]x[/] — Stop playback
  [cyan]q[/] — Quit
"""

TTS_ENGINES = ["coqui_clone", "piper", "macos_say"]


class SaymoTUI:
    def __init__(self, config_path: str | None = None):
        self.config = load_config(config_path)
        self.output_devices: list[str] = []
        self.current_device_idx: int = 0
        self.current_engine_idx: int = 0
        self.summary_text: str = ""
        self.status: str = "Ready"
        self.is_speaking: bool = False

        self._discover_devices()
        self._sync_engine_idx()

    def _discover_devices(self):
        """Find all output devices."""
        from saymo.audio.devices import list_devices
        self.output_devices = [
            d.name for d in list_devices() if d.max_output_channels > 0
        ]
        # Set current index to match config
        current = self.config.audio.playback_device
        for i, name in enumerate(self.output_devices):
            if current.lower() in name.lower():
                self.current_device_idx = i
                break

    def _sync_engine_idx(self):
        engine = self.config.tts.engine
        for i, e in enumerate(TTS_ENGINES):
            if e == engine:
                self.current_engine_idx = i
                break

    @property
    def current_device(self) -> str:
        if self.output_devices:
            return self.output_devices[self.current_device_idx]
        return "No devices"

    @property
    def current_engine(self) -> str:
        return TTS_ENGINES[self.current_engine_idx]

    def cycle_device(self):
        if self.output_devices:
            self.current_device_idx = (self.current_device_idx + 1) % len(self.output_devices)
            self.config.audio.playback_device = self.current_device
            self.status = f"Device → {self.current_device}"

    def cycle_engine(self):
        self.current_engine_idx = (self.current_engine_idx + 1) % len(TTS_ENGINES)
        self.config.tts.engine = self.current_engine
        self.status = f"Engine → {self.current_engine}"

    def build_panel(self) -> Panel:
        """Build the TUI display panel."""
        # Status table
        tbl = Table(show_header=False, box=None, padding=(0, 2))
        tbl.add_column("key", style="bold cyan", width=12)
        tbl.add_column("value")

        tbl.add_row("Device:", self._device_display())
        tbl.add_row("TTS Engine:", self._engine_display())
        tbl.add_row("Source:", self.config.speech.source)
        tbl.add_row("Status:", f"[bold yellow]{self.status}[/]")
        tbl.add_row("", "")

        if self.summary_text:
            # Truncate for display
            preview = self.summary_text[:300]
            if len(self.summary_text) > 300:
                preview += "..."
            tbl.add_row("Summary:", f"[dim]{preview}[/]")
        else:
            tbl.add_row("Summary:", "[dim](run [cyan]p[/] to prepare)[/]")

        content = Text()
        content.append_text(Text.from_markup(HELP_TEXT))

        grid = Table.grid(padding=1)
        grid.add_row(tbl)
        grid.add_row(content)

        return Panel(
            grid,
            title="[bold]Saymo Control Panel[/]",
            subtitle=f"[dim]{self.config.user.name} | {self.config.speech.language}[/]",
            border_style="blue",
        )

    def _device_display(self) -> str:
        parts = []
        for i, name in enumerate(self.output_devices):
            short = name[:30]
            if i == self.current_device_idx:
                parts.append(f"[bold green]▸ {short}[/]")
            else:
                parts.append(f"[dim]  {short}[/]")
        return "\n".join(parts) if parts else "No devices"

    def _engine_display(self) -> str:
        parts = []
        for i, name in enumerate(TTS_ENGINES):
            if i == self.current_engine_idx:
                parts.append(f"[bold green]▸ {name}[/]")
            else:
                parts.append(f"[dim]  {name}[/]")
        return "  ".join(parts)


def _read_key() -> str:
    """Read a single keypress (Unix)."""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


async def _run_prepare(tui: SaymoTUI):
    """Prepare standup summary."""
    from saymo.jira_source.confluence_tasks import fetch_daily_tasks, tasks_to_notes
    from saymo.speech.ollama_composer import compose_standup_ollama, check_ollama_health

    tui.status = "Fetching JIRA tasks..."

    try:
        daily = await fetch_daily_tasks(tui.config.jira)
    except Exception as e:
        tui.status = f"JIRA error: {e}"
        return

    if not daily.today and not daily.yesterday:
        tui.status = "No tasks found"
        return

    notes = tasks_to_notes(daily)
    count = len(daily.today) + len(daily.yesterday)
    tui.status = f"Found {count} tasks. Composing with Ollama..."

    if not await check_ollama_health(tui.config.ollama.url):
        tui.status = "Ollama not running! Start with: ollama serve"
        return

    try:
        text = await compose_standup_ollama(
            notes,
            model=tui.config.ollama.model,
            ollama_url=tui.config.ollama.url,
            language=tui.config.speech.language,
        )
        tui.summary_text = text
        tui.status = f"Summary ready ({len(text)} chars)"
    except Exception as e:
        tui.status = f"Compose error: {e}"


async def _run_speak(tui: SaymoTUI):
    """Speak the prepared summary."""
    if not tui.summary_text:
        tui.status = "No summary! Press [p] first"
        return

    from saymo.tts.text_normalizer import normalize_for_tts
    text = normalize_for_tts(tui.summary_text)

    tui.is_speaking = True
    tui.status = f"Speaking via {tui.current_engine} → {tui.current_device[:25]}..."

    try:
        if tui.current_engine == "coqui_clone":
            from saymo.tts.coqui_clone import CoquiCloneTTS
            engine = CoquiCloneTTS(language=tui.config.speech.language)
            await engine.synthesize_to_device(text, tui.current_device)
        elif tui.current_engine == "piper":
            from saymo.tts.piper_tts import PiperTTS
            engine = PiperTTS(model_path=tui.config.tts.piper.model_path or None)
            await engine.synthesize_to_device(text, tui.current_device)
        elif tui.current_engine == "macos_say":
            from saymo.tts.macos_say import MacOSSay
            engine = MacOSSay(tui.config.tts.macos_say)
            await engine.synthesize_to_device(text, tui.current_device)

        tui.status = "Done speaking"
    except Exception as e:
        tui.status = f"TTS error: {e}"
    finally:
        tui.is_speaking = False


async def _run_test_tts(tui: SaymoTUI):
    """Quick TTS test."""
    tui.status = f"Testing TTS ({tui.current_engine})..."
    text = "Привет, это тест голоса Saymo."

    try:
        if tui.current_engine == "macos_say":
            from saymo.tts.macos_say import MacOSSay
            engine = MacOSSay(tui.config.tts.macos_say)
            await engine.synthesize_to_device(text, tui.current_device)
        elif tui.current_engine == "piper":
            from saymo.tts.piper_tts import PiperTTS
            engine = PiperTTS(model_path=tui.config.tts.piper.model_path or None)
            await engine.synthesize_to_device(text, tui.current_device)
        elif tui.current_engine == "coqui_clone":
            from saymo.tts.coqui_clone import CoquiCloneTTS
            engine = CoquiCloneTTS(language=tui.config.speech.language)
            await engine.synthesize_to_device(text, tui.current_device)

        tui.status = "Test done"
    except Exception as e:
        tui.status = f"Test error: {e}"


def _stop_playback():
    """Stop all audio playback."""
    import sounddevice as sd
    sd.stop()


def run_tui(config_path: str | None = None):
    """Main TUI entry point."""
    from saymo.utils.logger import setup_logging
    setup_logging(level=logging.WARNING)

    tui = SaymoTUI(config_path)
    loop = asyncio.new_event_loop()
    running = True
    task_future = None

    def run_async_task(coro):
        """Run async task in background thread."""
        nonlocal task_future

        def _runner():
            nonlocal task_future
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro)
            task_future = None

        if task_future and task_future.is_alive():
            tui.status = "Busy... wait or press [x] to stop"
            return
        task_future = threading.Thread(target=_runner, daemon=True)
        task_future.start()

    console.clear()

    with Live(tui.build_panel(), console=console, refresh_per_second=2, screen=False) as live:
        while running:
            try:
                key = _read_key()
            except (EOFError, KeyboardInterrupt):
                break

            if key == "q":
                running = False
            elif key == "p":
                tui.status = "Preparing..."
                live.update(tui.build_panel())
                run_async_task(_run_prepare(tui))
            elif key == "s":
                run_async_task(_run_speak(tui))
            elif key == "d":
                tui.cycle_device()
            elif key == "e":
                tui.cycle_engine()
            elif key == "t":
                run_async_task(_run_test_tts(tui))
            elif key == "r":
                tui.summary_text = ""
                tui.status = "Cleared. Press [p] to re-prepare"
                run_async_task(_run_prepare(tui))
            elif key == "x":
                _stop_playback()
                tui.is_speaking = False
                tui.status = "Stopped"
            elif key == "\x03":  # Ctrl+C
                running = False

            live.update(tui.build_panel())

    # Cleanup
    if task_future and task_future.is_alive():
        _stop_playback()
    console.print("[dim]Bye![/]")

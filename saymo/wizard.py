"""Interactive setup wizard for Saymo."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def run_wizard(config_path: str | None = None):
    """Interactive wizard for first-time setup and meeting configuration."""

    console.print(Panel("[bold]Saymo Setup Wizard[/]", border_style="blue"))
    console.print()

    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config.yaml")

    import yaml

    if Path(config_path).exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        console.print(f"[green]Found existing config: {config_path}[/]\n")
    else:
        config = {}

    # Step 1: User info
    console.print("[bold cyan]Step 1: Your info[/]")
    name = click.prompt("  Your name (как тебя зовут)", default=config.get("user", {}).get("name", ""))
    if not name:
        console.print("[red]Name is required[/]")
        return

    variants = click.prompt(
        "  Name variants (comma-separated, как тебя могут звать)",
        default=", ".join(config.get("user", {}).get("name_variants", [name]))
    )
    name_variants = [v.strip() for v in variants.split(",") if v.strip()]

    lang = click.prompt("  Language (ru/en)", default=config.get("user", {}).get("language", "ru"))

    config.setdefault("user", {})
    config["user"]["name"] = name
    config["user"]["name_variants"] = name_variants
    config["user"]["language"] = lang

    # Step 2: Audio devices
    console.print("\n[bold cyan]Step 2: Audio devices[/]")
    try:
        from saymo.audio.devices import list_devices
        devices = list_devices()
        table = Table(title="Available Devices")
        table.add_column("#")
        table.add_column("Name")
        table.add_column("In/Out")
        for d in devices:
            io_type = []
            if d.max_input_channels > 0:
                io_type.append("IN")
            if d.max_output_channels > 0:
                io_type.append("OUT")
            table.add_row(str(d.index), d.name, "/".join(io_type))
        console.print(table)
    except Exception:
        console.print("[yellow]Could not list audio devices[/]")

    playback = click.prompt(
        "  Playback device (headphones)",
        default=config.get("audio", {}).get("playback_device", "Plantronics Blackwire 3220 Series")
    )
    monitor = click.prompt(
        "  Monitor device (hear yourself)",
        default=config.get("audio", {}).get("monitor_device", playback)
    )

    config.setdefault("audio", {})
    config["audio"]["playback_device"] = playback
    config["audio"]["monitor_device"] = monitor
    config["audio"]["capture_device"] = config["audio"].get("capture_device", "BlackHole 16ch")

    # Step 3: Voice sample
    console.print("\n[bold cyan]Step 3: Voice sample[/]")
    voice_path = Path.home() / ".saymo" / "voice_samples" / "voice_sample.wav"
    if voice_path.exists():
        size_mb = voice_path.stat().st_size / (1024 * 1024)
        console.print(f"  [green]Voice sample exists: {voice_path} ({size_mb:.1f} MB)[/]")
    else:
        console.print("  [yellow]No voice sample found[/]")
        console.print("  Record with: python3 -m saymo record-voice -d 300")

    # Step 4: Meeting profiles
    console.print("\n[bold cyan]Step 4: Meeting profiles[/]")

    meetings = config.get("meetings", {})
    if meetings:
        table = Table(title="Current Meetings")
        table.add_column("Name")
        table.add_column("Team")
        table.add_column("Triggers")
        for mname, mdata in meetings.items():
            if isinstance(mdata, dict):
                triggers = ", ".join(mdata.get("trigger_phrases", [])[:3])
                table.add_row(mname, str(mdata.get("team", False)), triggers + "...")
        console.print(table)

    if click.confirm("  Add/edit a meeting profile?", default=True):
        while True:
            console.print()
            mname = click.prompt("  Meeting name (e.g., standup, scrum, weekly)", default="")
            if not mname:
                break

            existing = meetings.get(mname, {})
            desc = click.prompt("  Description", default=existing.get("description", ""))
            is_team = click.confirm("  Team report? (includes all members)", default=existing.get("team", False))
            source = click.prompt("  Task source (confluence/obsidian/jira)", default=existing.get("source", "confluence"))

            triggers_str = click.prompt(
                "  Trigger phrases (comma-separated)",
                default=", ".join(existing.get("trigger_phrases", name_variants))
            )
            triggers = [t.strip() for t in triggers_str.split(",") if t.strip()]

            meetings[mname] = {
                "description": desc,
                "team": is_team,
                "source": source,
                "trigger_phrases": triggers,
                "glip_url_pattern": "v.ringcentral.com/conf",
            }

            console.print(f"  [green]Meeting '{mname}' configured[/]")

            if not click.confirm("  Add another meeting?", default=False):
                break

    config["meetings"] = meetings

    # Step 5: TTS engine
    console.print("\n[bold cyan]Step 5: TTS engine[/]")
    engines = ["coqui_clone", "piper", "macos_say"]
    current = config.get("tts", {}).get("engine", "coqui_clone")
    for i, e in enumerate(engines):
        marker = " [bold green]← current[/]" if e == current else ""
        console.print(f"  {i+1}. {e}{marker}")

    choice = click.prompt("  Select (1-3)", default=str(engines.index(current) + 1))
    try:
        config.setdefault("tts", {})
        config["tts"]["engine"] = engines[int(choice) - 1]
    except (ValueError, IndexError):
        pass

    # Save
    console.print(f"\n[bold cyan]Saving to {config_path}...[/]")
    with open(config_path, "w") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    console.print("[bold green]Configuration saved![/]\n")

    # Summary
    console.print(Panel(
        f"[bold]Name:[/] {config['user']['name']}\n"
        f"[bold]Meetings:[/] {', '.join(config.get('meetings', {}).keys())}\n"
        f"[bold]TTS:[/] {config['tts']['engine']}\n"
        f"[bold]Playback:[/] {config['audio']['playback_device']}",
        title="Configuration Summary",
        border_style="green",
    ))

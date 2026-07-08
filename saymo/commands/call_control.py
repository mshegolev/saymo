"""Call-control daemon commands."""

from __future__ import annotations

from pathlib import Path

import click

from saymo.analysis.control_daemon import daemon_heartbeat_path, run_control_daemon
from saymo.commands import console, main


@main.command("call-control-daemon")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option(
    "--heartbeat-interval",
    type=float,
    default=2.0,
    show_default=True,
    help="Seconds between heartbeat writes.",
)
@click.option(
    "--base-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Override live-control directory; defaults to ~/.saymo/live_control.",
)
@click.option("--label", default="", help="Override daemon label in heartbeat.")
@click.option(
    "--once",
    is_flag=True,
    help="Write one heartbeat and exit; intended for tests and diagnostics.",
)
@click.pass_context
def call_control_daemon(ctx, profile, heartbeat_interval, base_dir, label, once):
    """Run the foreground call-control daemon for one profile."""
    if heartbeat_interval < 0:
        raise click.ClickException("--heartbeat-interval must be >= 0")
    exit_code = run_control_daemon(
        ctx.obj["config"],
        profile=profile,
        label=label,
        heartbeat_interval_seconds=heartbeat_interval,
        base_dir=base_dir,
        stop_after_heartbeats=1 if once else None,
    )
    console.print(
        f"daemon heartbeat: {daemon_heartbeat_path(profile, base_dir=base_dir)}",
        markup=False,
        soft_wrap=True,
    )
    raise click.exceptions.Exit(exit_code)

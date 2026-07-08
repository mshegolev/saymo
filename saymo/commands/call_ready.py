"""Call-ready launch gate command."""

from __future__ import annotations

import json

import click

from saymo.analysis.launch_readiness import (
    collect_launch_readiness,
    render_launch_readiness,
)
from saymo.commands import console, main


@main.command("call-ready")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option("--provider", default=None, help="Override provider from profile")
@click.option("--prepare", is_flag=True, help="Allow idempotent preparation steps")
@click.option("--json", "json_output", is_flag=True, help="Print JSON output")
@click.pass_context
def call_ready(ctx, profile, provider, prepare, json_output):
    """Check launch readiness for a profile/provider."""
    config = ctx.obj["config"]
    meeting = config.get_meeting(profile)
    resolved_provider = provider or (meeting.provider if meeting else "glip")
    report = collect_launch_readiness(
        config,
        profile=profile,
        provider_name=resolved_provider,
        prepare=prepare,
    )

    if json_output:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False))
    else:
        console.print(render_launch_readiness(report), markup=False)

    raise click.exceptions.Exit(0 if report.ready else 1)

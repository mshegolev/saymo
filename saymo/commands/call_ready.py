"""Call-ready launch gate command."""

from __future__ import annotations

import json
from pathlib import Path

import click

from saymo.analysis.launch_readiness import (
    collect_launch_readiness,
    render_launch_readiness,
    write_launch_readiness_artifact,
)
from saymo.commands import console, main


@main.command("call-ready")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option("--provider", default=None, help="Override provider from profile")
@click.option("--prepare", is_flag=True, help="Allow idempotent preparation steps")
@click.option("--json", "json_output", is_flag=True, help="Print JSON output")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write sanitized JSON artifact to this path",
)
@click.pass_context
def call_ready(ctx, profile, provider, prepare, json_output, output):
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
    artifact_path = write_launch_readiness_artifact(report, output) if output else None

    if json_output:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False))
    else:
        console.print(render_launch_readiness(report), markup=False, soft_wrap=True)
        if artifact_path:
            click.echo(f"artifact: {artifact_path}")

    raise click.exceptions.Exit(0 if report.ready else 1)

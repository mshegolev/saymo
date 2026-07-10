"""Dry-run launch gate command."""

import json
from pathlib import Path

import click

from saymo.analysis.launch_evidence import (
    compare_launch_evidence_paths,
    launch_evidence_comparison_to_json,
    render_launch_evidence_comparison,
)
from saymo.analysis.launch_readiness import (
    collect_launch_readiness,
    render_launch_readiness,
    write_launch_readiness_artifact,
)
from saymo.commands import console, main


@main.command("dry-run")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option("--provider", default=None, help="Override provider from profile")
@click.option("--prepare-source", is_flag=True, help="Create the selected daily note if missing")
@click.option("--json", "json_output", is_flag=True, help="Print JSON output")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write sanitized JSON artifact to this path",
)
@click.pass_context
def dry_run(ctx, profile, provider, prepare_source, json_output, output):
    """Check dry-run launch readiness for a profile/provider."""
    config = ctx.obj["config"]
    meeting = config.get_meeting(profile)
    resolved_provider = provider or (meeting.provider if meeting else "glip")
    report = collect_launch_readiness(
        config,
        profile=profile,
        provider_name=resolved_provider,
        prepare=prepare_source,
        mode="dry-run",
    )
    artifact_path = (
        write_launch_readiness_artifact(report, output, mode="dry-run")
        if output
        else None
    )

    if json_output:
        payload = report.to_dict()
        payload["mode"] = "dry-run"
        click.echo(json.dumps(payload, ensure_ascii=False))
    else:
        console.print(
            render_launch_readiness(report, label="dry-run"),
            markup=False,
            soft_wrap=True,
        )
        if artifact_path:
            click.echo(f"artifact: {artifact_path}")

    raise click.exceptions.Exit(0 if report.ready else 1)


@main.command("dry-run-compare")
@click.option(
    "--current",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--previous",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--json", "json_output", is_flag=True, help="Print JSON output")
def dry_run_compare(current, previous, json_output):
    """Compare two saved dry-run/launch-readiness JSON artifacts."""
    try:
        comparison = compare_launch_evidence_paths(current=current, previous=previous)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise click.ClickException(f"launch evidence unreadable: {exc}") from exc

    if json_output:
        click.echo(
            json.dumps(
                launch_evidence_comparison_to_json(comparison),
                ensure_ascii=False,
            )
        )
    else:
        console.print(
            render_launch_evidence_comparison(comparison),
            markup=False,
            soft_wrap=True,
        )

"""CLI tests for live-control command queue helpers."""

from click.testing import CliRunner

from saymo.commands import main


def test_live_control_action_queues_normalized_command(tmp_path):
    result = CliRunner().invoke(
        main,
        [
            "live-control-action",
            "--profile",
            "daily",
            "--action",
            "skip",
            "--base-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "queued: skip_current" in result.output
    command_log = tmp_path / "daily" / "commands.jsonl"
    assert command_log.exists()
    text = command_log.read_text(encoding="utf-8")
    assert '"action": "skip_current"' in text
    assert '"source": "cli"' in text

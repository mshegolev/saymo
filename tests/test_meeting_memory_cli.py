"""CLI tests for local meeting-memory commands."""

import json
import textwrap

from click.testing import CliRunner

from saymo.analysis.trigger_sessions import start_trigger_session
from saymo.commands import main


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            user:
              name: "John"
              name_variants: ["John"]
            meeting_memory:
              enabled: true
              retain_transcripts: true
              default_window_seconds: 8.0
              summary_max_items: 5
            """
        ),
        encoding="utf-8",
    )
    return config_path


def _write_sample(
    base_dir,
    *,
    profile="daily",
    session_id,
    sequence=1,
    category="asked_to_speak",
    transcript="John, can you share the status?",
):
    sample_dir = base_dir / profile / category
    sample_dir.mkdir(parents=True, exist_ok=True)
    path = sample_dir / f"sample-{sequence}.json"
    path.write_text(
        json.dumps(
            {
                "profile": profile,
                "session_id": session_id,
                "session_name": "daily",
                "session_sequence": sequence,
                "created_at": "2026-05-20T10:00:00",
                "sample_rate": 16000,
                "wav": f"sample-{sequence}.wav",
                "category": category,
                "speaker": "other",
                "answer_decision": "unlabeled",
                "transcript": transcript,
                "trigger": True,
                "question": True,
                "will_answer": category == "asked_to_speak",
                "addressing": "addressed_to_me",
                "reason": "test",
                "rms": 0.01,
                "peak": 0.1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _session_with_sample(tmp_path):
    samples_dir = tmp_path / "samples"
    session = start_trigger_session(
        base_dir=samples_dir,
        profile="daily",
        session_name="daily",
        started_at="2026-05-20T10:00:00",
    )
    _write_sample(samples_dir, session_id=session.session_id)
    return samples_dir, session


def test_meeting_memory_build_command_writes_ledger(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "meeting-memory",
            "build",
            "-p",
            "daily",
            "--session",
            session.session_id,
            "--samples-dir",
            str(samples_dir),
        ],
    )

    assert result.exit_code == 0
    assert "meeting memory: saved" in result.output
    assert "segments: 1" in result.output
    assert (samples_dir / "daily" / "_sessions" / f"{session.session_id}.transcript.json").exists()


def test_meeting_summary_build_missing_outputs_questions(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "meeting-summary",
            "-p",
            "daily",
            "--session",
            session.session_id[:10],
            "--samples-dir",
            str(samples_dir),
            "--build-missing",
        ],
    )

    assert result.exit_code == 0
    assert f"# Meeting Summary: {session.session_id}" in result.output
    assert "John, can you share the" in result.output
    assert "status?" in result.output
    assert "incomplete coverage: 0" in result.output

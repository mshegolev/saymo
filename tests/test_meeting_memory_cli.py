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


def test_meeting_search_command_outputs_citations(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    runner = CliRunner()
    runner.invoke(
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

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "meeting-search",
            "-p",
            "daily",
            "--keyword",
            "status",
            "--samples-dir",
            str(samples_dir),
        ],
    )

    assert result.exit_code == 0
    assert "matches: 1" in result.output
    assert f"{session.session_id}#1@0.0-8.0s" in result.output


def test_meeting_ask_command_outputs_answer_and_citations(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    runner = CliRunner()
    runner.invoke(
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

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "meeting-ask",
            "What is the status?",
            "-p",
            "daily",
            "--samples-dir",
            str(samples_dir),
        ],
    )

    assert result.exit_code == 0
    assert "insufficient evidence: no" in result.output
    assert f"{session.session_id}#1@0.0-8.0s" in result.output


def test_meeting_summary_sanitized_export_omits_audio_names(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    output_path = tmp_path / "summary.md"
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
            session.session_id,
            "--samples-dir",
            str(samples_dir),
            "--build-missing",
            "--sanitized",
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    rendered = output_path.read_text(encoding="utf-8")
    assert "raw audio: omitted" in rendered
    assert "sample-1.wav" not in rendered
    assert "sample-1.json" not in rendered


def test_answer_draft_command_outputs_pending_draft_with_citations(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    output_path = tmp_path / "draft.json"
    runner = CliRunner()
    runner.invoke(
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

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-draft",
            "John, can you share the status?",
            "-p",
            "daily",
            "--session",
            session.session_id,
            "--samples-dir",
            str(samples_dir),
            "--source",
            "none",
            "-o",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "state: pending" in result.output
    assert "confidence:" in result.output
    assert f"{session.session_id}#1@0.0-8.0s" in result.output
    assert output_path.exists()


def _write_answer_draft(runner, config_path, samples_dir, session, output_path):
    return runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-draft",
            "John, can you share the status?",
            "-p",
            "daily",
            "--session",
            session.session_id,
            "--samples-dir",
            str(samples_dir),
            "--source",
            "none",
            "-o",
            str(output_path),
        ],
    )


def test_answer_cockpit_show_and_action_write_audit(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    draft_path = tmp_path / "draft.json"
    runner = CliRunner()
    runner.invoke(
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
    _write_answer_draft(runner, config_path, samples_dir, session, draft_path)

    show = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-cockpit",
            "show",
            "--draft-json",
            str(draft_path),
            "--samples-dir",
            str(samples_dir),
        ],
    )
    action = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-cockpit",
            "action",
            "-p",
            "daily",
            "--session",
            session.session_id,
            "--action",
            "speak",
            "--samples-dir",
            str(samples_dir),
        ],
    )

    assert show.exit_code == 0
    assert "available actions: speak, edit, skip, takeover" in show.output
    assert action.exit_code == 0
    assert "state: approved_to_speak" in action.output
    assert "playback started: no" in action.output
    assert (samples_dir / "daily" / "_sessions" / f"{session.session_id}.answer-audit.jsonl").exists()


def test_answer_audit_list_and_report_are_sanitized(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir, session = _session_with_sample(tmp_path)
    draft_path = tmp_path / "draft.json"
    report_path = tmp_path / "audit.md"
    runner = CliRunner()
    runner.invoke(
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
    _write_answer_draft(runner, config_path, samples_dir, session, draft_path)
    runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-cockpit",
            "show",
            "--draft-json",
            str(draft_path),
            "--samples-dir",
            str(samples_dir),
        ],
    )

    listed = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-audit",
            "list",
            "-p",
            "daily",
            "--session",
            session.session_id,
            "--samples-dir",
            str(samples_dir),
        ],
    )
    reported = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "answer-audit",
            "report",
            "-p",
            "daily",
            "--session",
            session.session_id,
            "--samples-dir",
            str(samples_dir),
            "-o",
            str(report_path),
        ],
    )

    assert listed.exit_code == 0
    assert "events: 1" in listed.output
    assert "type=draft_shown" in listed.output
    assert reported.exit_code == 0
    rendered = report_path.read_text(encoding="utf-8")
    assert "raw audio: omitted" in rendered
    assert "secrets and config values: omitted" in rendered

"""Documentation tests for Phase 40 launch/realtime evidence workflow."""

from __future__ import annotations

from pathlib import Path


DOC_PATH = Path("docs/LAUNCH-REALTIME-EVIDENCE.md")


def test_launch_realtime_evidence_doc_covers_local_workflow_commands():
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8")

    assert (
        "saymo call-ready -p standup --provider glip "
        "--output ~/.saymo/live_control/standup/call-ready.json"
    ) in text
    assert (
        "saymo session-scorecard -p standup --rehearsal <rehearsal.json> "
        "--launch-json ~/.saymo/live_control/standup/call-ready.json "
        "--realtime-jsonl ~/.saymo/live_control/standup/realtime-decisions.jsonl "
        "--json-output <scorecard.json>"
    ) in text
    assert "--launch-readiness" in text
    assert "--realtime" in text
    assert "saymo safety-soak -p standup --scorecard-json <scorecard.json>" in text
    assert "--output" in text
    assert "--json-output" in text


def test_launch_realtime_evidence_doc_states_privacy_and_read_only_limits():
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "local-only" in text
    assert "read-only" in text
    assert "raw transcript" in text
    assert "generated answer" in text
    assert "audio bytes" in text
    assert "does not repair provider state" in text
    assert "does not change audio routes" in text
    assert "live-call smoke" in text

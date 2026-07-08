"""Tests for local live-control handbrake state and commands."""

from saymo.analysis.live_control import (
    ACTION_CATALOG,
    LiveControlSnapshot,
    append_control_audit,
    append_control_command,
    effective_hotkey_bindings,
    load_live_state,
    read_control_commands,
    render_hotkey_table,
    write_live_state,
)
from saymo.config import SaymoConfig


def test_action_catalog_includes_primary_and_expanded_controls():
    assert ACTION_CATALOG["toggle_auto_answer"].primary is True
    assert ACTION_CATALOG["takeover"].hotkey_field == "hotkey_takeover"
    assert ACTION_CATALOG["approved_speak"].hotkey_field == "hotkey_approved_speak"
    assert ACTION_CATALOG["skip_current"].hotkey_field == "hotkey_skip"
    assert ACTION_CATALOG["hard_disable"].hotkey_field == "hotkey_hard_disable"


def test_control_command_log_reads_only_new_commands(tmp_path):
    append_control_command("daily", "stop", source="panel", base_dir=tmp_path)
    commands, offset = read_control_commands("daily", base_dir=tmp_path)

    assert [cmd.action for cmd in commands] == ["stop"]

    append_control_command("daily", "skip", source="hotkey", base_dir=tmp_path)
    commands, _ = read_control_commands("daily", offset=offset, base_dir=tmp_path)

    assert [cmd.action for cmd in commands] == ["skip_current"]
    assert commands[0].source == "hotkey"


def test_live_state_round_trip(tmp_path):
    snapshot = LiveControlSnapshot(
        profile="daily",
        auto_answer_enabled=False,
        paused=True,
        manual_takeover=True,
        last_action="manual_takeover",
    )

    write_live_state("daily", snapshot, base_dir=tmp_path)
    loaded = load_live_state("daily", base_dir=tmp_path)

    assert loaded is not None
    assert loaded.profile == "daily"
    assert loaded.auto_answer_enabled is False
    assert loaded.paused is True
    assert loaded.manual_takeover is True


def test_control_audit_writes_sanitized_state_event(tmp_path):
    previous = LiveControlSnapshot(profile="daily", auto_answer_enabled=True)
    next_state = LiveControlSnapshot(profile="daily", auto_answer_enabled=False)

    path = append_control_audit(
        "daily",
        action="toggle",
        source="hotkey",
        previous_state=previous,
        next_state=next_state,
        result="auto_answer_off",
        base_dir=tmp_path,
    )

    text = path.read_text(encoding="utf-8")
    assert '"action": "toggle_auto_answer"' in text
    assert '"result": "auto_answer_off"' in text
    assert "hotkey" in text


def test_control_audit_accepts_optional_command_and_probe_ids(tmp_path):
    previous = LiveControlSnapshot(profile="daily", auto_answer_enabled=True)
    next_state = LiveControlSnapshot(profile="daily", auto_answer_enabled=True)

    path = append_control_audit(
        "daily",
        action="status",
        source="probe",
        previous_state=previous,
        next_state=next_state,
        result="status_printed",
        command_id="cmd-123",
        probe_id="probe-456",
        payload={"probe_id": "probe-456", "raw_transcript": "private meeting text"},
        base_dir=tmp_path,
    )

    text = path.read_text(encoding="utf-8")
    assert '"command_id": "cmd-123"' in text
    assert '"probe_id": "probe-456"' in text
    assert '"payload": {"probe_id": "probe-456"}' in text
    assert "private meeting text" not in text
    assert '"previous_state"' in text
    assert '"next_state"' in text


def test_effective_hotkey_bindings_and_render_include_expanded_actions():
    config = SaymoConfig()

    bindings = effective_hotkey_bindings(config)
    rendered = render_hotkey_table(config)

    assert bindings["toggle_auto_answer"] == "<cmd>+<shift>+m"
    assert bindings["approved_speak"] == "<cmd>+<shift>+a"
    assert bindings["skip_current"] == "<cmd>+<shift>+k"
    assert "Hard Disable" in rendered
    assert "<cmd>+<shift>+h" in rendered

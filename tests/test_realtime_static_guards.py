"""Static guards for Phase 39 realtime evidence scope."""

from __future__ import annotations

from pathlib import Path


REALTIME_ANALYSIS_FILES = [
    Path("saymo/analysis/realtime_gate.py"),
    Path("saymo/analysis/realtime_policy.py"),
    Path("saymo/analysis/realtime_events.py"),
]

PHASE40_EVIDENCE_FILES = [
    Path("saymo/analysis/launch_readiness.py"),
    Path("saymo/analysis/launch_evidence.py"),
    Path("saymo/analysis/realtime_events.py"),
    Path("saymo/analysis/session_scorecard.py"),
    Path("saymo/analysis/safety_soak.py"),
    Path("saymo/analysis/remediation.py"),
]

PHASE40_NEW_REPORTING_FILES = [
    Path("saymo/analysis/launch_evidence.py"),
    Path("saymo/analysis/realtime_events.py"),
    Path("saymo/analysis/session_scorecard.py"),
    Path("saymo/analysis/safety_soak.py"),
    Path("saymo/analysis/remediation.py"),
]


def _source(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_realtime_evidence_sources_do_not_name_private_payload_fields():
    source = _source(REALTIME_ANALYSIS_FILES)

    for forbidden in (
        "raw_transcript",
        "generated_answer",
        "answer_text",
        "audio_bytes",
        "PRIVATE_",
    ):
        assert forbidden not in source


def test_realtime_analysis_modules_do_not_mutate_provider_or_audio_routes():
    source = _source(REALTIME_ANALYSIS_FILES)

    for forbidden in (
        "activate_meeting(",
        "toggle_mute(",
        "switch_mic(",
        "get_previous_app(",
        "activate_app(",
        "leave_meeting(",
        "play_audio_bytes",
        "play_bytes_to_devices",
        "sd.rec",
        "sounddevice.rec",
        "_write_audio_settings_to_user_config",
        "set_input_volume",
        "bump_input_volume",
        "killall",
        "pkill",
    ):
        assert forbidden not in source


def test_phase40_evidence_modules_do_not_name_private_payload_fields():
    source = _source(PHASE40_EVIDENCE_FILES)

    for forbidden in (
        "raw_transcript",
        "generated_answer",
        "answer_text",
        "audio_bytes",
    ):
        assert forbidden not in source


def test_phase40_new_reporting_modules_do_not_use_private_sentinels():
    source = _source(PHASE40_NEW_REPORTING_FILES)

    assert "PRIVATE_" not in source


def test_phase40_evidence_modules_do_not_mutate_provider_audio_or_launchd():
    source = _source(PHASE40_EVIDENCE_FILES)

    for forbidden in (
        "activate_meeting(",
        "toggle_mute(",
        "switch_mic(",
        "get_previous_app(",
        "activate_app(",
        "leave_meeting(",
        "play_audio_bytes",
        "play_bytes_to_devices",
        "sd.rec",
        "sounddevice.rec",
        "_write_audio_settings_to_user_config",
        "set_input_volume",
        "bump_input_volume",
        "killall",
        "pkill",
        "bootstrap_argv(",
        "bootout_argv(",
        "kickstart_argv(",
        "append_control_command(",
        "run_handbrake_reachability_probe(",
    ):
        assert forbidden not in source


def test_realtime_event_scope_does_not_import_phase_40_reporting():
    source = _source(
        [
            Path("saymo/analysis/realtime_events.py"),
            Path("saymo/analysis/realtime_policy.py"),
            Path("saymo/commands/core.py"),
        ]
    )

    for forbidden in (
        "scorecard",
        "safety-soak",
        "safety_soak",
        "session-scorecard",
        "Launch and Realtime Evidence Feedback",
    ):
        assert forbidden not in source


def test_realtime_event_module_uses_live_control_jsonl_path():
    source = Path("saymo/analysis/realtime_events.py").read_text(encoding="utf-8")

    assert "live_control_dir" in source
    assert "realtime-decisions.jsonl" in source


def test_core_does_not_restore_legacy_automatic_fallback():
    source = Path("saymo/commands/core.py").read_text(encoding="utf-8")

    assert "_resolve_auto_response_decision" not in source
    assert "answer_question(" not in source

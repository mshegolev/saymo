"""RED contracts for dry-run launch evidence loading and comparison."""

from __future__ import annotations

import json

import pytest

from saymo.analysis.launch_evidence import load_launch_evidence


PRIVATE_SENTINELS = (
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_PROMPT_TEXT",
    "PRIVATE_GENERATED_RESPONSE",
    "SECRET_TOKEN",
    "PRIVATE_VOICE_SAMPLE",
    "PRIVATE_TRAINING_DATA",
)


EXPECTED_COMPARISON_KEYS = {
    "current_path",
    "previous_path",
    "status",
    "ready_change",
    "block_delta",
    "warn_delta",
    "resolved_failures",
    "new_failures",
    "blocker_category_deltas",
    "cache_deltas",
    "provider_change",
    "daemon_change",
    "rerun_commands_added",
    "rerun_commands_removed",
    "warnings",
}


def _assert_no_private_content(value) -> None:
    rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    for sentinel in PRIVATE_SENTINELS:
        assert sentinel not in rendered


def _write_launch_artifact(
    tmp_path,
    name,
    *,
    mode="dry-run",
    ready,
    block_count,
    warn_count,
    cache_ready,
    cache_total,
    cache_missing,
    provider_ok,
    daemon_ok,
    failed_labels,
    reruns,
):
    path = tmp_path / name
    failed = set(failed_labels)
    rerun_iter = iter(reruns)

    def rerun_for(label):
        if label not in failed:
            return ""
        return next(rerun_iter, "")

    checks = [
        {
            "key": "response_cache_coverage",
            "label": "response cache coverage",
            "severity": "block",
            "ok": "response cache coverage" not in failed,
            "detail": "cache coverage PRIVATE_TRANSCRIPT",
            "action": "review cache without PRIVATE_PROMPT_TEXT",
            "rerun": rerun_for("response cache coverage"),
            "metadata": {
                "category": "source-data",
                "ready": cache_ready,
                "total": cache_total,
                "missing": cache_missing,
                "stale_reason": "PRIVATE_GENERATED_RESPONSE",
                "raw_transcript": "PRIVATE_TRANSCRIPT",
                "prompt_text": "PRIVATE_PROMPT_TEXT",
                "generated_response_text": "PRIVATE_GENERATED_RESPONSE",
                "audio_bytes": "PRIVATE_GENERATED_RESPONSE",
                "auth_token": "SECRET_TOKEN",
            },
        },
        {
            "key": "provider_meeting_tab",
            "label": "provider meeting tab",
            "severity": "block",
            "ok": provider_ok,
            "detail": "meeting tab missing SECRET_TOKEN",
            "action": "open provider tab without PRIVATE_PROMPT_TEXT",
            "rerun": rerun_for("provider meeting tab"),
            "metadata": {
                "category": "provider",
                "meeting_found": provider_ok,
                "app_running": True,
                "raw_transcript": "PRIVATE_TRANSCRIPT",
            },
        },
        {
            "key": "call_control_daemon",
            "label": "call-control daemon",
            "severity": "block",
            "ok": daemon_ok,
            "detail": "heartbeat stale SECRET_TOKEN",
            "action": "restart helper without PRIVATE_GENERATED_RESPONSE",
            "rerun": rerun_for("call-control daemon"),
            "metadata": {
                "category": "call-control",
                "running": daemon_ok,
                "heartbeat_fresh": daemon_ok,
                "daemon_ok": daemon_ok,
                "classification": "ready" if daemon_ok else "blocked",
                "auth_token": "SECRET_TOKEN",
            },
        },
        {
            "key": "cloned_voice_metadata",
            "label": "cloned voice metadata",
            "severity": "info",
            "ok": True,
            "detail": "voice metadata ready",
            "action": "none",
            "rerun": "",
            "metadata": {
                "category": "voice-cache",
                "selected_engine": "f5tts_clone",
                "voice_profile": "personal",
                "profile_approved": True,
                "reference_fingerprint": "voice-ref-123",
                "voice_sample_path": "PRIVATE_VOICE_SAMPLE",
                "training_data_path": "PRIVATE_TRAINING_DATA",
            },
        },
    ]
    payload = {
        "schema_version": "1.0",
        "evidence_kind": "launch-readiness",
        "mode": mode,
        "artifact_path": str(path),
        "created_at": "2026-07-10T14:20:00Z",
        "profile": "personal",
        "provider": "glip",
        "ready": ready,
        "check_count": len(checks),
        "ready_count": sum(1 for check in checks if check["ok"]),
        "block_count": block_count,
        "warn_count": warn_count,
        "checks": checks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_load_launch_evidence_accepts_dry_run_mode_without_private_content(tmp_path):
    path = _write_launch_artifact(
        tmp_path,
        "dry-run.json",
        ready=False,
        block_count=2,
        warn_count=1,
        cache_ready=1,
        cache_total=3,
        cache_missing=2,
        provider_ok=False,
        daemon_ok=True,
        failed_labels=("response cache coverage", "provider meeting tab"),
        reruns=("saymo dry-run -p personal --provider glip",),
    )

    evidence = load_launch_evidence(path)

    assert evidence.mode == "dry-run"
    assert evidence.profile == "personal"
    assert evidence.provider == "glip"
    assert evidence.ready is False
    assert evidence.check_count == 4
    assert evidence.block_count == 2
    assert evidence.warn_count == 1
    assert evidence.failed_labels == (
        "response cache coverage",
        "provider meeting tab",
    )
    assert evidence.blocker_categories == {
        "provider": 1,
        "source-data": 1,
    }
    assert evidence.cache_counts == {"ready": 1, "total": 3, "missing": 2}
    assert evidence.provider_status["meeting_tab_ok"] is False
    assert evidence.daemon_status["daemon_ok"] is True
    assert evidence.rerun_commands == ("saymo dry-run -p personal --provider glip",)
    _assert_no_private_content(evidence.__dict__)


def test_compare_launch_evidence_paths_reports_improvement_without_private_content(tmp_path):
    from saymo.analysis.launch_evidence import (
        compare_launch_evidence_paths,
        launch_evidence_comparison_to_json,
        render_launch_evidence_comparison,
    )

    previous = _write_launch_artifact(
        tmp_path,
        "previous.json",
        ready=False,
        block_count=3,
        warn_count=1,
        cache_ready=1,
        cache_total=4,
        cache_missing=3,
        provider_ok=False,
        daemon_ok=False,
        failed_labels=(
            "response cache coverage",
            "provider meeting tab",
            "call-control daemon",
        ),
        reruns=(
            "saymo dry-run -p personal --provider glip",
            "saymo call-control-agent status -p personal",
        ),
    )
    current = _write_launch_artifact(
        tmp_path,
        "current.json",
        ready=True,
        block_count=0,
        warn_count=0,
        cache_ready=4,
        cache_total=4,
        cache_missing=0,
        provider_ok=True,
        daemon_ok=True,
        failed_labels=(),
        reruns=(),
    )

    comparison = compare_launch_evidence_paths(current=current, previous=previous)

    assert comparison.status == "improved"
    assert comparison.ready_change == "not_ready_to_ready"
    assert comparison.block_delta == -3
    assert comparison.warn_delta == -1
    assert comparison.resolved_failures == (
        "response cache coverage",
        "provider meeting tab",
        "call-control daemon",
    )
    assert comparison.new_failures == ()
    assert comparison.cache_deltas["ready"] == 3
    assert comparison.cache_deltas["missing"] == -3
    assert comparison.provider_change == "not_ready_to_ready"
    assert comparison.daemon_change == "not_ready_to_ready"
    assert comparison.rerun_commands_added == ()
    assert comparison.rerun_commands_removed == (
        "saymo dry-run -p personal --provider glip",
        "saymo call-control-agent status -p personal",
    )

    payload = launch_evidence_comparison_to_json(comparison)
    assert set(payload) == EXPECTED_COMPARISON_KEYS
    rendered = render_launch_evidence_comparison(comparison)
    assert "dry-run comparison: improved" in rendered
    assert "ready: no -> yes" in rendered
    assert "blocks: -3" in rendered
    assert (
        "resolved: response cache coverage, provider meeting tab, call-control daemon"
        in rendered
    )
    _assert_no_private_content(payload)
    _assert_no_private_content(rendered)


def test_compare_launch_evidence_paths_reports_regression_and_mixed_states(tmp_path):
    from saymo.analysis.launch_evidence import compare_launch_evidence_paths

    ready = _write_launch_artifact(
        tmp_path,
        "ready.json",
        ready=True,
        block_count=0,
        warn_count=0,
        cache_ready=4,
        cache_total=4,
        cache_missing=0,
        provider_ok=True,
        daemon_ok=True,
        failed_labels=(),
        reruns=(),
    )
    regressed = _write_launch_artifact(
        tmp_path,
        "regressed.json",
        ready=False,
        block_count=1,
        warn_count=0,
        cache_ready=3,
        cache_total=4,
        cache_missing=1,
        provider_ok=True,
        daemon_ok=True,
        failed_labels=("response cache coverage",),
        reruns=("saymo dry-run -p personal --provider glip",),
    )
    mixed = _write_launch_artifact(
        tmp_path,
        "mixed.json",
        ready=False,
        block_count=1,
        warn_count=0,
        cache_ready=4,
        cache_total=4,
        cache_missing=0,
        provider_ok=False,
        daemon_ok=True,
        failed_labels=("provider meeting tab",),
        reruns=("saymo dry-run -p personal --provider glip",),
    )

    regression = compare_launch_evidence_paths(current=regressed, previous=ready)
    mixed_result = compare_launch_evidence_paths(current=mixed, previous=regressed)

    assert regression.status == "regressed"
    assert regression.ready_change == "ready_to_not_ready"
    assert regression.new_failures == ("response cache coverage",)
    assert mixed_result.status == "mixed"
    assert mixed_result.cache_deltas["missing"] == -1
    assert mixed_result.provider_change == "ready_to_not_ready"


def test_compare_launch_evidence_paths_rejects_missing_or_invalid_artifacts_with_clear_error(tmp_path):
    from saymo.analysis.launch_evidence import compare_launch_evidence_paths

    valid = _write_launch_artifact(
        tmp_path,
        "valid.json",
        ready=True,
        block_count=0,
        warn_count=0,
        cache_ready=4,
        cache_total=4,
        cache_missing=0,
        provider_ok=True,
        daemon_ok=True,
        failed_labels=(),
        reruns=(),
    )
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not valid json\n", encoding="utf-8")

    with pytest.raises((FileNotFoundError, ValueError, json.JSONDecodeError), match="launch|evidence|not found|invalid"):
        compare_launch_evidence_paths(current=tmp_path / "missing.json", previous=valid)
    with pytest.raises((ValueError, json.JSONDecodeError), match="launch|evidence|invalid|unreadable"):
        compare_launch_evidence_paths(current=valid, previous=invalid)

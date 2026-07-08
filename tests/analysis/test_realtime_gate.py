"""Tests for realtime startup launch gating."""

from __future__ import annotations

from saymo.analysis.launch_readiness import (
    LaunchReadinessCheck,
    LaunchReadinessReport,
)
from saymo.analysis.realtime_gate import (
    evaluate_realtime_launch_gate,
    render_realtime_launch_block,
)
from saymo.config import SaymoConfig


def _report(*, ready: bool, provider: str = "glip") -> LaunchReadinessReport:
    return LaunchReadinessReport(
        profile="standup",
        provider=provider,
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="block",
                ok=ready,
                detail="ready" if ready else "placeholder_only",
                action="" if ready else "Add usable standup content",
                rerun="" if ready else f"saymo call-ready -p standup --provider {provider}",
            ),
        ),
    )


def test_realtime_launch_gate_resolves_profile_provider_and_uses_shared_readiness(
    monkeypatch,
):
    import saymo.analysis.realtime_gate as realtime_gate

    config = SaymoConfig()
    config.meetings = {
        "standup": {
            "description": "Daily",
            "provider": "zoom",
            "team": False,
            "source": "obsidian",
        }
    }
    calls = []
    ready_report = _report(ready=True, provider="zoom")

    def fake_collect(config_arg, *, profile, provider_name, prepare):
        calls.append((config_arg, profile, provider_name, prepare))
        return ready_report

    monkeypatch.setattr(realtime_gate, "collect_launch_readiness", fake_collect)

    gate = evaluate_realtime_launch_gate(config, profile="standup")

    assert gate.allowed is True
    assert gate.reason == "launch-readiness-ready"
    assert gate.profile == "standup"
    assert gate.provider == "zoom"
    assert gate.report is ready_report
    assert calls == [(config, "standup", "zoom", False)]


def test_realtime_launch_gate_blocks_when_shared_readiness_blocks(monkeypatch):
    import saymo.analysis.realtime_gate as realtime_gate

    config = SaymoConfig()
    blocked_report = _report(ready=False, provider="teams")

    monkeypatch.setattr(
        realtime_gate,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare: blocked_report,
    )

    gate = evaluate_realtime_launch_gate(
        config,
        profile="standup",
        provider_name="teams",
    )

    assert gate.allowed is False
    assert gate.reason == "launch-readiness-blocked"
    assert gate.profile == "standup"
    assert gate.provider == "teams"
    assert gate.report is blocked_report


def test_render_realtime_launch_block_reuses_call_ready_remediation():
    import saymo.analysis.realtime_gate as realtime_gate

    report = _report(ready=False, provider="glip")
    gate = realtime_gate.RealtimeLaunchGate(
        profile="standup",
        provider="glip",
        allowed=False,
        reason="launch-readiness-blocked",
        report=report,
    )

    rendered = render_realtime_launch_block(gate)

    assert "call-ready: not ready" in rendered
    assert "remediation:" in rendered
    assert "- [source-data] daily note source ready" in rendered
    assert "realtime: blocked (launch-readiness-blocked)" in rendered

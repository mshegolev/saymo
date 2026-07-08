"""Tests for realtime startup launch gating."""

from __future__ import annotations

from saymo.analysis.launch_readiness import (
    LaunchReadinessCheck,
    LaunchReadinessReport,
)
from saymo.analysis.realtime_gate import (
    automatic_handbrake_block,
    evaluate_realtime_launch_gate,
    provider_playback_block,
    RealtimePlaybackBlock,
    render_realtime_launch_block,
)
from saymo.config import SaymoConfig


class _Flag:
    def __init__(self, value: bool = False):
        self.value = value

    def is_set(self) -> bool:
        return self.value


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


def test_automatic_handbrake_block_returns_stable_reasons():
    assert isinstance(
        automatic_handbrake_block(_Flag(True), _Flag(True), _Flag(False)),
        RealtimePlaybackBlock,
    )

    cases = [
        (_Flag(True), _Flag(True), _Flag(False), "manual-takeover"),
        (_Flag(True), _Flag(False), _Flag(True), "hard-disabled"),
        (_Flag(False), _Flag(False), _Flag(False), "auto-answer-off"),
    ]

    for auto_answer_enabled, manual_takeover, hard_disabled, reason in cases:
        block = automatic_handbrake_block(
            auto_answer_enabled,
            manual_takeover,
            hard_disabled,
        )

        assert block is not None
        assert block.label == "handbrake-blocked"
        assert block.reason == reason
        assert "private" not in block.detail.lower()


def test_automatic_handbrake_block_allows_enabled_automatic_state():
    assert automatic_handbrake_block(_Flag(True), _Flag(False), _Flag(False)) is None


def test_provider_playback_block_reports_missing_provider_tab():
    class Provider:
        name = "FakeMeet"

        def check_ready(self):
            return type("Status", (), {"meeting_found": False})()

    block = provider_playback_block(Provider())

    assert block is not None
    assert block.label == "provider-blocked"
    assert block.reason == "meeting-not-found"
    assert block.detail == "FakeMeet"


def test_provider_playback_block_sanitizes_readiness_exceptions():
    class Provider:
        name = "FakeMeet"

        def check_ready(self):
            raise RuntimeError("raw chrome tab title and private meeting text")

    block = provider_playback_block(Provider())

    assert block is not None
    assert block.label == "provider-blocked"
    assert block.reason == "provider-check-error"
    assert block.detail == "RuntimeError"
    assert "private meeting text" not in block.detail


def test_provider_playback_block_allows_ready_provider():
    class Provider:
        name = "FakeMeet"

        def check_ready(self):
            return type("Status", (), {"meeting_found": True})()

    assert provider_playback_block(Provider()) is None

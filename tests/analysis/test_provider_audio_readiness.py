"""Tests for provider/audio launch-readiness checks."""

from __future__ import annotations

import json
import textwrap
from unittest.mock import MagicMock

from saymo.config import load_config
from saymo.providers.base import MeetingStatus


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            user:
              name: "John"
              name_variants:
                - "John"
            meetings:
              standup:
                description: "Standup"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
            responses:
              enabled: true
              cache_dir: "{tmp_path / 'responses'}"
              library: {{}}
            """
        ),
        encoding="utf-8",
    )
    return config_path


def _config(tmp_path):
    return load_config(config_path=str(_write_config(tmp_path)))


def _provider(*, status: MeetingStatus | None = None):
    provider = MagicMock()
    provider.name = "glip"
    provider.url_pattern = "app.glip.com"
    provider.check_ready.return_value = status or MeetingStatus(
        app_running=True,
        meeting_found=True,
        tab_info=(1, 2),
    )
    return provider


def _assert_provider_mutators_not_called(provider):
    provider.activate_meeting.assert_not_called()
    provider.toggle_mute.assert_not_called()
    provider.switch_mic.assert_not_called()
    provider.get_previous_app.assert_not_called()
    provider.activate_app.assert_not_called()


def test_provider_tab_readiness_reports_found_missing_and_errors(tmp_path, monkeypatch):
    from saymo.analysis.provider_audio_readiness import collect_provider_tab_check
    import saymo.providers.factory as provider_factory

    config = _config(tmp_path)
    found_provider = _provider()
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: found_provider)

    found = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert found.key == "provider_meeting_tab"
    assert found.label == "provider meeting tab"
    assert found.severity == "block"
    assert found.ok is True
    assert found.detail == "meeting_found"
    assert found.metadata["category"] == "provider"
    assert found.metadata["provider_name"] == "glip"
    assert found.metadata["configured_provider"] == "glip"
    assert found.metadata["url_pattern"] == "app.glip.com"
    assert found.metadata["meeting_found"] is True
    assert found.metadata["app_running"] is True
    assert found.metadata["tab_info"] == [1, 2]

    missing_provider = _provider(
        status=MeetingStatus(
            app_running=True,
            meeting_found=False,
            tab_info=None,
        )
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: missing_provider)

    missing = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert missing.key == "provider_meeting_tab"
    assert missing.severity == "block"
    assert missing.ok is False
    assert missing.detail == "meeting_tab_not_found"
    assert missing.action == "Open the glip meeting in Chrome"
    assert missing.rerun == "saymo call-ready -p standup --provider glip"
    assert missing.metadata["meeting_found"] is False
    assert missing.metadata["tab_info"] is None

    def raise_unknown(name):
        raise ValueError("Unknown provider: unknown. Available: glip")

    monkeypatch.setattr(provider_factory, "get_provider", raise_unknown)

    unknown = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="unknown",
    )

    assert unknown.key == "provider_meeting_tab"
    assert unknown.severity == "block"
    assert unknown.ok is False
    assert unknown.detail == "unknown_provider"
    assert unknown.action == "Use a supported provider name, then rerun saymo call-ready"
    assert unknown.rerun == "saymo call-ready -p standup --provider unknown"
    assert unknown.metadata["configured_provider"] == "unknown"
    assert unknown.metadata["provider_name"] == "unknown"
    assert unknown.metadata["error_type"] == "ValueError"

    def raise_factory_error(name):
        raise RuntimeError("SECRET_TOKEN factory denied")

    monkeypatch.setattr(provider_factory, "get_provider", raise_factory_error)

    factory_error = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert factory_error.key == "provider_meeting_tab"
    assert factory_error.severity == "block"
    assert factory_error.ok is False
    assert factory_error.detail == "provider_check_error"
    assert factory_error.action == (
        "Open Chrome, allow provider automation permissions, then rerun saymo call-ready"
    )
    assert factory_error.rerun == "saymo call-ready -p standup --provider glip"
    assert factory_error.metadata["error_type"] == "RuntimeError"
    assert "SECRET_TOKEN" not in json.dumps(factory_error.to_dict(), ensure_ascii=False)

    check_error_provider = _provider()
    check_error_provider.check_ready.side_effect = RuntimeError(
        "SECRET_TOKEN check denied"
    )
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: check_error_provider)

    check_error = collect_provider_tab_check(
        config,
        profile="standup",
        provider_name="glip",
    )

    assert check_error.key == "provider_meeting_tab"
    assert check_error.severity == "block"
    assert check_error.ok is False
    assert check_error.detail == "provider_check_error"
    assert check_error.rerun == "saymo call-ready -p standup --provider glip"
    assert check_error.metadata["error_type"] == "RuntimeError"
    assert "SECRET_TOKEN" not in json.dumps(check_error.to_dict(), ensure_ascii=False)


def test_collect_provider_audio_checks_is_non_destructive(tmp_path, monkeypatch):
    from saymo.analysis.provider_audio_readiness import collect_provider_audio_checks
    import saymo.providers.factory as provider_factory

    provider = _provider()
    monkeypatch.setattr(provider_factory, "get_provider", lambda name: provider)

    checks = collect_provider_audio_checks(
        _config(tmp_path),
        profile="standup",
        provider_name="glip",
    )

    assert isinstance(checks, tuple)
    assert checks[0].key == "provider_meeting_tab"
    provider.check_ready.assert_called_once_with()
    _assert_provider_mutators_not_called(provider)

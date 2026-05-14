"""Tests for setup-wizard helper logic."""

from saymo.wizard import _build_meeting_profile


def test_build_meeting_profile_includes_provider_and_trigger_phrases():
    profile = _build_meeting_profile(
        description="Daily standup",
        team=False,
        source="obsidian",
        provider="zoom",
        trigger_phrases=["Миша", "Михаил"],
    )

    assert profile == {
        "description": "Daily standup",
        "team": False,
        "source": "obsidian",
        "provider": "zoom",
        "trigger_phrases": ["Миша", "Михаил"],
    }

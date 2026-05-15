"""Tests for setup-wizard helper logic."""

from saymo.wizard import _build_meeting_profile, _trigger_setup_tip


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


def test_trigger_setup_tip_points_to_verified_learning_flow():
    tip = _trigger_setup_tip("personal", "Миша")

    assert "saymo trigger-check -p personal --mic" in tip
    assert 'saymo trigger-setup -p personal --heard "Миша, what is the status?"' in tip

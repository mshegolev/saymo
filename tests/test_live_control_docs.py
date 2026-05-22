"""Docs checks for live-control operator guidance."""

from pathlib import Path


def test_live_control_guide_explains_terminal_focus_and_accessibility():
    text = Path("docs/LIVE-CONTROL-HANDBRAKE.md").read_text(encoding="utf-8")

    assert "terminal window to be focused" in text
    assert "running Saymo process" in text
    assert "Accessibility permission" in text
    assert "saymo live-control -p personal" in text
    assert "Hard Disable" in text

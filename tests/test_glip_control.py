"""Tests for generic AppleScript helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_run_applescript_strict_mode_exposes_permission_errors(monkeypatch):
    from saymo.glip_control import AppleScriptError, _run_applescript

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Not authorized to send Apple events to Google Chrome",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    assert _run_applescript("return 1") == ""
    with pytest.raises(AppleScriptError) as excinfo:
        _run_applescript("return 1", raise_on_error=True)

    assert excinfo.value.returncode == 1
    assert "Not authorized" in str(excinfo.value)

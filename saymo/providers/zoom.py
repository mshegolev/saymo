"""Zoom call provider — placeholder for future implementation.

Zoom uses a native macOS app (not Chrome), so automation will differ:
- AppleScript to find Zoom window
- Cmd+Shift+A for mute toggle (Zoom hotkey)
- Zoom API or accessibility for mic switch
"""

import logging

from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.zoom")


class ZoomProvider:
    """Zoom provider — NOT YET IMPLEMENTED."""

    name = "zoom"

    def check_ready(self) -> MeetingStatus:
        # TODO: Check if Zoom.us is running and in a meeting
        logger.warning("Zoom provider not yet implemented")
        return MeetingStatus()

    def activate_meeting(self) -> bool:
        # TODO: Activate Zoom window
        return False

    def toggle_mute(self) -> None:
        # Zoom uses Cmd+Shift+A for mute toggle
        from saymo.glip_control import _run_applescript
        _run_applescript('''
        tell application "System Events"
            keystroke "a" using {command down, shift down}
        end tell
        ''')

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        # TODO: Zoom mic switching via accessibility or API
        logger.warning("Zoom mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

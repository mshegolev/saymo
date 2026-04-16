"""Telegram call provider — native app (Telegram.app).

Telegram uses native macOS app for calls.
Mute toggle: space bar or microphone button during call.
"""

import logging
from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.telegram")


class TelegramProvider:
    """Telegram calls — NOT YET IMPLEMENTED."""

    name = "telegram"
    app_name = "Telegram"

    def check_ready(self) -> MeetingStatus:
        from saymo.glip_control import _run_applescript
        result = _run_applescript(f'''
        tell application "System Events"
            return (name of processes) contains "{self.app_name}"
        end tell
        ''')
        return MeetingStatus(app_running=result == "true")

    def activate_meeting(self) -> bool:
        from saymo.glip_control import _run_applescript
        _run_applescript(f'''
        tell application "{self.app_name}" to activate
        ''')
        return True

    def toggle_mute(self) -> None:
        from saymo.glip_control import _run_applescript
        _run_applescript('''
        tell application "System Events"
            keystroke " "
        end tell
        ''')

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning("Telegram mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

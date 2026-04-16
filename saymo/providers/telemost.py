"""Yandex Telemost call provider — browser-based (telemost.yandex.ru).

Runs in browser. Mute toggle: microphone button or 'M' hotkey.
"""

import logging
from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.telemost")


class TelemostProvider:
    """Yandex Telemost — NOT YET IMPLEMENTED."""

    name = "telemost"
    url_pattern = "telemost.yandex.ru"
    mute_hotkey = "m"  # Telemost uses 'M' for mute toggle

    def check_ready(self) -> MeetingStatus:
        from saymo.glip_control import _run_applescript
        result = _run_applescript(f'''
        tell application "Google Chrome"
            repeat with w from 1 to (count of windows)
                repeat with t from 1 to (count of tabs of window w)
                    if URL of tab t of window w contains "{self.url_pattern}" then
                        return (w as text) & "," & (t as text)
                    end if
                end repeat
            end repeat
        end tell
        return "not_found"
        ''')
        found = result and result != "not_found"
        tab = None
        if found:
            parts = result.split(",")
            tab = (int(parts[0]), int(parts[1]))
        return MeetingStatus(app_running=True, meeting_found=found, tab_info=tab)

    def activate_meeting(self) -> bool:
        status = self.check_ready()
        if not status.tab_info:
            return False
        w, t = status.tab_info
        from saymo.glip_control import _run_applescript
        _run_applescript(f'''
        tell application "Google Chrome"
            activate
            set active tab index of window {w} to {t}
            set index of window {w} to 1
        end tell
        ''')
        return True

    def toggle_mute(self) -> None:
        from saymo.glip_control import _run_applescript
        _run_applescript(f'''
        tell application "System Events"
            keystroke "{self.mute_hotkey}"
        end tell
        ''')

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning("Telemost mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

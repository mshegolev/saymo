"""Google Meet call provider — browser-based (meet.google.com).

Mute toggle: Cmd+D (Google Meet hotkey).
"""

import logging
from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.google_meet")


class GoogleMeetProvider:
    """Google Meet — NOT YET IMPLEMENTED."""

    name = "google_meet"
    url_pattern = "meet.google.com"

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
        # Google Meet: Cmd+D toggles mute
        _run_applescript('''
        tell application "System Events"
            keystroke "d" using {command down}
        end tell
        ''')

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning("Google Meet mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

"""Microsoft Teams call provider.

Native app (Microsoft Teams.app) or browser (teams.microsoft.com).
Mute toggle: Cmd+Shift+M (native app) or Ctrl+Shift+M (browser).
"""

import logging
from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.ms_teams")


class MSTeamsProvider:
    """Microsoft Teams — NOT YET IMPLEMENTED."""

    name = "ms_teams"
    app_name = "Microsoft Teams"
    url_pattern = "teams.microsoft.com"

    def check_ready(self) -> MeetingStatus:
        from saymo.glip_control import _run_applescript
        # Check native app first
        result = _run_applescript(f'''
        tell application "System Events"
            return (name of processes) contains "{self.app_name}"
        end tell
        ''')
        if result == "true":
            return MeetingStatus(app_running=True, meeting_found=True)

        # Check browser
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
        return MeetingStatus(app_running=found, meeting_found=found, tab_info=tab)

    def activate_meeting(self) -> bool:
        from saymo.glip_control import _run_applescript
        _run_applescript(f'''
        tell application "{self.app_name}" to activate
        ''')
        return True

    def toggle_mute(self) -> None:
        from saymo.glip_control import _run_applescript
        # Teams: Cmd+Shift+M
        _run_applescript('''
        tell application "System Events"
            keystroke "m" using {command down, shift down}
        end tell
        ''')

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning("MS Teams mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

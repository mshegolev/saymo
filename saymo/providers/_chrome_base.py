"""Base class for all browser-based (Chrome) call providers.

All providers work through Chrome tabs. Only url_pattern and mute_key differ.
"""

import logging

from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers")


class ChromeCallProvider:
    """Base for any call provider that runs in Chrome.

    Subclasses only need to set: name, url_pattern, mute_key, mute_modifiers.
    """

    name: str = ""
    url_pattern: str = ""
    mute_key: str = " "  # Space by default
    mute_modifiers: str = ""  # e.g., "command down, shift down"

    def check_ready(self) -> MeetingStatus:
        from saymo.glip_control import _run_applescript
        result = _run_applescript(f'''
        tell application "Google Chrome"
            set windowCount to count of windows
            repeat with w from 1 to windowCount
                set tabCount to count of tabs of window w
                repeat with t from 1 to tabCount
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
        return MeetingStatus(
            app_running=True,
            meeting_found=found,
            tab_info=tab,
        )

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
        delay 0.5
        ''')
        logger.info(f"Activated {self.name} tab (window {w}, tab {t})")
        return True

    def toggle_mute(self) -> None:
        from saymo.glip_control import _run_applescript
        if self.mute_modifiers:
            script = f'''
            tell application "System Events"
                keystroke "{self.mute_key}" using {{{self.mute_modifiers}}}
            end tell
            '''
        else:
            script = f'''
            tell application "System Events"
                keystroke "{self.mute_key}"
            end tell
            '''
        _run_applescript(script)
        logger.info(f"Toggled mute ({self.name})")

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning(f"{self.name} mic auto-switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

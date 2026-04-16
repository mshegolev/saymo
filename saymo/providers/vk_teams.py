"""VK Teams (ex-VK WorkSpace, ex-MyTeam) call provider.

Native app (VK Teams.app) or browser. Mute: Cmd+Shift+M.
"""

import logging
from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.vk_teams")


class VKTeamsProvider:
    """VK Teams — NOT YET IMPLEMENTED."""

    name = "vk_teams"
    app_name = "VK Teams"
    mute_hotkey_modifiers = "command down, shift down"
    mute_hotkey_key = "m"

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
        _run_applescript(f'''
        tell application "System Events"
            keystroke "{self.mute_hotkey_key}" using {{{self.mute_hotkey_modifiers}}}
        end tell
        ''')

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning("VK Teams mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

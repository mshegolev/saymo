"""Glip (RingCentral Video) call provider — Chrome-based automation."""

import logging

from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.glip")

# Re-export existing glip_control functions as a CallProvider
from saymo.glip_control import (
    find_glip_tab,
    activate_glip_tab,
    press_space,
    get_previous_app,
    activate_app,
    check_glip_ready,
    switch_rc_mic_to_blackhole,
    unmute_speak_mute,
)


class GlipProvider:
    """Glip/RingCentral Video provider via Chrome + AppleScript."""

    name = "glip"

    def check_ready(self) -> MeetingStatus:
        status = check_glip_ready()
        return MeetingStatus(
            app_running=status["chrome_running"],
            meeting_found=status["glip_tab_found"],
            tab_info=status["tab_info"],
            mic_is_correct=status.get("mic_is_blackhole", False),
        )

    def activate_meeting(self) -> bool:
        return activate_glip_tab()

    def toggle_mute(self) -> None:
        press_space()

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        return switch_rc_mic_to_blackhole()

    def get_previous_app(self) -> str:
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        activate_app(app_name)


# Singleton instance
glip_provider = GlipProvider()

"""MTS Link call provider — placeholder for future implementation.

MTS Link (formerly Webinar.ru) runs in browser, similar to Glip.
Automation approach will be similar: Chrome + JS injection.
"""

import logging

from saymo.providers.base import MeetingStatus

logger = logging.getLogger("saymo.providers.mts_link")


class MTSLinkProvider:
    """MTS Link provider — NOT YET IMPLEMENTED."""

    name = "mts_link"

    def check_ready(self) -> MeetingStatus:
        # TODO: Check Chrome for MTS Link tab (lk.mts-link.ru or similar)
        logger.warning("MTS Link provider not yet implemented")
        return MeetingStatus()

    def activate_meeting(self) -> bool:
        return False

    def toggle_mute(self) -> None:
        # TODO: Find mute button in MTS Link UI
        pass

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        logger.warning("MTS Link mic switch not yet implemented")
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import get_previous_app
        return get_previous_app()

    def activate_app(self, app_name: str) -> None:
        from saymo.glip_control import activate_app
        activate_app(app_name)

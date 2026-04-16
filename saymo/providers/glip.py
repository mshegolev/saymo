"""Glip (RingCentral Video) — browser (v.ringcentral.com/conf). Mute: Space.

Extended with JS-based mic switching specific to RingCentral Video UI.
"""

from saymo.providers._chrome_base import ChromeCallProvider
from saymo.glip_control import switch_rc_mic_to_blackhole


class GlipProvider(ChromeCallProvider):
    name = "glip"
    url_pattern = "v.ringcentral.com/conf"
    mute_key = " "

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        """Override: Glip supports auto mic switch via JS injection."""
        return switch_rc_mic_to_blackhole()

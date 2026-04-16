"""Zoom — web version (app.zoom.us). Mute: Alt+A."""

from saymo.providers._chrome_base import ChromeCallProvider


class ZoomProvider(ChromeCallProvider):
    name = "zoom"
    url_pattern = "app.zoom.us"
    mute_key = "a"
    mute_modifiers = "option down"  # Alt+A in Zoom web

"""Google Meet — browser (meet.google.com). Mute: Cmd+D."""

from saymo.providers._chrome_base import ChromeCallProvider


class GoogleMeetProvider(ChromeCallProvider):
    name = "google_meet"
    url_pattern = "meet.google.com"
    mute_key = "d"
    mute_modifiers = "command down"

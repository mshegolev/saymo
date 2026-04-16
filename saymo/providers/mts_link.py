"""MTS Link (ex-Webinar.ru) — browser (mts-link.ru). Mute: Space."""

from saymo.providers._chrome_base import ChromeCallProvider


class MTSLinkProvider(ChromeCallProvider):
    name = "mts_link"
    url_pattern = "mts-link.ru"
    mute_key = " "

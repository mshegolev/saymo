"""Yandex Telemost — browser (telemost.yandex.ru). Mute: M key."""

from saymo.providers._chrome_base import ChromeCallProvider


class TelemostProvider(ChromeCallProvider):
    name = "telemost"
    url_pattern = "telemost.yandex.ru"
    mute_key = "m"

"""Telegram — web version (web.telegram.org). Mute: Space during call."""

from saymo.providers._chrome_base import ChromeCallProvider


class TelegramProvider(ChromeCallProvider):
    name = "telegram"
    url_pattern = "web.telegram.org"
    mute_key = " "

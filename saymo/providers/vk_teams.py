"""VK Teams — web version. Mute: M key."""

from saymo.providers._chrome_base import ChromeCallProvider


class VKTeamsProvider(ChromeCallProvider):
    name = "vk_teams"
    url_pattern = "teams.vk.com"
    mute_key = "m"

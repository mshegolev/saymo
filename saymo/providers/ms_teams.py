"""Microsoft Teams — web version (teams.microsoft.com). Mute: Cmd+Shift+M."""

from saymo.providers._chrome_base import ChromeCallProvider


class MSTeamsProvider(ChromeCallProvider):
    name = "ms_teams"
    url_pattern = "teams.microsoft.com"
    mute_key = "m"
    mute_modifiers = "command down, shift down"

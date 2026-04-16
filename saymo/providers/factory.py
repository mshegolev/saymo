"""Factory for creating call provider instances."""

from saymo.providers.glip import GlipProvider
from saymo.providers.zoom import ZoomProvider
from saymo.providers.mts_link import MTSLinkProvider
from saymo.providers.telemost import TelemostProvider
from saymo.providers.vk_teams import VKTeamsProvider
from saymo.providers.google_meet import GoogleMeetProvider
from saymo.providers.ms_teams import MSTeamsProvider

PROVIDERS = {
    # RingCentral
    "glip": GlipProvider,
    "ringcentral": GlipProvider,
    # Zoom
    "zoom": ZoomProvider,
    # Russian providers
    "mts_link": MTSLinkProvider,
    "mts-link": MTSLinkProvider,
    "telemost": TelemostProvider,
    "yandex": TelemostProvider,
    "vk_teams": VKTeamsProvider,
    "vk": VKTeamsProvider,
    # Google & Microsoft
    "google_meet": GoogleMeetProvider,
    "google": GoogleMeetProvider,
    "meet": GoogleMeetProvider,
    "ms_teams": MSTeamsProvider,
    "teams": MSTeamsProvider,
    "microsoft_teams": MSTeamsProvider,
}


def get_provider(name: str = "glip"):
    """Get a call provider by name."""
    cls = PROVIDERS.get(name.lower())
    if cls is None:
        available = ", ".join(sorted(set(PROVIDERS.keys())))
        raise ValueError(f"Unknown provider: {name}. Available: {available}")
    return cls()


def list_providers() -> list[str]:
    """List unique provider names."""
    return sorted(set(cls.name for cls in PROVIDERS.values()))

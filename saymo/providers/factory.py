"""Factory for creating call provider instances."""

from saymo.providers.glip import GlipProvider
from saymo.providers.zoom import ZoomProvider
from saymo.providers.mts_link import MTSLinkProvider

PROVIDERS = {
    "glip": GlipProvider,
    "ringcentral": GlipProvider,
    "zoom": ZoomProvider,
    "mts_link": MTSLinkProvider,
    "mts-link": MTSLinkProvider,
}


def get_provider(name: str = "glip"):
    """Get a call provider by name.

    Supported: glip, zoom, mts_link.
    """
    cls = PROVIDERS.get(name.lower())
    if cls is None:
        available = ", ".join(sorted(set(PROVIDERS.keys())))
        raise ValueError(f"Unknown provider: {name}. Available: {available}")
    return cls()


def list_providers() -> list[str]:
    """List unique provider names."""
    return sorted(set(cls.name for cls in PROVIDERS.values()))

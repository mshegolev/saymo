"""Base class and auto-discovery for source plugins."""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Protocol

logger = logging.getLogger("saymo.plugins")


class SourcePlugin(Protocol):
    """Protocol for task/content source plugins.

    Each plugin provides standup content as a dict with keys:
    - yesterday: str | None — what was done
    - today: str | None — what's planned
    - yesterday_date: str
    - today_date: str
    """

    name: str
    description: str

    async def fetch(self, config) -> dict | None:
        """Fetch standup content. Returns notes dict or None."""
        ...


# Registry of discovered plugins
_plugins: dict[str, type] = {}


def discover_plugins() -> dict[str, type]:
    """Auto-discover all SourcePlugin implementations in saymo/plugins/."""
    global _plugins
    if _plugins:
        return _plugins

    plugins_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(plugins_dir)]):
        if module_info.name.startswith("_") or module_info.name == "base":
            continue
        try:
            module = importlib.import_module(f"saymo.plugins.{module_info.name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and hasattr(attr, "name")
                        and hasattr(attr, "fetch")
                        and attr_name != "SourcePlugin"
                        and not attr_name.startswith("_")):
                    plugin_name = getattr(attr, "name", module_info.name)
                    _plugins[plugin_name] = attr
                    logger.debug(f"Discovered plugin: {plugin_name} ({attr.__name__})")
        except Exception as e:
            logger.warning(f"Failed to load plugin {module_info.name}: {e}")

    return _plugins


def get_plugin(name: str):
    """Get a plugin instance by name."""
    plugins = discover_plugins()
    cls = plugins.get(name)
    if cls is None:
        available = ", ".join(sorted(plugins.keys()))
        raise ValueError(f"Unknown source plugin: {name}. Available: {available}")
    return cls()


def list_plugins() -> list[str]:
    """List available plugin names."""
    return sorted(discover_plugins().keys())

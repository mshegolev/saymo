# ADR-008: Multi-Provider Architecture via ChromeCallProvider Base

**Status:** Accepted
**Date:** 2026-04-17
**Author:** Mikhail Shchegolev

## Context

Saymo initially supported only Glip (RingCentral Video) calls. Need to support Zoom, Google Meet, MS Teams, Telegram, Yandex Telemost, VK Teams, MTS Link — all through Chrome web versions.

## Decision

All providers work through **Chrome browser** (web versions of each service). Common logic extracted into `ChromeCallProvider` base class.

### Base Class (`_chrome_base.py`)
Handles: Chrome tab detection by URL pattern, tab activation, mute toggle via keystroke, app switching.

### Provider Implementation (5 lines each)
```python
class ZoomProvider(ChromeCallProvider):
    name = "zoom"
    url_pattern = "app.zoom.us"
    mute_key = "a"
    mute_modifiers = "option down"
```

### 8 Providers

| Provider | URL Pattern | Mute Key | Special |
|----------|-------------|----------|---------|
| Glip | v.ringcentral.com/conf | Space | JS mic switch |
| Zoom | app.zoom.us | Alt+A | — |
| Google Meet | meet.google.com | Cmd+D | — |
| MS Teams | teams.microsoft.com | Cmd+Shift+M | — |
| Telegram | web.telegram.org | Space | — |
| Yandex Telemost | telemost.yandex.ru | M | — |
| VK Teams | teams.vk.com | M | — |
| MTS Link | mts-link.ru | Space | — |

### Factory Pattern
```python
from saymo.providers.factory import get_provider
provider = get_provider("zoom")  # or "glip", "teams", "tg", etc.
```

### Meeting Profiles (config.yaml)
```yaml
meetings:
  standup:
    provider: "glip"
  zoom_weekly:
    provider: "zoom"
```

## Consequences

**Positive:**
- Adding new provider: 5 lines of code + 1 line in factory
- All providers share tested Chrome automation logic
- No native app dependencies — everything through Chrome
- Refactored from 435 lines → 139 lines (68% reduction)

**Negative:**
- Web versions may have fewer features than native apps
- Mute hotkeys may change with provider updates
- JS-based mic switching only implemented for Glip (others need manual mic setup)

## Alternatives Considered

- **Native app support**: would need separate AppleScript per app, complex accessibility automation
- **Provider API integration**: OAuth complexity, rate limits, most don't support call automation via API

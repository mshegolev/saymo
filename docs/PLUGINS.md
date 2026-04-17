# Extending Saymo

Saymo has two extension points. Both are designed so that a human reader and an AI agent (Claude Code) can add new ones from a short example without reading the rest of the codebase.

| Extension          | Directory             | Registration              | Use it for                                            |
| ------------------ | --------------------- | ------------------------- | ----------------------------------------------------- |
| **Source plugin**  | `saymo/plugins/`      | Auto-discovered on import | New place to fetch standup content from               |
| **Call provider**  | `saymo/providers/`    | Manual entry in `factory.py` | New meeting app to drive (mute, switch mic, focus tab) |

If you only want pre-written text spoken — no plugin needed, use the built-in `file` source (`saymo/plugins/file_summary.py`) and point `speech.summary_file` at your file.

---

## 1. Source plugin — fetch standup content from a new system

### Contract

A source plugin is any class that exposes:

```python
name: str          # short id, used in config (speech.source: "<name>")
description: str   # one-line human description
async def fetch(self, config) -> dict | None
```

`fetch` returns either `None` (nothing to say) or a dict with these keys:

```python
{
    "yesterday":      str | None,  # what was done
    "today":          str | None,  # what's planned
    "yesterday_date": str,         # free-form label, shown in TUI
    "today_date":     str,
}
```

The composer (`saymo/speech/ollama_composer.py`) takes that dict and turns it into spoken Russian via Ollama.

### Minimal example — fetch from a Notion database

Drop this file at `saymo/plugins/notion.py`. No registration step needed — `discover_plugins()` (in `saymo/plugins/base.py`) finds it on next start.

```python
"""Notion source — pull yesterday/today from a Notion database."""

import httpx


class NotionSource:
    name = "notion"
    description = "Standup notes from a Notion database"

    async def fetch(self, config) -> dict | None:
        token = getattr(config, "notion_token", None) or ""
        db_id = getattr(config, "notion_db", None) or ""
        if not token or not db_id:
            return None

        async with httpx.AsyncClient(timeout=20.0, proxy=None) as client:
            r = await client.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                },
                json={"page_size": 20},
            )
            r.raise_for_status()
            pages = r.json().get("results", [])

        if not pages:
            return None

        yesterday_lines = [_title(p) for p in pages if _is_done(p)]
        today_lines     = [_title(p) for p in pages if _is_planned(p)]

        return {
            "yesterday":      "\n".join(yesterday_lines) or None,
            "today":          "\n".join(today_lines)     or None,
            "yesterday_date": "вчера",
            "today_date":     "сегодня",
        }


def _title(page) -> str:
    props = page.get("properties", {})
    title_prop = next((v for v in props.values() if v.get("type") == "title"), None)
    if not title_prop:
        return ""
    return "".join(t.get("plain_text", "") for t in title_prop.get("title", []))


def _is_done(page) -> bool:
    return _status(page) in {"Done", "Готово"}


def _is_planned(page) -> bool:
    return _status(page) in {"In Progress", "Today", "В работе"}


def _status(page) -> str:
    s = page.get("properties", {}).get("Status", {})
    return (s.get("status") or s.get("select") or {}).get("name", "")
```

### Wire it into the config

```yaml
# config.yaml
speech:
  source: notion         # matches NotionSource.name
  composer: ollama
notion_token: ${NOTION_TOKEN}
notion_db: 1234567890abcdef...
```

`config.py` does `${ENV_VAR}` substitution, so put secrets in env vars, not in YAML.

### Try it

```bash
saymo prepare        # runs Ollama composer on what your plugin returned
saymo dashboard      # press 'p' to see your plugin in the source list
```

---

## 2. Call provider — drive a new meeting app

### Two flavours

- **Browser-based app** (Zoom Web, Meet, MTS Link, …) — subclass `ChromeCallProvider`, set 3 fields, done.
- **Native macOS app** — implement the full `CallProvider` protocol (`saymo/providers/base.py`).

For 95% of cases the browser version is what you need.

### Minimal Chrome-based example — Whereby

```python
# saymo/providers/whereby.py
"""Whereby — web only. Mute: M."""

from saymo.providers._chrome_base import ChromeCallProvider


class WherebyProvider(ChromeCallProvider):
    name = "whereby"
    url_pattern = "whereby.com"     # any open Chrome tab matching this is the meeting
    mute_key = "m"                  # the app's mute hotkey
    mute_modifiers = ""             # e.g. "option down" for Zoom (Alt+A)
```

### Register it

Edit `saymo/providers/factory.py`:

```python
from saymo.providers.whereby import WherebyProvider

PROVIDERS = {
    # ...existing entries...
    "whereby": WherebyProvider,
}
```

Aliases are free — just add another key to `PROVIDERS` pointing at the same class.

### Wire it into a meeting profile

```yaml
# config.yaml
meetings:
  standup:
    provider: whereby
    triggers: ["михаил", "саймо"]
    team: false
```

Then:

```bash
saymo speak --whereby            # one-shot speak into the call
saymo auto -p standup            # listen for trigger, then speak
```

### When you need more than Chrome

If the app is a native client (e.g. desktop Telegram), implement the full protocol:

```python
# saymo/providers/native_example.py
from saymo.providers.base import CallProvider, MeetingStatus


class NativeExampleProvider:
    name = "native_example"

    def check_ready(self) -> MeetingStatus:
        # Use AppleScript / `pgrep` / window queries to detect the call
        ...

    def activate_meeting(self) -> bool:
        # Bring the app/window to front
        ...

    def toggle_mute(self) -> None:
        # Send the mute hotkey via System Events
        ...

    def switch_mic(self, device_name: str) -> bool:
        # Optional: open the app's audio settings and pick the mic
        return False

    def get_previous_app(self) -> str:
        from saymo.glip_control import _run_applescript
        return _run_applescript('tell application "System Events" to '
                                'get name of first process whose frontmost is true') or ""
```

`saymo/glip_control.py` already has `_run_applescript` and helper utilities — reuse them.

---

## 3. Quick checklist before sending a PR

- [ ] Plugin/provider file lives in `saymo/plugins/` or `saymo/providers/`.
- [ ] `name` is lowercase, no spaces — it's used in YAML and CLI flags.
- [ ] All HTTP clients use `proxy=None` (corporate proxies block localhost / external APIs in unexpected ways — see `saymo/speech/ollama_composer.py` for the pattern).
- [ ] Secrets read from env via `${VAR}` in `config.yaml`, never hardcoded.
- [ ] For providers — entry added to `saymo/providers/factory.py` `PROVIDERS` dict.
- [ ] For sources — nothing to register; auto-discovery picks it up. To verify:

      ```bash
      python -c "from saymo.plugins.base import list_plugins; print(list_plugins())"
      ```

- [ ] Smoke test:
      - source plugin → `saymo prepare` produces text
      - call provider → `saymo speak --<name>` plays audio into the meeting

---

## 4. Notes for AI agents (Claude Code)

- Both extension types are intentionally tiny. **Do not refactor `base.py`, `factory.py`, or `discover_plugins()`** when adding a new plugin — copy an existing file instead (`file_summary.py` for sources, `zoom.py` for providers).
- If the user describes a new "place tasks come from", that's a **source plugin**, not a provider.
- If the user describes a new "app to talk into", that's a **call provider**.
- Don't add a top-level CLI command for the new plugin — sources are selected via `speech.source`, providers via `--<name>` flag and `meetings.<profile>.provider`. The infrastructure is already wired.
- After adding a source plugin, run the one-liner from the checklist above to confirm `discover_plugins()` sees it before reporting success.

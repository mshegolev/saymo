"""Glip-specific Chrome helpers + generic AppleScript utilities.

This module hosts:

* Generic AppleScript helpers (``_run_applescript``, ``_run_applescript_js``,
  ``get_previous_app``, ``activate_app``) used by every
  :class:`ChromeCallProvider`.
* Glip-only mic-switch logic (``find_glip_tab``, ``switch_rc_mic_to_blackhole``)
  used by :class:`GlipProvider` — Glip exposes a working audio dropdown that
  we can drive from JavaScript.

Everything else (muting, tab activation, unmute/speak/mute flow,
``check_ready``) is provider-agnostic and lives in
``saymo/providers/_chrome_base.py``. Do not re-introduce Glip-specific
wrappers here.
"""

import logging
import subprocess

logger = logging.getLogger("saymo.glip")


def _run_applescript(script: str) -> str:
    """Execute AppleScript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        logger.warning(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def _run_applescript_js(window: int, tab: int, js: str) -> str:
    """Execute JavaScript in a Chrome tab via AppleScript.

    Uses a temp file for long scripts to avoid escaping issues.
    """
    import tempfile
    from pathlib import Path

    # For short scripts, inline works fine
    if len(js) < 200 and '"' not in js:
        escaped_js = js.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        script = (
            'tell application "Google Chrome"\n'
            f"    tell window {window}\n"
            f'        set jsResult to execute tab {tab} javascript "{escaped_js}"\n'
            "        return jsResult\n"
            "    end tell\n"
            "end tell"
        )
        return _run_applescript(script)

    # For long/complex scripts, write to temp file and read via shell
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(js.replace("\n", " "))
        js_path = f.name

    try:
        script = (
            f'set jsCode to do shell script "cat {js_path}"\n'
            'tell application "Google Chrome"\n'
            f"    tell window {window}\n"
            f"        set jsResult to execute tab {tab} javascript jsCode\n"
            "        return jsResult\n"
            "    end tell\n"
            "end tell"
        )
        return _run_applescript(script)
    finally:
        Path(js_path).unlink(missing_ok=True)


def get_previous_app() -> str:
    """Get the name of the currently active app (before switching)."""
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
    end tell
    return frontApp
    '''
    return _run_applescript(script)


def activate_app(app_name: str):
    """Switch back to a specific app."""
    script = f'''
    tell application "{app_name}"
        activate
    end tell
    '''
    _run_applescript(script)


def find_glip_tab() -> tuple[int, int] | None:
    """Find Chrome window and tab index with a Glip call.

    Returns ``(window_index, tab_index)`` or ``None`` if not found.
    """
    script = '''
    tell application "Google Chrome"
        set windowCount to count of windows
        repeat with w from 1 to windowCount
            set tabCount to count of tabs of window w
            repeat with t from 1 to tabCount
                set tabURL to URL of tab t of window w
                if tabURL contains "v.ringcentral.com/conf" or tabURL contains "glip.com" then
                    return (w as text) & "," & (t as text)
                end if
            end repeat
        end repeat
    end tell
    return "not_found"
    '''
    result = _run_applescript(script)
    if result and result != "not_found":
        parts = result.split(",")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return None


def switch_rc_mic_to_blackhole() -> bool:
    """Switch Glip's microphone to BlackHole 2ch via Chrome JS injection.

    Clicks the audio-settings dropdown and selects BlackHole 2ch. Returns
    ``True`` on success. When the JS path fails (UI moved, dropdown locked
    behind a modal, etc.), logs a warning and returns ``False`` — the user
    should switch the mic manually once per call (see README).
    """
    tab = find_glip_tab()
    if not tab:
        logger.error("Glip tab not found")
        return False

    w, t = tab

    # Step 1: Click "Audio menu" button (^ dropdown arrow)
    js_open = (
        '(function() {'
        ' var btn = document.querySelector(\'[aria-label="Audio menu"]\');'
        ' if (btn) { btn.click(); return "clicked"; }'
        ' return "not_found";'
        '})()'
    )
    result = _run_applescript_js(w, t, js_open)
    logger.info(f"Open audio menu: {result}")

    if not result or "not_found" in result or "missing" in result.lower():
        logger.warning(
            "Audio-menu button not reachable — switch BlackHole 2ch manually "
            "in the Glip call (^ arrow next to Mute → Microphone)."
        )
        return False

    import time
    time.sleep(2)

    # Step 2: Click BlackHole 2ch in the Microphone section (first half of radio list)
    js_select = (
        '(function() {'
        ' var radios = document.querySelectorAll(\'li[role="radio"]\');'
        ' if (radios.length === 0) return "no_radios";'
        ' var micCount = Math.floor(radios.length / 2);'
        ' for (var i = 0; i < micCount; i++) {'
        '   var text = (radios[i].textContent || "").trim();'
        '   if (text.includes("BlackHole 2ch")) {'
        '     if (radios[i].classList.contains("media-buttons__opt--selected"))'
        '       return "already_selected";'
        '     radios[i].click();'
        '     return "selected";'
        '   }'
        ' }'
        ' return "not_found";'
        '})()'
    )
    result2 = _run_applescript_js(w, t, js_select)
    logger.info(f"Select BlackHole: {result2}")

    if result2 and ("selected" in result2 or "already" in result2):
        # Close the dropdown
        time.sleep(0.3)
        _run_applescript_js(w, t, "document.body.click()")
        return True

    logger.warning(
        "BlackHole 2ch not found in Glip audio menu — select it manually."
    )
    return False

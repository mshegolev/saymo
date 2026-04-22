"""Glip call control — Chrome tab automation via AppleScript.

Handles:
- Finding Chrome tab with Glip call (v.ringcentral.com/conf)
- Pressing Space to toggle mute/unmute
- Auto-switching mic to BlackHole via JS injection
- Switching to Chrome and back
"""

import asyncio
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


def find_glip_tab() -> tuple[int, int] | None:
    """Find Chrome window and tab index with Glip call.

    Returns (window_index, tab_index) or None if not found.
    """
    script = '''
    tell application "Google Chrome"
        set windowCount to count of windows
        repeat with w from 1 to windowCount
            set tabCount to count of tabs of window w
            repeat with t from 1 to tabCount
                set tabURL to URL of tab t of window w
                set tabTitle to title of tab t of window w
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


def activate_glip_tab() -> bool:
    """Switch to Chrome and activate the Glip tab.

    Returns True if successful.
    """
    tab = find_glip_tab()
    if not tab:
        logger.error("Glip tab not found in Chrome")
        return False

    w, t = tab
    script = f'''
    tell application "Google Chrome"
        activate
        set active tab index of window {w} to {t}
        set index of window {w} to 1
    end tell
    delay 0.5
    '''
    _run_applescript(script)
    logger.info(f"Activated Glip tab (window {w}, tab {t})")
    return True


def press_space():
    """Press Space key in the frontmost app (Chrome) to toggle mute."""
    script = '''
    tell application "System Events"
        keystroke " "
    end tell
    '''
    _run_applescript(script)
    logger.info("Pressed Space (mute toggle)")


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


async def unmute_speak_mute(speak_fn, *args, **kwargs):
    """Full Glip automation flow:

    1. Remember current app
    2. Switch to Chrome (Glip tab)
    3. Press Space (unmute)
    4. Run speak function
    5. Press Space (mute)
    6. Switch back to original app
    """
    previous_app = get_previous_app()
    logger.info(f"Current app: {previous_app}")

    # Activate Glip
    if not activate_glip_tab():
        raise RuntimeError("Cannot find Glip tab in Chrome")

    await asyncio.sleep(0.3)

    # Unmute
    press_space()
    await asyncio.sleep(0.5)

    try:
        # Speak
        await speak_fn(*args, **kwargs)
    finally:
        # Always mute back
        await asyncio.sleep(0.3)

        # Re-activate Glip tab in case focus changed
        activate_glip_tab()
        await asyncio.sleep(0.3)

        press_space()
        logger.info("Muted back")

        # Switch back to original app
        await asyncio.sleep(0.3)
        if previous_app and previous_app != "Google Chrome":
            activate_app(previous_app)
            logger.info(f"Switched back to {previous_app}")


def check_glip_ready() -> dict:
    """Check if Glip is ready for automation.

    Returns dict with status info.
    """
    result = {
        "chrome_running": False,
        "glip_tab_found": False,
        "tab_info": None,
        "mic_is_blackhole": False,
    }

    # Check Chrome is running
    check = _run_applescript('''
    tell application "System Events"
        return (name of processes) contains "Google Chrome"
    end tell
    ''')
    result["chrome_running"] = check == "true"

    if result["chrome_running"]:
        tab = find_glip_tab()
        result["glip_tab_found"] = tab is not None
        result["tab_info"] = tab

    # Check system default input device
    from saymo.audio.devices import default_input
    dev = default_input()
    if dev and "blackhole" in dev["name"].lower():
        result["mic_is_blackhole"] = True

    return result


def switch_rc_mic_to_blackhole() -> bool:
    """Switch Glip microphone to BlackHole 2ch via Chrome JS injection.

    Clicks the audio settings dropdown and selects BlackHole 2ch.
    Returns True if successful.
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
        logger.warning("Could not find audio menu button, trying GUI fallback")
        return _switch_mic_via_gui()

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

    # JS approach failed — try GUI fallback
    return _switch_mic_via_gui()


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


def _switch_mic_via_gui() -> bool:
    """Fallback: switch mic using macOS accessibility GUI scripting.

    Clicks through the UI using coordinates relative to the mute button area.
    """
    logger.info("Attempting GUI-based mic switch")

    # Use System Events to find and interact with Chrome UI
    script = '''
    tell application "Google Chrome" to activate
    delay 0.5

    tell application "System Events"
        tell process "Google Chrome"
            -- Find all buttons, look for audio-related ones
            set allButtons to every button of front window
            set foundAudio to false

            -- Try to find by accessibility description
            repeat with btn in allButtons
                try
                    set desc to description of btn
                    if desc contains "audio" or desc contains "microphone" or desc contains "Audio" then
                        click btn
                        set foundAudio to true
                        exit repeat
                    end if
                end try
            end repeat

            if not foundAudio then
                return "gui_audio_button_not_found"
            end if

            delay 1

            -- Now find BlackHole 2ch in the opened menu
            set allUIElements to every UI element of front window
            repeat with elem in allUIElements
                try
                    if (name of elem) contains "BlackHole 2ch" then
                        click elem
                        return "gui_selected_blackhole"
                    end if
                end try
            end repeat

            -- Try static text elements
            set allTexts to every static text of front window
            repeat with txt in allTexts
                try
                    if (value of txt) contains "BlackHole 2ch" then
                        click txt
                        return "gui_clicked_blackhole_text"
                    end if
                end try
            end repeat

            return "gui_blackhole_not_found"
        end tell
    end tell
    '''
    result = _run_applescript(script)
    logger.info(f"GUI switch result: {result}")
    return "selected" in result or "clicked" in result


def get_mic_setup_instructions() -> str:
    """Return instructions for setting up BlackHole as mic in Glip."""
    return (
        "In the Glip call:\n"
        "  1. Click the ^ arrow next to the Mute button\n"
        "  2. Under Microphone, select 'BlackHole 2ch (Virtual)'\n"
        "  3. Keep Speakers as 'Plantronics' (so you hear others)\n"
        "\n"
        "This only needs to be done once per call."
    )

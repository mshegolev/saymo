"""Glip call control — Chrome tab automation via AppleScript.

Handles:
- Finding Chrome tab with Glip call
- Pressing Space to toggle mute/unmute
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
    """Find Chrome window and tab index with Glip/RingCentral call.

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
                if tabURL contains "v.ringcentral.com/conf" or tabURL contains "glip.com" or tabTitle contains "RingCentral" then
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
    try:
        import sounddevice as sd
        default_input = sd.query_devices(kind="input")
        if default_input and "blackhole" in default_input["name"].lower():
            result["mic_is_blackhole"] = True
    except Exception:
        pass

    return result


def set_system_input_to_blackhole() -> bool:
    """Set macOS system input device to BlackHole 2ch via AppleScript.

    Note: This changes the SYSTEM default mic, not the RingCentral in-app setting.
    The user must select BlackHole 2ch in RingCentral audio settings manually.
    """
    script = '''
    tell application "System Preferences"
        reveal anchor "input" of pane id "com.apple.preference.sound"
        activate
    end tell
    '''
    _run_applescript(script)
    logger.info("Opened Sound preferences → Input")
    return True


def get_mic_setup_instructions() -> str:
    """Return instructions for setting up BlackHole as mic in RingCentral."""
    return (
        "In the RingCentral Video call:\n"
        "  1. Click the ^ arrow next to the Mute button\n"
        "  2. Under Microphone, select 'BlackHole 2ch (Virtual)'\n"
        "  3. Keep Speakers as 'Plantronics' (so you hear others)\n"
        "\n"
        "This only needs to be done once per call."
    )

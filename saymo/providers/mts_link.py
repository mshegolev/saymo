"""MTS Link (ex-Webinar.ru) — browser (mts-link.ru). Mute: Space.

Extended with JS-based mic switching for MTS Link UI.
DOM structure (MUI Select):
  - Mic dropdown button: [data-testid="VCSControlButton.Microfone.dropdown"]
  - Mic select: .Select__input___E9fzk[role="button"] (first one = mic)
  - Options appear as [role="option"] with data-value=hash, text=device name
  - Speaker select: second .Select__input___E9fzk (same structure)
"""

import logging
import time

from saymo.providers._chrome_base import ChromeCallProvider

logger = logging.getLogger("saymo.providers.mts_link")


class MTSLinkProvider(ChromeCallProvider):
    name = "mts_link"
    url_pattern = "mts-link.ru"
    mute_key = " "

    def switch_mic(self, device_name: str = "BlackHole 2ch") -> bool:
        """Switch microphone in MTS Link via JS injection.

        Flow: open mic dropdown → open MUI Select → click matching option.
        """
        status = self.check_ready()
        if not status.tab_info:
            logger.error("MTS Link tab not found")
            return False

        w, t = status.tab_info

        try:
            from saymo.glip_control import _run_applescript_js
        except ImportError:
            logger.warning("Cannot import _run_applescript_js")
            return False

        # Step 1: Open mic settings dropdown (the little arrow next to mic button)
        js_open_dropdown = (
            '(function(){'
            'var btn=document.querySelector(\'[data-testid="VCSControlButton.Microfone.dropdown"]\');'
            'if(btn){btn.click();return "ok";}return "no_btn";'
            '})()'
        )
        r = _run_applescript_js(w, t, js_open_dropdown)
        logger.info(f"Open mic dropdown: {r}")
        if not r or "ok" not in r:
            return False

        time.sleep(1)

        # Step 2: Click the MUI Select to open the device listbox
        js_open_select = (
            '(function(){'
            'var s=document.querySelector(\'.Select__input___E9fzk[role="button"]\');'
            'if(s){s.dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));return "ok";}'
            'return "no_select";'
            '})()'
        )
        r2 = _run_applescript_js(w, t, js_open_select)
        logger.info(f"Open MUI Select: {r2}")
        if not r2 or "ok" not in r2:
            return False

        time.sleep(1)

        # Step 3: Find and click the target device option
        # Options are [role="option"] with text containing device_name
        js_select_device = (
            '(function(){'
            'var opts=document.querySelectorAll(\'[role="option"]\');'
            'for(var i=0;i<opts.length;i++){'
            'var t=(opts[i].textContent||"").trim();'
            f'if(t.includes("{device_name}"))' '{'
            'opts[i].click();return "selected:"+t;'
            '}}'
            'var names=[];'
            'opts.forEach(function(o){names.push(o.textContent.trim());});'
            'return "not_found:"+names.join(",");'
            '})()'
        )
        r3 = _run_applescript_js(w, t, js_select_device)
        logger.info(f"Select device: {r3}")

        if r3 and "selected:" in r3:
            time.sleep(0.5)
            # Close the settings panel by pressing Escape
            from saymo.glip_control import _run_applescript
            _run_applescript('''
            tell application "System Events"
                key code 53
            end tell
            ''')
            return True

        if r3 and "not_found:" in r3:
            available = r3.split("not_found:")[1]
            logger.warning(
                f"Device '{device_name}' not found in MTS Link. "
                f"Available: {available}"
            )

        return False

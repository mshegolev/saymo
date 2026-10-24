# Saymo Daily Prep

Auto-runs `saymo prepare` before a recurring meeting, opens the call app, and
shows a floating window with the prepared text and a Play/Stop control. Play
plays the prepared speech and records your own mic for the meeting; Stop ends
the recording and automatically re-transcribes it with the offline Whisper
model (`config.stt.whisper`) and asks the local LLM for a speech-coaching
pass (pace, filler words, clarity) — recommendations show up in the same
window and are saved under `~/.saymo/speech_reviews/`.

## Configure the profile

```yaml
meetings:
  personal:
    description: "Personal update — first-person brief"
    provider: glip
    schedule:
      time: "09:45"                    # HH:MM, 24h, local time
      days: [mon, tue, wed, thu, fri]   # optional, defaults to weekdays
    meeting_url: "https://meet.google.com/xxx-xxxx-xxx"  # optional
```

`schedule` is required to install the LaunchAgent; `meeting_url` is optional
— without it, `daily-prep` only prepares and shows the window.

## Install the schedule

```bash
saymo daily-prep-agent install -p personal
saymo daily-prep-agent start -p personal
saymo daily-prep-agent status -p personal
```

The plist is written under `~/Library/LaunchAgents/` and logs go to
`~/.saymo/daily_prep/<profile>/logs/`. It fires `saymo daily-prep -p
<profile>` at the configured time via launchd's `StartCalendarInterval` — no
continuously-running process, unlike the call-control LaunchAgent.

```bash
saymo daily-prep-agent uninstall -p personal   # remove the schedule
saymo daily-prep-agent restart -p personal     # reload after editing config.yaml
```

## Run it by hand

```bash
saymo daily-prep -p personal              # prepare + open app + show window
saymo daily-prep -p personal --no-window  # prepare + open app only
```

## Secrets (JIRA_TOKEN, etc.)

launchd's GUI session does not read `~/.zshrc`/`~/.zprofile`, so `${VAR}`
secrets exported there (e.g. `jira.token: ${JIRA_TOKEN}`) never reach a
scheduled run unless baked into the plist explicitly. `daily-prep-agent
install` scans your active `config.yaml` for `${VAR}` references and bakes
whichever of those are currently set in your shell into the plist's
`EnvironmentVariables` — so **run `install` from the same shell where the
secret is exported**, and re-run it whenever that secret rotates (`status`
lists which names are baked in, never their values).

## Notes

- Recording uses `config.audio.recording_device` (your own mic) — the
  remote side of the call is never recorded, same policy as `--record` in
  `scripts/live_translate.py`.
- Speech coaching needs Ollama running (`ollama serve`) and reuses
  `config.ollama.model`; override the prompt via `config.prompts.speech_coaching_ru`.
- If `tkinter` isn't available, `daily-prep` prints the prepared text to the
  console instead of opening a window.

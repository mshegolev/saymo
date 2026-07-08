# Launch and Realtime Evidence

This workflow is local-only and read-only. It consumes saved launch-readiness,
realtime decision, scorecard, and safety-soak artifacts. It does not repair provider state,
does not change audio routes, does not control launchd, and
does not start live fallback behavior.

## Workflow

1. Capture call-ready evidence before the call:

   ```bash
   saymo call-ready -p standup --provider glip --output ~/.saymo/live_control/standup/call-ready.json
   ```

2. Run or rehearse the call so realtime decisions are written to the local
   profile log, normally:

   ```text
   ~/.saymo/live_control/standup/realtime-decisions.jsonl
   ```

3. Build a scorecard from the saved artifacts:

   ```bash
   saymo session-scorecard -p standup --rehearsal <rehearsal.json> --launch-json ~/.saymo/live_control/standup/call-ready.json --realtime-jsonl ~/.saymo/live_control/standup/realtime-decisions.jsonl --json-output <scorecard.json>
   ```

   `--launch-readiness` is an alias for `--launch-json`, and `--realtime` is
   an alias for `--realtime-jsonl`. Use `--output <scorecard.md>` when a
   Markdown scorecard file is needed; `--json-output` remains the JSON output
   path.

4. Gate the evidence with safety-soak:

   ```bash
   saymo safety-soak -p standup --scorecard-json <scorecard.json>
   ```

   Use `--output <soak.md>` for Markdown and `--json-output <soak.json>` for a
   saved JSON gate result.

## Troubleshooting

`session-scorecard` prints a v1.9 evidence section and remediation hints. The
hints list failed launch labels, blocker categories, launch artifact paths,
daemon stdout/stderr log paths, realtime artifact paths, blocker counts, and
rerun commands for `saymo call-ready`, `saymo call-control-agent status`,
`saymo call-control probe`, and `saymo session-scorecard`.

`safety-soak` prints safety violations and v1.9 next actions. For a failing
scorecard, rerun the scorecard first with the launch and realtime artifacts,
then rerun:

```bash
saymo safety-soak -p standup --scorecard-json <scorecard.json>
```

## Privacy

Evidence output uses sanitized labels, counts, booleans, hashes, artifact
paths, log paths, and rerun commands. It must not include raw transcript text,
generated answer text, daily-note body content, audio bytes, secrets, or
provider payloads.

## Live Risk

Automated evidence can prove saved launch and realtime artifacts are readable
and internally safe. A live-call smoke is still required before trusting a real
meeting because Chrome tab state, BlackHole routing, Accessibility permission,
LaunchAgent session state, mute behavior, and actual audio playback depend on
the user's macOS GUI session.

# Pitfalls Research: Saymo v1.9 Call Launch Readiness

**Domain:** Local macOS realtime voice assistant for live calls
**Milestone:** v1.9 Call Launch Readiness
**Researched:** 2026-07-08
**Confidence:** HIGH for repo-specific safety and readiness risks; MEDIUM for LaunchAgent behavior until tested in the user's GUI session with real permissions.

## Summary

v1.9 fails if it makes Saymo easier to start without making it safer to start. The milestone adds a single call-ready path, provider remediation, a local daemon/LaunchAgent, and a realtime loop. Those features sit directly on the existing safety boundary: approved cloned voice, prepared/cache freshness, provider tab readiness, BlackHole routing, hotkeys, manual takeover, hard-disable state, and sanitized local evidence.

The most dangerous shortcuts are treating warnings as ready, letting a cache miss speak a generic or live-generated fallback, relying on a stale `~/.saymo/live_control/<profile>/state.json`, or reporting "daemon running" without proving hotkeys and stop/takeover actions work. The roadmap should keep the first phase diagnostic and fail-closed, then add realtime behavior only after preflight, provider, cache, voice, and handbrake checks become explicit gates.

Suggested phase names used below:

| Phase | Suggested Name | Purpose |
|---|---|---|
| 36 | Call-Ready Preflight and Cache Gate | One ready/not-ready flow for daily note, prepared standup, response cache, voice metadata, profile, and concise remediation. |
| 37 | Provider and Audio Remediation | Chrome/provider tab, BlackHole, playback/capture devices, permissions, mic takeover, and provider latency evidence. |
| 38 | Local Call-Control Daemon and LaunchAgent | Long-running local listener with hotkeys, live-control state, audit, install/start/stop/status/recover commands. |
| 39 | Fail-Closed Realtime Meeting Loop | Start realtime loop only after all readiness gates pass; block unsafe fallbacks and stale state. |
| 40 | Launch and Realtime Evidence Feedback | Post-call/rehearsal scorecards for launch health, cache hits/misses, fallback blocks, daemon health, and safety-soak regressions. |

## Critical Pitfalls

### Pitfall 1: Nonblocking Readiness Warnings Become a Green Launch

**What goes wrong:**
The new call-ready command prints `ready` while response cache, hotkeys, daemon, launchd helper, or live-control state are only warnings. The operator joins a call believing Saymo is controlled, but the stop/takeover path or cached answer path is missing.

**Why it happens:**
Current `auto-preflight` treats response cache and hotkeys as `blocking=False`. That was acceptable for rehearsal visibility, but v1.9's "one green launch path" has a higher standard.

**How to avoid:**
Create separate readiness levels:

- `rehearsal_ready`: can run a dry local check with warnings.
- `call_ready`: all safety-critical checks pass.
- `realtime_ready`: call-ready plus daemon heartbeat, provider tab, voice/cache freshness, and fail-closed response policy.

For `call_ready` and `realtime_ready`, make missing response cache variants, missing primary hotkeys, stale live-control state, unverified provider tab, and stale launchd helper blocking unless explicitly waived by a named `--allow-*` flag that is shown in evidence.

**Warning signs:**
- `preflight: ready` appears with `warn: response cache`, `warn: hotkeys`, `saymo auto listener: not detected`, or "no running saymo auto state detected".
- The roadmap says "reuse auto-preflight" without redefining which checks are blocking for real calls.
- Tests assert "ready" while cache variant count is `0/N`.

**Phase to address:**
Phase 36, then enforce again in Phase 39.

---

### Pitfall 2: Cache Misses Speak the Wrong Thing Instead of Failing Closed

**What goes wrong:**
A realtime question misses the response cache and Saymo speaks today's generic standup audio, a stale prepared WAV, or a live Ollama/TTS answer. This can sound like the user answering a question they did not actually answer.

**Why it happens:**
`_resolve_auto_response_decision()` currently falls back to prepared standup on cache miss when `responses.live_fallback=false`, and can generate a live answer when `responses.live_fallback=true`. That behavior is useful for older auto-mode, but v1.9 realtime readiness promises cache-backed, controlled replies.

**How to avoid:**
For the v1.9 realtime loop, add a strict response policy:

- Cache hit with fresh voice metadata: allowed.
- Explicit manual "Speak" prepared standup: allowed only as a user action.
- Cache miss during automatic question handling: block and audit `unsafe_cache_miss_blocked`.
- Live fallback: disabled for realtime unless a later phase creates latency, approval, and source-grounding gates.
- Non-cloned fallback: blocked for live-call output unless explicitly allowed and surfaced as not the user's voice.

**Warning signs:**
- Logs say `response route: standup_fallback` during automatic question handling.
- Safety-soak cannot distinguish `response_cache`, `standup_fallback`, and `live_fallback`.
- Cache miss tests still expect prepared standup for the new realtime command.

**Phase to address:**
Phase 36 defines policy; Phase 39 enforces it; Phase 40 verifies it in evidence.

---

### Pitfall 3: Stale Voice or Response Cache Metadata Is Accepted

**What goes wrong:**
Saymo plays a WAV generated for an old daily note, old voice profile, old F5 checkpoint, old reference transcript, or different selector/fallback policy.

**Why it happens:**
Voice cache metadata exists and checks selector fingerprints, but v1.9 combines several cache classes: prepared standup WAV, response variants, daily-note source, and cloned voice profile. It is easy to validate one cache and forget another.

**How to avoid:**
Make every launch-critical audio artifact carry privacy-safe sidecar metadata:

- purpose: `prepare`, `response_cache`, `manual_speak`, or `live_call`.
- selected engine and attempted engines.
- voice profile, approval state, reference audio/text hashes.
- source digest for the daily note or response text, but not the raw text.
- generated date/profile/provider.

The call-ready command should report exact stale reasons: `audio_missing`, `voice_metadata_missing`, `voice_metadata_stale`, `source_digest_stale`, `profile_not_approved`, or `non_cloned_fallback`.

**Warning signs:**
- A cache file exists but has no `.meta.json`.
- The preflight output says only "prepared standup exists".
- `prepare-responses` skips files solely because WAV files exist.
- Changing `~/.saymo/config.yaml`, voice profile, or daily note does not force a rebuild.

**Phase to address:**
Phase 36.

---

### Pitfall 4: False Positives Become Faster and More Operationally Convenient

**What goes wrong:**
Saymo answers when the user's name was only mentioned, when the transcript window contains unrelated chatter, or when a loose response-cache trigger matches a broad phrase.

**Why it happens:**
v1.9 improves launch speed and realtime readiness, but the underlying risk from earlier milestones remains: incidental name mentions and unknown speakers can look like handoffs. Faster launch and lower friction can amplify bad trigger decisions.

**How to avoid:**
Keep deterministic addressing as the safety boundary. The realtime loop must require:

- trigger phrase match.
- addressing decision that is not `mentioned_me`.
- current auto-answer state on.
- no manual takeover or hard disable.
- cache hit or explicitly approved prepared speech.
- recent safety-soak with no worsened false positives.

Do not let classifier live-assist, intent classifier, or LLM wording override a deterministic skip in v1.9.

**Warning signs:**
- `trigger-check` says `addressing=mentioned_me` but the realtime loop would still speak.
- New code checks `detector.check(text)` but not `classify_addressing()`.
- Phase plans optimize chunk size, F5 latency, or cache lookup before replaying known false-positive samples.

**Phase to address:**
Phase 39, with regression evidence in Phase 40.

---

### Pitfall 5: The Handbrake Exists but Is Not Actually Reachable

**What goes wrong:**
The operator sees a status panel or stale state file, but global hotkeys are not registered, the listener process died, Accessibility permission is missing, or stop/takeover commands are not being consumed.

**Why it happens:**
Current controls require a running Saymo process. `hotkey-doctor` can say the listener is not detected, and the live-control panel writes commands to a JSONL queue consumed by `saymo auto`. v1.9 moves this into a daemon/LaunchAgent, which adds more ways to look alive while control actions are dead.

**How to avoid:**
Daemon readiness must require:

- process identity: exactly one daemon/listener for the profile.
- fresh heartbeat/state `updated_at` within a short TTL.
- hotkeys registered or a clear "hotkeys unavailable" block.
- successful write and consume probe for a harmless `status` action.
- audit event proving `stop`, `toggle_auto_answer`, and `takeover` paths are wired.
- status surface that distinguishes `running`, `registered`, `reachable`, and `safe`.

**Warning signs:**
- `state.json` exists but `updated_at` is old.
- `launchctl print` shows a service, but Saymo status does not show a recent heartbeat.
- Multiple Saymo listener processes match the same profile.
- The menu/status surface has no "last action applied" timestamp.

**Phase to address:**
Phase 38, and Phase 39 blocks realtime start on stale/unreachable handbrake.

---

### Pitfall 6: LaunchAgent Works in Terminal Tests but Fails in the GUI Session

**What goes wrong:**
The LaunchAgent starts under the wrong domain, lacks `PATH`/`HOME`, cannot find `uv` or the venv, cannot access Keychain/GUI Accessibility, writes logs nowhere, or crash-loops until launchd throttles it.

**Why it happens:**
LaunchAgents are not login shells. `launchd.plist(5)` expects explicit `Program`/`ProgramArguments`, `WorkingDirectory`, `EnvironmentVariables`, and log paths. `launchctl(1)` distinguishes user, login, and `gui/<uid>` domains. A service being bootstrapped is not the same as its hotkeys being usable.

**How to avoid:**
Generate a per-user LaunchAgent with:

- reverse-DNS label, for example `com.mshegolev.saymo.call-control`.
- absolute `ProgramArguments`; avoid shell profile assumptions.
- explicit `HOME`, `PATH`, `SAYMO_CONFIG`, and any needed Python/uv path.
- `WorkingDirectory=/opt/develop/saymo`.
- `StandardOutPath` and `StandardErrorPath` under `~/.saymo/logs/`.
- `KeepAlive` only for the control daemon, with a sane crash-loop status report.
- install/start/stop/status commands using `launchctl bootstrap gui/$(id -u)`, `bootout`, `kickstart -k`, and `print`.

Do not double-fork or daemonize inside the process launched by launchd; let launchd supervise it.

**Warning signs:**
- The plist uses `saymo` or `uv` without absolute paths.
- The command works only after `source .venv/bin/activate`.
- No log file is configured.
- `launchctl list` is used as the only status check.
- The process exits immediately and launchd keeps respawning/throttling it.

**Phase to address:**
Phase 38.

---

### Pitfall 7: Provider Tab Readiness Is Too Shallow

**What goes wrong:**
Preflight finds a Chrome tab, but it is the wrong meeting, the audio menu selectors changed, BlackHole is not selected, the real microphone cannot be restored, or the provider tab cannot be activated/unmuted in time.

**Why it happens:**
Provider readiness can be mistaken for `meeting_found=true`. Existing provider latency and takeover checks prove more: tab activation, mic switch, BlackHole output, unmute/mute recovery, and playback timing.

**How to avoid:**
Split provider readiness into checks:

- `provider_tab_found`.
- `provider_tab_activated`.
- `saymo_mic_selectable`.
- `recording_mic_selectable`.
- `unmute_toggle_reversible`.
- `provider_latency_within_budget`.
- `mute_recovery_ok`.

Call-ready can stop at tab/audio readiness; realtime-ready must require takeover and latency evidence from the current provider/profile or a fresh dry probe.

**Warning signs:**
- The check says `ok: provider tab` but no mic switch was attempted.
- `takeover-check` is not part of the launch flow.
- Provider selectors are updated without replaying `provider-latency`.
- A failed mic switch is logged as a warning but the call is still green.

**Phase to address:**
Phase 37.

---

### Pitfall 8: Daily Note Creation Masks Missing Standup Content

**What goes wrong:**
The call-ready path creates today's Obsidian daily note, but it is an empty template. Saymo then prepares a generic, incomplete, or stale standup response and reports the source as ready.

**Why it happens:**
`scripts/ensure_obsidian_daily_note.py` correctly preserves existing notes and creates a missing file, but file existence is not content readiness. It also uses a narrow YAML section parser, so config shape changes can break silently unless surfaced.

**How to avoid:**
Treat "note exists" and "standup content ready" as separate checks:

- `daily_note_present`: helper can create this.
- `daily_note_has_standup_content`: must inspect relevant sections.
- `prepared_audio_matches_note_digest`: must compare cache metadata.
- `source_empty`: should block automatic launch unless explicitly allowed for rehearsal.

If a note is created, show the path and say content still needs review unless the generated sections contain real text.

**Warning signs:**
- A just-created note immediately leads to `prepared standup: ok`.
- The note contains only `- ` placeholders.
- The helper output path is the only evidence for source readiness.

**Phase to address:**
Phase 36.

---

### Pitfall 9: Launch and Runtime Evidence Leaks Raw Call Data

**What goes wrong:**
Readiness logs, launchd stdout/stderr, scorecards, JSON artifacts, or daemon status include raw transcripts, user names, meeting questions, local note content, full sensitive paths, or generated answer text.

**Why it happens:**
Older commands sometimes print transcript text for debugging, while v1.7/v1.8 added sanitized reports and privacy-safe cache metadata. v1.9 adds background logs and post-call evidence, increasing the chance that private call data lands in repo files or persistent launchd logs.

**How to avoid:**
For v1.9 evidence:

- Store raw call data only under `~/.saymo/`, never `.planning/`, `docs/`, or tests.
- Keep launchd logs operational: service start/stop, blocker codes, timestamps, not transcripts.
- Use source/session IDs, counts, hashes, durations, categories, and blocker reasons.
- Render sanitized Markdown/JSON for roadmap evidence.
- Redact tokens, secrets, and full paths in remediation output.
- Add tests that generated reports do not include transcript text passed into the fixture.

**Warning signs:**
- `StandardOutPath` contains raw `console.print(f"[dim]{text}[/]")` transcript lines from the live loop.
- A committed fixture includes real meeting text or local personal paths.
- Remediation hints include full vault paths, tokens, or note contents.

**Phase to address:**
Phase 38 for daemon logs; Phase 40 for evidence artifacts.

---

### Pitfall 10: Heavy Model Installs or Cold Starts Enter the Call-Ready Path

**What goes wrong:**
The user runs the call-ready command before a meeting and it installs dependencies, downloads models, loads F5/Qwen, or performs live synthesis. The command takes minutes or fails due to network/model state.

**Why it happens:**
v1.8 intentionally isolated heavy voice work and made F5 the approved local profile. v1.9 should validate readiness, not perform model acquisition or training.

**How to avoid:**
Keep call-ready read-mostly:

- It may create the daily note and regenerate explicitly requested caches.
- It must not install packages, download models, train, or promote engines.
- It should report missing heavy assets with exact commands, not run them.
- It should benchmark or warm up only in a deliberate `--warmup` or `prepare` phase, not in every status check.
- Realtime loop start should use already prepared cache and approved voice profile.

**Warning signs:**
- `saymo call-ready` imports optional heavy packages just to render status.
- A status command takes longer than a few seconds on a warm machine.
- Missing model remediation starts with "downloading..." instead of a command to run later.

**Phase to address:**
Phase 36.

---

### Pitfall 11: F5 Latency Is Measured Outside the Real Call Path

**What goes wrong:**
F5 benchmark numbers look acceptable, but the live loop still misses the conversational window because startup, source lookup, cache validation, provider activation, mic switch, pre-speak delay, playback start, or mute recovery are not included.

**Why it happens:**
v1.8 measured voice generation and selector readiness. v1.9's user value is end-to-end call readiness, not just synthesis time.

**How to avoid:**
For launch and realtime evidence, record segmented latency:

- preflight time.
- source/cache validation time.
- provider activation and mic switch time.
- trigger/addressing/confirmation time.
- response resolution time.
- playback start and completion.
- mute recovery.

Set separate thresholds for pre-call preparation and live turn response. F5 generation on the hot path should be avoided; cache playback should be the normal realtime path.

**Warning signs:**
- "Latency passed" references only F5 per-clip synthesis.
- Scorecard cannot explain where a slow turn spent time.
- The realtime loop loads the TTS model after a trigger.

**Phase to address:**
Phase 39 and Phase 40.

---

### Pitfall 12: Multiple Control Processes Race on the Same Profile

**What goes wrong:**
Two daemon/listener instances read and write the same command queue and state file. A `stop`, `hard_disable`, or `takeover` command is consumed by the wrong process, replayed twice, or hidden by a stale state write.

**Why it happens:**
The local control design uses profile-scoped JSONL commands and `state.json`. This is simple and good for local control, but v1.9 backgrounding increases the chance of duplicate listeners.

**How to avoid:**
Add single-instance protection per profile:

- PID/lock file with stale lock detection.
- startup check that refuses a second live listener unless `--replace` is explicit.
- command IDs deduped in the consumer.
- state writes that include pid, launch source, monotonic sequence, and updated timestamp.
- status command that flags multiple matching processes.

**Warning signs:**
- `ps` finds more than one `saymo auto` or daemon command for `-p personal`.
- Audit events alternate between different pids.
- State `last_action` changes without a matching audit entry.

**Phase to address:**
Phase 38.

---

### Pitfall 13: Status UI Says "Green" Without Explaining Recovery

**What goes wrong:**
The user sees a menu item or terminal panel that says ready/not-ready, but cannot tell what to fix, which command to rerun, or whether a blocker is safety-critical.

**Why it happens:**
v1.7 remediation already produces actionable hints. A new daemon/menu layer can accidentally replace those with icons or generic labels.

**How to avoid:**
Status output should show:

- overall state: `ready`, `not_ready`, `blocked`, `degraded`, or `stale`.
- blocker category: source-data, audio-device, provider, launchd, daemon, cache, voice, handbrake, privacy.
- exact action and rerun command.
- last successful check timestamp and artifact path.
- explicit safety text for auto-answer, manual takeover, hard-disable, and non-cloned fallback.

**Warning signs:**
- "Fix provider" with no Chrome tab or rerun command.
- A menu icon changes color but the CLI status has no structured reason.
- Remediation hints are not reused in the new flow.

**Phase to address:**
Phase 36 for CLI output; Phase 38 for daemon/status surface.

---

### Pitfall 14: Safety-Soak Does Not Learn From Launch Failures

**What goes wrong:**
Post-call evidence captures trigger and playback regressions, but not launch failures: missing tab, stale cache, daemon unreachable, launchd crash loop, unsafe fallback block, or handbrake action latency.

**Why it happens:**
Existing safety-soak focuses on rehearsal and scorecard artifacts. v1.9 adds a new pre-call launch path and daemon health, which need to be represented in artifacts before soak can enforce them.

**How to avoid:**
Add launch/realtime fields to scorecards and soak:

- launch status and blocker codes.
- cache variant counts and stale/miss counts.
- daemon heartbeat age and hotkey registration status.
- provider readiness details.
- response route counts: cache hit, cache miss blocked, live fallback blocked, standup manual.
- handbrake actions and whether stop/takeover succeeded.
- privacy check result for raw transcript leakage.

**Warning signs:**
- A failed launch leaves no artifact.
- Safety-soak passes without seeing any v1.9 launch fields.
- Cache miss blocks are visible only in terminal logs.

**Phase to address:**
Phase 40.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| Reusing current `auto-preflight` readiness semantics unchanged | Fast implementation | `ready` can hide cache, hotkey, daemon, and launchd warnings | Only for rehearsal mode, never for call-ready/realtime-ready |
| Treating WAV existence as cache readiness | Simple file check | Stale voice/profile/source artifacts reach calls | Never for live-call output |
| Letting cache miss fall back to prepared standup automatically | Keeps old auto-mode behavior | Answers the wrong question in the user's cloned voice | Only on explicit manual speak, not automatic question handling |
| Checking only process existence for daemon status | Easy status command | Stale or dead control surface looks healthy | Never; require heartbeat and command probe |
| Printing raw transcripts in launchd logs | Easy debugging | Persistent privacy leak outside sanitized artifacts | Only in an explicit local debug mode with redaction warning |
| Using shell wrappers that depend on `.zshrc` | Works in terminal | LaunchAgent fails under launchd environment | Never for installed LaunchAgent |
| Making response-cache miss nonblocking | Lets launch pass with partial cache | Realtime loop loses fail-closed behavior | Only if realtime loop is disabled |
| Starting provider automation from generic "tab found" | Quicker provider check | Wrong tab/mic/mute state is missed | Acceptable for early diagnostics, not realtime-ready |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| Obsidian daily note | Create missing file and treat it as content-ready | Separate file existence, non-placeholder standup content, and prepared audio digest checks |
| Prepared standup cache | Check only today's WAV path | Require privacy-safe metadata matching profile, voice selector, source digest, and purpose |
| Response cache | Count any cached file as ready | Count fresh variants against current library and voice metadata; block automatic cache miss |
| F5 cloned voice | Load or synthesize during status | Status should inspect approval/metadata; generation belongs to prepare/cache commands |
| Chrome/Glip provider | `meeting_found=true` equals ready | Verify tab activation, BlackHole mic selection, real mic takeover, mute recovery, and latency |
| BlackHole routing | Check only device name exists | Verify capture input, playback output, provider-selected mic, and monitor route separately |
| Global hotkeys | `pynput` can create a listener once, therefore safe | Require running listener, Accessibility permission, fresh heartbeat, and command audit proof |
| LaunchAgent | Use terminal command line directly in plist | Use absolute `ProgramArguments`, explicit env, working dir, log paths, GUI domain commands |
| Live-control command queue | Append commands without single-instance control | Add lock/pid, command ID dedupe, state sequence, and stale heartbeat detection |
| Safety-soak | Reuse old scorecard fields only | Add launch health, daemon health, response-route, and unsafe-fallback fields |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|---|---|---|---|
| Cold-starting F5/TTS after trigger | First answer starts 5-10+ seconds late | Pre-generate cache; optional warmup before call; block hot-path synthesis | First live question |
| Live Ollama fallback in realtime | Long pause before answer; answer may be unreviewed | Keep `responses.live_fallback=false` for realtime; require cache or explicit approval | Any cache miss |
| Intent classifier before cache lookup | Adds about a second and can still miss | Keep optional and non-safety-critical; do not let it override deterministic skip | CPU-constrained machine |
| Provider checks only at launch | Tab/mic state changes mid-call | Revalidate before playback and record provider recovery failures | Long calls or tab switches |
| Excessive preflight work | User avoids running call-ready because it is slow | Split status from prepare; make heavy rebuild explicit | Daily standup workflow |
| Broad response triggers | Cache hit is fast but wrong | Require confidence thresholds, reviewable library, and replay examples | Real meeting questions |
| Crash-looping LaunchAgent | launchd throttles restart; hotkeys unavailable | Status surfaces last exit/restart count and log path | Bad env or missing venv |
| Large artifacts in logs | Slower status, hard-to-review evidence | Store counts/hashes and sanitized summaries | Multi-hour sessions |

## Security and Privacy Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Raw call transcript in LaunchAgent stdout/stderr | Persistent local privacy leak; accidental commit | Keep daemon logs operational only; sanitize scorecards |
| Writing real meeting artifacts under repo paths | Private data enters git status | Store raw audio/transcripts under `~/.saymo/`; `.planning/research` contains only research |
| Secrets in launchd env/logs | Tokens or credentials become visible in plist or logs | Do not put secrets in plists; use config/env names only and redact remediation |
| Non-cloned fallback speaks without label | User identity promise is broken | Live-call selector blocks non-cloned engines by default and audits any explicit override |
| Accessibility permission assumed | Hotkeys fail during emergency | Doctor/status must block or degrade clearly when permission/registration is unavailable |
| World-readable control/log files | Local user privacy leak | Create `~/.saymo/live_control` and `~/.saymo/logs` with user-only permissions where possible |
| Training on call recordings | Voice identity data reused without consent | Keep call audio for trigger/reliability review only; no voice training in v1.9 |
| Committing generated plist with personal paths | Machine-specific paths leak and break other users | Generate local plist from template; keep repo docs/examples generic |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---|---|---|
| One command prints too much | Operator misses the one blocker before a call | Start with concise ready/not-ready and top blockers, with `--verbose` details |
| Status does not show staleness | User trusts yesterday's green state | Always show last check time and stale threshold |
| Menu/status hides safety state | User cannot tell if auto-answer is off, takeover is active, or hard-disable is set | Surface these as first-class states, not secondary details |
| Recovery commands are missing | User fixes issue manually and forgets what to rerun | Every blocker has `action` and `rerun` |
| LaunchAgent install feels magical | User cannot recover after reboot/update | Provide `install`, `start`, `stop`, `restart`, `status`, `logs`, and `uninstall` commands |
| Preview and live routes look identical | User accidentally sends test audio into the call | Label monitor preview, BlackHole live route, and provider-selected mic separately |
| Hard-disable is buried | Emergency recovery is slow | Keep hard-disable visible in CLI/menu and hotkeys, with audit proof |
| "Ready" ignores content quality | Empty daily note or generic answer sounds awkward | Call-ready checks content presence, not just file existence |

## "Looks Done But Isn't" Checklist

- [ ] **Call-ready command:** Often missing stricter blocking semantics - verify cache, hotkeys, daemon, provider, voice, and source blockers fail the command.
- [ ] **Daily note bootstrap:** Often creates only an empty template - verify non-placeholder standup content or clear source-data blocker.
- [ ] **Prepared standup:** Often checks WAV existence only - verify metadata matches current note digest, profile, voice selector, and date.
- [ ] **Response cache:** Often reports `N>0` as enough - verify required variants are fresh and cache miss blocks automatic realtime speech.
- [ ] **Provider readiness:** Often stops at tab detection - verify activation, mic switch to BlackHole, real mic takeover, unmute/mute recovery, and latency.
- [ ] **Daemon/LaunchAgent:** Often reports process running - verify heartbeat, hotkey registration, command consume probe, audit event, and single instance.
- [ ] **Hotkeys:** Often pass in a terminal but not as LaunchAgent - verify Accessibility permission in the GUI session that runs the listener.
- [ ] **Realtime loop:** Often starts after preflight with warnings - verify it refuses to start unless `realtime_ready`.
- [ ] **Fallback policy:** Often preserves old standup fallback - verify automatic question cache miss is blocked and audited.
- [ ] **Evidence:** Often logs private transcript text - verify launch/realtime artifacts are sanitized and raw data stays under `~/.saymo/`.
- [ ] **Safety-soak:** Often remains v1.7-only - verify it fails missing v1.9 launch/daemon/cache/fallback fields.
- [ ] **Recovery:** Often has no operator path - verify every blocker includes action, rerun, and log/artifact path.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| Green launch with warnings | MEDIUM | Split readiness modes, update tests to make safety warnings blocking for call/realtime, rerun rehearsal and safety-soak |
| Unsafe cache miss spoke fallback | HIGH | Disable realtime auto-answer, audit affected session, change response policy to block misses, add regression test and soak rule |
| Stale cache played | MEDIUM | Regenerate prepared/response cache, add missing metadata fields, invalidate old sidecar schema, add stale-cache test |
| False positive answered | HIGH | Add sample to regression fixtures, tighten addressing/profile patterns, require soak pass before auto-answer |
| Handbrake unreachable | HIGH | Hard-disable auto-answer, stop daemon/listener, verify hotkey doctor and command probe, add heartbeat/single-instance checks |
| LaunchAgent env failure | LOW/MEDIUM | Inspect logs, fix absolute paths/env/working dir, `bootout`, `bootstrap`, `kickstart -k`, rerun daemon status |
| Provider mic switch failed | MEDIUM | Stop auto-answer, manually restore mic, run `takeover-check` and provider latency probe, update provider selectors/remediation |
| Raw transcript leaked to logs | MEDIUM/HIGH | Remove leaked artifact from repo/log collection, rotate/delete local log if needed, add redaction tests |
| Heavy model work in preflight | LOW/MEDIUM | Move work to explicit prepare/install command, add no-heavy-import smoke test for status path |
| Duplicate listeners | MEDIUM | Stop all but one process, add lock/pid detection, mark stale state invalid, add audit pid/sequence |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| Nonblocking warnings become green launch | Phase 36 | CLI tests where cache/hotkey/daemon warnings produce `not_ready` for call-ready mode |
| Cache miss speaks wrong fallback | Phase 36 and 39 | Unit tests for strict response policy; realtime UAT shows `cache_miss_blocked` |
| Stale voice/response metadata | Phase 36 | Metadata sidecar tests for prepared and response cache; stale config/note/profile invalidates readiness |
| False positives amplified | Phase 39 and 40 | Replay known false-positive sessions before realtime starts; safety-soak blocks regressions |
| Handbrake unreachable | Phase 38 and 39 | Daemon status requires heartbeat, hotkeys, command probe, and audit proof before realtime starts |
| LaunchAgent GUI/env failures | Phase 38 | Generated plist lint/smoke; `launchctl print`, logs, and kickstart documented and tested locally |
| Shallow provider readiness | Phase 37 | Provider readiness includes tab activation, mic switch, takeover, and latency evidence |
| Empty daily note treated as source-ready | Phase 36 | Tests for placeholder-only note blocking prepared audio readiness |
| Raw call data leaks | Phase 38 and 40 | Sanitization tests over launch logs, scorecards, and JSON evidence |
| Heavy model installs in status path | Phase 36 | Status tests prove no optional heavy imports/downloads/training |
| F5 latency measured outside call path | Phase 39 and 40 | Scorecard reports segmented end-to-end latency and threshold failures |
| Multiple control processes race | Phase 38 | Single-instance tests, stale lock handling, command ID dedupe |
| Status lacks recovery | Phase 36 and 38 | Every blocker includes category, action, rerun command, and artifact/log path |
| Safety-soak misses launch failures | Phase 40 | Soak fails missing launch/daemon/cache/fallback fields and worsened launch metrics |

## Research Flags for Roadmap

- Phase 36 needs detailed design for readiness modes and which checks are blocking in `call_ready` vs `realtime_ready`.
- Phase 37 needs focused research only if provider automation selectors have drifted; otherwise use existing Glip/Chrome provider patterns.
- Phase 38 needs implementation-specific research for LaunchAgent install/status commands in the user's GUI session, especially Accessibility permission and `launchctl` domain handling.
- Phase 39 needs careful tests around response policy so old auto-mode fallback behavior does not leak into the new realtime loop.
- Phase 40 needs schema design for sanitized launch/realtime evidence before safety-soak can enforce it.

## Sources

- `.planning/PROJECT.md` - v1.9 goals, active requirements, safety/privacy decisions, out-of-scope boundaries.
- `.planning/STATE.md` - current milestone position, risks, selected priority order.
- `docs/LIVE-CONTROL-HANDBRAKE.md` - operator controls, hotkey assumptions, safety rules.
- `docs/VOICE-NATURALNESS.md` - cloned voice generation constraints, reference/sample quality, verification expectations.
- `saymo/analysis/remediation.py` - current remediation categories and rerun commands.
- `saymo/analysis/live_control.py` - command queue, state file, audit model, hotkey diagnostics.
- `saymo/commands/tests.py` - `auto-preflight`, rehearsal, provider latency, cache preparation, scorecard, safety-soak, hotkey doctor, takeover check.
- `saymo/commands/core.py` and `saymo/commands/__init__.py` - live auto loop, handbrake handling, response-cache and fallback decisions.
- `saymo/analysis/response_cache.py` and `saymo/analysis/cache_metadata.py` - response-cache behavior and privacy-safe voice metadata sidecars.
- `scripts/ensure_obsidian_daily_note.py` and `tests/scripts/test_ensure_obsidian_daily_note.py` - daily-note creation behavior and limits.
- `config.example.yaml` - voice selector, hotkeys, live tuning, response-cache, and fallback defaults.
- macOS `launchd.plist(5)` and `launchctl(1)` local manpages - LaunchAgent plist keys, GUI/user domains, bootstrap/bootout/kickstart/print behavior.
- Apple Developer archive, "Creating Launch Daemons and Agents": https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html

---
*Pitfalls research for: Saymo v1.9 Call Launch Readiness*
*Researched: 2026-07-08*

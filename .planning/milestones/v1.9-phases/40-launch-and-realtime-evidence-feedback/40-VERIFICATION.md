---
phase: 40-launch-and-realtime-evidence-feedback
verified: 2026-07-08T19:38:36Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "Live macOS call-ready evidence smoke"
    expected: "call-ready writes a sanitized artifact with real provider/audio/daemon rows, log paths, and rerun commands for the user's GUI session."
    why_human: "Chrome tab state, Accessibility permissions, LaunchAgent state, and BlackHole devices depend on the local macOS GUI session."
  - test: "Live realtime decision evidence smoke"
    expected: "A controlled live/rehearsal run writes realtime-decisions.jsonl rows that scorecard reports as launch/cache/provider/fallback/handbrake/playback/stop evidence without raw meeting content."
    why_human: "Actual provider audio, mute state, and call timing cannot be proven by unit tests."
  - test: "Live safety-soak rerun from real artifacts"
    expected: "Safety-soak passes safe real evidence and fails unsafe real launch/realtime evidence with actionable remediation."
    why_human: "The automated suite uses deterministic fixtures, not a real call provider and audio route."
---

# Phase 40: Launch and Realtime Evidence Feedback Verification Report

**Phase Goal:** User can inspect sanitized launch and realtime evidence, see health signals in scorecards, and run safety-soak gates that fail on v1.9 launch or runtime safety regressions.
**Verified:** 2026-07-08T19:38:36Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

Automated verification passes for all five EVID requirements. Status is `human_needed` only because the remaining end-to-end smoke depends on the user's macOS GUI session, provider tab, BlackHole routing, Accessibility permissions, LaunchAgent state, and live audio behavior.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can inspect sanitized launch-readiness artifacts containing checks, blocker categories, cache counts, voice/cache fingerprints, provider status, daemon status, mode, paths, and rerun commands. | VERIFIED | `write_launch_readiness_artifact()` preserves `report.to_dict()` and adds `schema_version`, `evidence_kind`, `mode`, `artifact_path`, `created_at` (`saymo/analysis/launch_readiness.py:188`). `LaunchEvidence` normalizes counts, failed labels, categories, cache, voice, provider, daemon, paths, reruns, and checks (`saymo/analysis/launch_evidence.py:37`, `saymo/analysis/launch_evidence.py:245`). `call-ready --output` is wired while `--json` prints legacy report JSON only (`saymo/commands/call_ready.py:41`). |
| 2 | User can load and summarize sanitized realtime JSONL for launch start/end/block, cache hit/miss, fallback/provider/handbrake blocks, playback attempts, stop reasons, and malformed rows. | VERIFIED | `RealtimeEventSummary` has all required counters (`saymo/analysis/realtime_events.py:77`). `summarize_realtime_decision_events()` counts launch/cache/block/playback/stop evidence and malformed rows (`saymo/analysis/realtime_events.py:123`). JSONL loading reconstructs allowlisted `RealtimeDecisionEvent` payloads and skips malformed rows (`saymo/analysis/realtime_events.py:161`). |
| 3 | User can see optional launch/realtime metrics in session/rehearsal scorecards while old scorecards remain compatible. | VERIFIED | Scorecard metrics dataclasses cover launch readiness, daemon, cache, provider, realtime labels/sources, stop reasons, and artifacts (`saymo/analysis/session_scorecard.py:70`). Rehearsal and regression builders accept optional `launch_json`/`realtime_jsonl` (`saymo/analysis/session_scorecard.py:150`). JSON omits unavailable metrics for old compatibility (`saymo/analysis/session_scorecard.py:363`). Markdown renders v1.9 evidence only when supplied (`saymo/analysis/session_scorecard.py:617`). CLI flags and aliases are wired (`saymo/commands/tests.py:1020`). |
| 4 | User can run safety-soak against v1.9 scorecard evidence and fail on unsafe playback, stale cache, missing daemon readiness, provider blockers, fallback blocks, or unapproved fallback conditions. | VERIFIED | `build_safety_soak_report()` consumes `SessionScorecard` only (`saymo/analysis/safety_soak.py:96`). v1.9 totals are not drift metrics (`saymo/analysis/safety_soak.py:14`). Violations are derived from `launch_metrics`, `realtime_metrics`, and existing unsafe playback metrics (`saymo/analysis/safety_soak.py:383`, `saymo/analysis/safety_soak.py:461`). Safety-soak CLI passes optional evidence into rehearsal scorecard construction (`saymo/commands/tests.py:1138`). |
| 5 | User can troubleshoot failures from sanitized evidence with artifact/log paths and exact rerun commands. | VERIFIED | Scorecard remediation includes failed labels, categories, artifact path, log paths, blocker counts, and rerun chains (`saymo/analysis/remediation.py:115`, `saymo/analysis/remediation.py:227`). Safety-soak remediation prints scorecard-first and soak rerun commands (`saymo/analysis/remediation.py:185`, `saymo/analysis/remediation.py:316`). Soak Markdown includes v1.9 next actions (`saymo/analysis/safety_soak.py:269`). Operator docs contain exact workflow commands and privacy/read-only limits (`docs/LAUNCH-REALTIME-EVIDENCE.md:1`). |

**Score:** 5/5 truths verified by automated checks.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `saymo/analysis/launch_evidence.py` | Read-only launch artifact loader and summary | VERIFIED | Exports `LaunchEvidence`, `load_launch_evidence`, `summarize_launch_evidence`; no provider/audio/launchd mutation calls found. |
| `saymo/analysis/launch_readiness.py` | Enriched but backward-compatible artifact writer | VERIFIED | Adds schema metadata to root JSON while keeping readiness root fields. Existing sanitizer sentinels are confined to this legacy module. |
| `saymo/analysis/realtime_events.py` | JSONL loader and summary helpers | VERIFIED | Loads allowlisted rows, skips malformed JSON, summarizes required labels/sources/outcomes. |
| `saymo/analysis/session_scorecard.py` | Optional launch/realtime scorecard metrics | VERIFIED | Metrics are loaded only when paths are supplied and omitted from JSON when unavailable. |
| `saymo/analysis/safety_soak.py` | v1.9 safety-soak totals and violations | VERIFIED | Uses scorecard metrics, not raw launch/realtime readers; old baselines remain neutral. |
| `saymo/analysis/remediation.py` | Troubleshooting hints | VERIFIED | Uses sanitized scorecard/soak fields and renders rerun commands. |
| `saymo/commands/call_ready.py` | call-ready output wiring | VERIFIED | `--output` writes artifact; `--json` remains pure report JSON. |
| `saymo/commands/tests.py` | scorecard and soak CLI options | VERIFIED | Wires `--launch-json`/`--launch-readiness` and `--realtime-jsonl`/`--realtime`. |
| `docs/LAUNCH-REALTIME-EVIDENCE.md` | Operator workflow docs | VERIFIED | Documents call-ready, session-scorecard, safety-soak commands, aliases, privacy, and live risk. |
| Phase 40 tests | Focused contract coverage | VERIFIED | Focused suite passes: `58 passed in 2.08s`; static docs/guard tests pass: `10 passed in 0.02s`. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `call_ready.py` | `write_launch_readiness_artifact()` | `--output` path | WIRED | `artifact_path = write_launch_readiness_artifact(report, output)` at `saymo/commands/call_ready.py:41`. |
| `launch_readiness.py` | `launch_evidence.py` loader contract | root JSON shape | WIRED | Writer preserves root `report.to_dict()` and adds optional metadata. Loader reads `checks`, counts, metadata, paths, reruns. |
| `session_scorecard.py` | `load_launch_evidence()` | optional `launch_json` | WIRED | Imported and called at `saymo/analysis/session_scorecard.py:12` and `saymo/analysis/session_scorecard.py:262`. |
| `session_scorecard.py` | `summarize_realtime_decision_events()` | optional `realtime_jsonl` | WIRED | Imported and called at `saymo/analysis/session_scorecard.py:15` and `saymo/analysis/session_scorecard.py:311`. |
| `commands/tests.py` | scorecard builders | CLI evidence flags | WIRED | Flags are passed into rehearsal/regression scorecard construction at `saymo/commands/tests.py:1063` and `saymo/commands/tests.py:1094`. |
| `safety_soak.py` | `SessionScorecard.launch_metrics` / `realtime_metrics` | scorecard-only gate | WIRED | Violations read only `scorecard.launch_metrics` and `scorecard.realtime_metrics`; no direct evidence loader imports found. |
| `commands/tests.py` | safety-soak scorecard construction | rehearsal evidence pass-through | WIRED | Evidence paths are passed before soak aggregation at `saymo/commands/tests.py:1191`. |
| `remediation.py` | scorecard and soak reports | hint rendering | WIRED | `hints_from_scorecard()` and `hints_from_safety_soak()` render v1.9 artifacts and reruns. |
| `tests/test_realtime_static_guards.py` | Phase 40 modules | static privacy/mutation guard | WIRED | Guards ban private field names and provider/audio/launchd mutation calls across evidence modules. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| EVID-01 | 40-01 | Sanitized launch artifact with checks, categories, cache, voice/cache fingerprints, provider/daemon status, mode, rerun commands | SATISFIED | Launch writer, loader, call-ready wiring, focused tests. |
| EVID-02 | 40-02 | Sanitized realtime JSONL loading and summary | SATISFIED | Realtime loader/summary, malformed-row handling, labels/sources/outcomes, focused tests. |
| EVID-03 | 40-02 | Optional scorecard launch/realtime metrics and old JSON compatibility | SATISFIED | Metric dataclasses, optional loaders, JSON/Markdown rendering, CLI flags, compatibility tests. |
| EVID-04 | 40-03 | Safety-soak v1.9 gates from scorecard metrics only | SATISFIED | v1.9 violations, safe evidence pass tests, old-baseline neutrality, no direct raw evidence readers in soak. |
| EVID-05 | 40-04 | Troubleshooting/docs/static guards with paths and rerun commands | SATISFIED | Remediation hints, soak next actions, operator docs, static privacy/mutation guards. |

No orphaned Phase 40 requirements were found in `.planning/REQUIREMENTS.md`; EVID-01 through EVID-05 are all mapped to Phase 40.

### Automated Checks

| Command | Result |
|---|---|
| `uv run pytest tests/analysis/test_launch_readiness.py tests/analysis/test_realtime_events.py tests/analysis/test_session_scorecard.py tests/analysis/test_safety_soak.py tests/analysis/test_remediation.py tests/test_call_ready_cli.py tests/test_session_scorecard_cli.py tests/test_safety_soak_cli.py -q` | 58 passed in 2.08s |
| `uv run pytest tests/analysis/test_realtime_gate.py tests/analysis/test_realtime_policy.py tests/analysis/test_realtime_events.py tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_live_control_cli.py tests/test_realtime_static_guards.py tests/test_call_control_cli.py -q` | 108 passed in 3.00s |
| `uv run pytest tests/test_auto_qa_flow.py tests/test_call_ready_cli.py tests/test_takeover_check.py tests/analysis/test_launch_readiness.py -q` | 82 passed in 3.52s |
| `uv run pytest tests/test_realtime_static_guards.py tests/test_launch_realtime_evidence_docs.py -q` | 10 passed in 0.02s |
| `uv run pytest -q` | 540 passed in 7.28s |
| Static privacy guard from `40-VALIDATION.md` | passed |
| Static provider/audio/launchd mutation guard from `40-VALIDATION.md` | passed |
| `git diff --check` | passed |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| None blocking | - | - | - | Anti-pattern scan found only legitimate empty-default returns and placeholder-readiness test fixture strings; no implementation stubs or blocker placeholders found. |

### Human Verification Required

#### 1. Live macOS call-ready evidence smoke

**Test:** Run `uv run saymo call-ready -p standup --provider glip --output ~/.saymo/live_control/standup/call-ready.json` in the user's normal GUI session.
**Expected:** Artifact is readable and sanitized, with real provider/audio/daemon rows, log paths, artifact path, and rerun commands.
**Why human:** Chrome tab state, Accessibility permissions, LaunchAgent state, and BlackHole devices depend on the local macOS GUI session.

#### 2. Live realtime decision evidence smoke

**Test:** Run a controlled live/rehearsal flow that writes `~/.saymo/live_control/standup/realtime-decisions.jsonl`, then run `uv run saymo session-scorecard -p standup --launch-json ~/.saymo/live_control/standup/call-ready.json --realtime-jsonl ~/.saymo/live_control/standup/realtime-decisions.jsonl --rehearsal <rehearsal.json>`.
**Expected:** Scorecard reports launch/cache/provider/fallback/handbrake/playback/stop evidence without raw meeting content.
**Why human:** Actual provider audio, mute state, call timing, and live realtime behavior cannot be proven by deterministic unit tests.

#### 3. Live safety-soak rerun from real artifacts

**Test:** Save a scorecard JSON from real artifacts and run `uv run saymo safety-soak -p standup --scorecard-json <scorecard.json>`.
**Expected:** Safe real evidence passes; unsafe real launch/realtime evidence fails with actionable remediation and rerun commands.
**Why human:** The automated suite uses fixtures, not a real call provider and audio route.

### Gaps Summary

No automated gaps found. The phase goal is achieved at the code, artifact, CLI, test, and documentation levels. Remaining risk is live-environment validation only: provider tab/mute behavior, BlackHole routing, Accessibility permissions, LaunchAgent state, and actual call audio must be checked in the user's macOS GUI session before relying on this in a real meeting.

---

_Verified: 2026-07-08T19:38:36Z_
_Verifier: Claude (gsd-verifier)_

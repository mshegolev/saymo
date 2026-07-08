---
phase: 40-launch-and-realtime-evidence-feedback
type: context
status: ready_for_research
created: 2026-07-08
autonomous: true
requirements: [EVID-01, EVID-02, EVID-03, EVID-04, EVID-05]
depends_on:
  - 36-call-ready-preflight-and-cache-gate
  - 37-provider-and-audio-remediation
  - 38-local-call-control-daemon-and-launchagent
  - 39-fail-closed-realtime-meeting-loop
---

# Phase 40 Context: Launch and Realtime Evidence Feedback

## Goal

Turn v1.9 launch-readiness and realtime decision evidence into sanitized
operator-facing artifacts, scorecard signals, safety-soak gates, and
troubleshooting guidance.

## Approved Design Direction

Phase 40 should consume the contracts created in Phases 36-39 rather than
adding new realtime behavior:

- `LaunchReadinessReport.to_dict()` remains the source of truth for launch
  checks, blocker counts, cache/voice/provider/daemon metadata, and rerun
  commands.
- `RealtimeDecisionEvent` JSONL remains the source of truth for realtime
  spoke/skipped/blocked decision evidence.
- `SessionScorecard` should summarize launch health, daemon/control state,
  cache hit/miss and fallback-block counts, provider drift, handbrake blocks,
  and unsafe playback from sanitized launch/realtime evidence.
- `SafetySoakReport` should fail when v1.9 launch or realtime evidence proves
  unsafe conditions such as stale cache, missing daemon readiness, provider
  blockers, unsafe fallback, or automatic playback that bypassed safety gates.
- Troubleshooting output should connect the user to sanitized artifact paths,
  failed labels, remediation categories, and exact rerun commands.

Phase 40 must not weaken the Phase 39 fail-closed runtime loop. Evidence is a
feedback layer over already-sanitized artifacts.

## Grey Areas Resolved By Assumption

### Evidence Shape

- Launch evidence may be a richer schema or wrapper around
  `LaunchReadinessReport.to_dict()`, but it must not duplicate readiness logic.
- Realtime evidence may be read from `realtime-decisions.jsonl` and summarized
  by label/outcome/source, not by raw transcript or generated text.
- Artifact paths are useful and allowed when sanitized local filesystem paths
  help the operator troubleshoot.

### Scorecard Scope

- Existing scorecard APIs should grow typed v1.9 launch/realtime metrics rather
  than introducing a parallel report family.
- Scorecards may accept optional launch and realtime evidence paths/roots.
- Rehearsal and existing regression scorecards should stay backward compatible
  when no v1.9 evidence is provided.

### Safety-Soak Scope

- Safety soak should continue accepting scorecards and baselines.
- New v1.9 violations should be derived from sanitized scorecard metrics, not
  by rereading raw meeting content.
- A failed gate should explain which sanitized condition failed and which source
  artifact to inspect.

### Troubleshooting Scope

- Troubleshooting can be a renderer/helper or CLI output extension, but it
  should remain local and deterministic.
- It should favor existing remediation hints from launch readiness and
  scorecards over new prose-only heuristics.

## Existing Building Blocks

- `saymo.analysis.launch_readiness`
  - `LaunchReadinessReport`, `LaunchReadinessCheck`,
    `write_launch_readiness_artifact()`, grouped remediation rendering.
- `saymo.analysis.realtime_events`
  - `RealtimeDecisionEvent`, `realtime_event_log_path()`,
    `append_realtime_decision_event()`.
- `saymo.analysis.session_scorecard`
  - `SessionScorecard`, trigger/playback/safety metrics, JSON/Markdown
    renderers, live-control audit ingestion.
- `saymo.analysis.safety_soak`
  - aggregate soak reports, violations, drift metrics, CLI export support.
- `saymo.analysis.remediation`
  - hints from launch readiness and scorecards.
- `saymo.commands.core`
  - `call-ready`, `session-scorecard`, `safety-soak`, and current output path
    options.

## Required User-Facing Outcomes

1. User can inspect a sanitized launch-readiness artifact with checks, blocker
   categories, cache counts, voice/cache fingerprints, provider status, daemon
   status, mode, artifact paths, and rerun commands.
2. User can inspect sanitized realtime events for launch start/end, cache
   hits/misses, fallback blocks, provider failures, playback attempts,
   handbrake actions, and stop reasons.
3. User can see launch health, daemon/control availability, cache hit/miss
   counts, unsafe fallback blocks, and provider drift in rehearsal/session
   scorecards.
4. User can run safety-soak against v1.9 launch/realtime evidence and get a
   failed gate for unsafe playback, stale cache, missing daemon readiness,
   provider blockers, or unapproved fallback conditions.
5. User can troubleshoot failures from sanitized evidence that includes
   relevant log/artifact paths and next rerun commands.

## Guardrails

- Do not store or render raw transcripts, generated answers, daily-note body,
  audio bytes, or secrets in launch, realtime, scorecard, soak, or
  troubleshooting evidence.
- Do not add Chrome, provider, microphone, audio-route, playback, recording, or
  launchd mutations to evidence readers or renderers.
- Do not make scorecards or safety-soak depend on a live provider/browser.
- Do not make Phase 40 bypass or relax Phase 39 fail-closed behavior.
- Preserve existing CLI behavior when new evidence paths are not supplied.
- Keep artifacts local-by-default and deterministic under test.

## Suggested Module Boundaries

- `saymo.analysis.launch_readiness` or a focused `launch_evidence` helper:
  normalized launch artifact schema and loader over existing readiness reports.
- `saymo.analysis.realtime_events`:
  event loader and summary helpers over existing JSONL.
- `saymo.analysis.session_scorecard`:
  v1.9 launch/realtime metrics, JSON/Markdown fields, and optional evidence
  ingestion.
- `saymo.analysis.safety_soak`:
  v1.9 safety violations derived from scorecard metrics.
- `saymo.analysis.remediation`:
  troubleshooting hints from launch/realtime/scorecard evidence.
- `saymo.commands.core`:
  minimal CLI option wiring and output rendering.

## Validation Strategy

- Unit tests for sanitized launch artifact schema/load/render behavior.
- Unit tests for realtime event loading/summarization without raw private
  content.
- Scorecard tests proving v1.9 launch/realtime metrics appear in JSON and
  Markdown while existing scorecard inputs remain backward compatible.
- Safety-soak tests proving unsafe v1.9 conditions fail the gate and safe
  evidence passes.
- CLI tests for artifact paths, rerun commands, and troubleshooting output.
- Static guards proving evidence readers do not import or call provider/audio
  mutation APIs and do not expose private field names.

## Deferred Ideas

- A native visual dashboard over launch/realtime evidence.
- Automatic provider repair or route mutation based on evidence.
- Cloud sync or sharing of artifacts.
- Raw transcript-based post-call analytics.

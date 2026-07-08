# Phase 39 Plan Check: Fail-Closed Realtime Meeting Loop

**Checked:** 2026-07-08
**Verdict:** PASS
**Plans checked:** 39-01, 39-02, 39-03, 39-04, 39-05

## Summary

The revised Phase 39 plans are goal-backward complete and ready for execution.
REAL-01 through REAL-06 all have explicit plan ownership, the five plans run in
a valid sequential dependency chain, each plan stays inside a small scope, every
task has automated RED/GREEN validation, and the locked Phase 39 decisions are
preserved.

The previous blocker is resolved. The source-text privacy guards no longer ban
the required `transcript_window` policy input parameter. The revised validation
and Plan 39-05 now require privacy at the serialized decision/event boundary:
tests must prove no event or decision payload contains a `transcript_window` key,
raw transcript value, generated answer text, daily-note content, audio bytes, or
secrets.

## Source Context Read

- `.planning/ROADMAP.md` Phase 39 section
- `.planning/REQUIREMENTS.md` REAL-01..REAL-06
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-CONTEXT.md`
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-RESEARCH.md`
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-VALIDATION.md`
- all five `39-0*-PLAN.md` files
- previous `.planning/phases/39-fail-closed-realtime-meeting-loop/39-PLAN-CHECK.md`
- repo guidance in `CLAUDE.md`

## Previous Blocker Resolution

| Check | Result |
|-------|--------|
| Plan 39-02 still requires `resolve_realtime_response_decision(..., transcript_window: str, ...)` | PASS |
| `39-VALIDATION.md` static privacy guard omits `transcript_window` from source-text bans | PASS |
| Plan 39-05 validation commands omit `transcript_window` from source-text bans | PASS |
| Plan 39-05 tests require serialized event payloads to exclude a `transcript_window` key and raw transcript values | PASS |
| Plan 39-05/validation still ban unsafe serialized/source fields such as `raw_transcript`, `generated_answer`, `answer_text`, `audio_bytes`, and `PRIVATE_` | PASS |

Concrete resolution evidence:

- `39-VALIDATION.md` states the policy helper may still use
  `transcript_window` as an input parameter name.
- `39-VALIDATION.md` requires privacy tests proving no serialized decision or
  event payload contains a `transcript_window` key or raw transcript value.
- Plan 39-05 carries the same scoped privacy policy and final automated guards.

## Requirement Coverage

| Requirement | Plans | Covering tasks | Status |
|-------------|-------|----------------|--------|
| REAL-01 | 39-01 | Launch gate RED tests; shared realtime launch gate implementation | Covered |
| REAL-02 | 39-01 | Alias/shared `_auto()` path tests; no unsafe bypass guard | Covered |
| REAL-03 | 39-02, 39-03 | Cache-only automatic policy; provider and handbrake pre-play blockers | Covered |
| REAL-04 | 39-04 | Manual standup route and automatic cache-miss separation | Covered |
| REAL-05 | 39-05 | Sanitized event schema, event emission, static privacy guards | Covered |
| REAL-06 | 39-02, 39-05 | Deterministic skip before cache/classifier; handbrake boundary regressions | Covered |

No relevant Phase 39 requirement from `.planning/REQUIREMENTS.md` is missing from
plan frontmatter.

## Plan Summary

| Plan | Wave | Depends on | Tasks | Files | Status |
|------|------|------------|-------|-------|--------|
| 39-01 | 1 | none | 2 | 4 | Valid |
| 39-02 | 2 | 39-01 | 2 | 4 | Valid |
| 39-03 | 3 | 39-02 | 2 | 5 | Valid |
| 39-04 | 4 | 39-03 | 2 | 4 | Valid |
| 39-05 | 5 | 39-04 | 2 | 7 | Valid |

Dependencies are linear and acyclic:

`39-01 -> 39-02 -> 39-03 -> 39-04 -> 39-05`

The file overlap is intentional and sequential. Ownership is split by behavior:
startup gate, cache-only policy, runtime provider/handbrake blockers, manual
standup separation, then sanitized events/final guards.

## Specific Re-checks

| Area | Result |
|------|--------|
| Sequential ownership/no conflict | PASS |
| TDD commands | PASS |
| Strict launch gate/no bypass | PASS |
| Fail-closed automatic cache miss | PASS |
| Fail-closed live fallback | PASS |
| Fail-closed standup fallback | PASS |
| Explicit manual standup separation | PASS |
| Provider rechecks before playback | PASS |
| Handbrake rechecks before resolution and playback | PASS |
| Sanitized events without Phase 40 reporting | PASS |

## Key Links Planned

- `saymo/commands/core.py` runs the realtime launch gate before realtime setup.
- `saymo/analysis/realtime_gate.py` delegates startup readiness to
  `collect_launch_readiness()` and remediation rendering to
  `render_launch_readiness()`.
- `saymo/commands/core.py` routes automatic answers through
  `resolve_realtime_response_decision()`.
- `saymo/analysis/realtime_policy.py` builds `ResponseCache` with cloned-voice
  metadata and blocks cache miss, stale metadata, disabled cache, live fallback,
  and deterministic skip paths.
- `saymo/commands/core.py` runs provider and handbrake blockers before
  automatic playback with strict provider fallback disabled.
- `saymo/commands/core.py` routes explicit manual speak through
  `resolve_manual_standup_decision()` and keeps it separate from automatic
  cache-miss handling.
- `saymo/commands/core.py` appends sanitized realtime decision events without
  importing or implementing Phase 40 scorecards, safety-soak, or reporting.

## Nyquist Compliance

`workflow.nyquist_validation` is enabled, `39-RESEARCH.md` contains a Validation
Architecture section, and `39-VALIDATION.md` exists. Dimension 8 applies.

| Task | Plan | Wave | Automated command | Status |
|------|------|------|-------------------|--------|
| 1 | 39-01 | 1 | RED pytest for launch gate and auto flow | PASS |
| 2 | 39-01 | 1 | Focused pytest, call-ready regression, no-bypass guard, mutation guard | PASS |
| 1 | 39-02 | 2 | RED pytest for realtime policy and auto flow | PASS |
| 2 | 39-02 | 2 | Focused pytest, launch regression, fail-closed guard, privacy guard | PASS |
| 1 | 39-03 | 3 | RED pytest for provider and handbrake blockers | PASS |
| 2 | 39-03 | 3 | Focused pytest, policy/call-ready/live-control regression, mutation guard | PASS |
| 1 | 39-04 | 4 | RED pytest for manual standup separation | PASS |
| 2 | 39-04 | 4 | Focused pytest, gate/call-ready/live-control regression, standup separation guard | PASS |
| 1 | 39-05 | 5 | RED pytest for events, policy, auto flow, static guards | PASS |
| 2 | 39-05 | 5 | Focused suite, safety regression suite, full pytest, static guards | PASS |

Sampling continuity passes: every implementation task has automated validation,
and no task relies on watch mode, browser E2E suites, or delay-based validation.
No `MISSING` automated commands or Wave 0 gaps remain in the executable plans.

## Context Compliance

- Strict launch gate: honored by 39-01 through default
  `collect_launch_readiness()` integration and no-bypass tests.
- Cache-only automatic answers: honored by 39-02 through metadata-aware
  `ResponseCache` construction and blocked cache-miss/live-fallback tests.
- Manual standup stays explicit: honored by 39-04 through
  `manual-standup-requested` routing and cache-miss separation.
- Provider and handbrake rechecks before playback: honored by 39-03 through
  pre-resolution, pre-play, and strict provider fallback tests.
- Sanitized evidence without Phase 40 reporting: honored by 39-05 through
  minimal realtime events plus static Phase 40 scope guards.
- Deferred ideas excluded: no plan implements guarded live LLM/TTS fallback,
  automatic provider repair, scorecards, safety-soak gates, or Phase 40
  reporting.

## Structured Issues

```yaml
issues: []
```

## Recommendation

Plans verified. Run `/gsd:execute-phase 39` to proceed.

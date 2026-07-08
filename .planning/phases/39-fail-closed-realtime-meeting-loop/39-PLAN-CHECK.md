# Phase 39 Plan Check: Fail-Closed Realtime Meeting Loop

**Checked:** 2026-07-08
**Verdict:** BLOCK
**Plans checked:** 39-01, 39-02, 39-03, 39-04, 39-05

## Summary

The five plans are mostly goal-backward complete: every REAL-01..REAL-06
requirement has test ownership and implementation ownership, the plans are
sequentially dependent, scopes do not duplicate in a conflicting way, and the
locked Phase 39 decisions are reflected in the plan tasks.

Execution should not start yet because the final validation design is
self-contradictory. Plan 39-02 requires `realtime_policy.py` to expose a
`transcript_window` parameter, while Plan 39-05 and `39-VALIDATION.md` require a
static privacy guard that fails if the literal string `transcript_window` exists
in `realtime_policy.py`. A correct implementation cannot satisfy both.

## Source Context Read

- `.planning/ROADMAP.md` Phase 39 section
- `.planning/REQUIREMENTS.md` REAL-01..REAL-06
- `.planning/PROJECT.md`
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-CONTEXT.md`
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-RESEARCH.md`
- `.planning/phases/39-fail-closed-realtime-meeting-loop/39-VALIDATION.md`
- all five `39-0*-PLAN.md` files
- relevant current seams in `saymo/commands/core.py`,
  `saymo/commands/__init__.py`, `saymo/analysis/launch_readiness.py`,
  `saymo/analysis/launch_cache.py`, `saymo/analysis/response_cache.py`,
  `saymo/analysis/live_control.py`, and `tests/test_auto_qa_flow.py`

## Requirement Coverage

| Requirement | Plans | Concrete tests | Implementation ownership | Status |
|-------------|-------|----------------|--------------------------|--------|
| REAL-01 | 39-01 | RED launch gate tests prove blocked readiness exits before cached audio stat, device lookup, provider lookup, capture, STT, hotkeys, and command loops. | `saymo/analysis/realtime_gate.py`, `saymo/commands/core.py` | Covered |
| REAL-02 | 39-01 | RED CLI/auto tests prove `saymo auto` and any realtime alias share the same gate and no unsafe bypass option appears. | `saymo/commands/core.py` alias and `_auto` integration | Covered |
| REAL-03 | 39-02, 39-03 | Cache hit/miss/stale/fallback tests plus provider and handbrake blocker tests. | `saymo/analysis/realtime_policy.py`, `saymo/analysis/realtime_gate.py`, `saymo/commands/core.py`, `saymo/commands/__init__.py` | Covered |
| REAL-04 | 39-04 | Manual standup separation tests prove explicit manual playback and automatic cache-miss blocking. | `saymo/analysis/realtime_policy.py`, `saymo/commands/core.py` | Covered |
| REAL-05 | 39-05 | Sanitized event tests and static privacy/scope guards are planned. | `saymo/analysis/realtime_events.py`, `saymo/analysis/realtime_policy.py`, `saymo/commands/core.py` | Covered, but final validation is blocked |
| REAL-06 | 39-02, 39-05 | Deterministic skip tests, classifier boundary tests, and handbrake boundary tests are planned. | `saymo/analysis/realtime_policy.py`, `saymo/commands/core.py` | Covered |

## Plan Dependency and Scope Check

| Plan | Wave | Depends on | Tasks | Files | Scope status |
|------|------|------------|-------|-------|--------------|
| 39-01 | 1 | none | 2 | 4 | OK |
| 39-02 | 2 | 39-01 | 2 | 4 | OK |
| 39-03 | 3 | 39-02 | 2 | 5 | OK |
| 39-04 | 4 | 39-03 | 2 | 4 | OK |
| 39-05 | 5 | 39-04 | 2 | 7 | OK |

Dependencies are linear and acyclic: 39-01 -> 39-02 -> 39-03 -> 39-04 ->
39-05. No plan references a missing or future dependency.

## Context Compliance

- Strict launch gate: honored by 39-01 through default `collect_launch_readiness()`
  integration and no-bypass tests.
- Cache-only automatic answers: honored by 39-02 through metadata-aware
  `ResponseCache` construction and blocked cache-miss/live-fallback tests.
- Manual standup stays explicit: honored by 39-04 through
  `manual-standup-requested` routing and cache-miss separation.
- Provider and handbrake rechecks before playback: honored by 39-03 through
  pre-resolution, pre-play, and strict provider fallback tests.
- Sanitized evidence without Phase 40 scorecards/safety-soak: intended by
  39-05, but blocked by the validation-command contradiction below.
- Deferred ideas excluded: no plan implements guarded live LLM/TTS fallback,
  automatic provider repair, scorecards, safety-soak gates, or Phase 40
  reporting.

## Blocking Issue

### 1. Final privacy guard cannot pass if Plan 39-02 is implemented as written

**Dimension:** verification_feasibility / nyquist_compliance
**Severity:** blocker
**Plan:** 39-05
**Task:** 2

Evidence:

- Plan 39-02 defines the new policy interface with
  `transcript_window: str` in `resolve_realtime_response_decision()`:
  `.planning/phases/39-fail-closed-realtime-meeting-loop/39-02-PLAN.md:124`.
- Plan 39-02 tells the executor to implement `saymo.analysis.realtime_policy`
  with that contract:
  `.planning/phases/39-fail-closed-realtime-meeting-loop/39-02-PLAN.md:187`.
- Plan 39-05 final verification rejects the literal string
  `transcript_window` in `saymo/analysis/realtime_policy.py`:
  `.planning/phases/39-fail-closed-realtime-meeting-loop/39-05-PLAN.md:195`.
- `39-VALIDATION.md` carries the same static privacy guard:
  `.planning/phases/39-fail-closed-realtime-meeting-loop/39-VALIDATION.md:73`.

Why this blocks execution:

The privacy goal is correct, but the static guard is too broad. It scans source
text for a parameter name that the earlier plan requires. An executor can either
follow the Plan 39-02 interface or pass the Plan 39-05 final guard, but not both.

Required fix:

Revise Plan 39-05 and `39-VALIDATION.md` so the privacy guard checks serialized
decision/event payloads rather than banning `transcript_window` as a source-code
identifier. Recommended fix:

- Keep tests that prove `RealtimeDecisionEvent.to_dict()` and
  `RealtimeResponseDecision.to_event()` never emit `raw_transcript`,
  `transcript_window`, `generated_answer`, `answer_text`, `daily_note`,
  `audio_bytes`, `PRIVATE_`, secrets, raw cached text, or generated answers.
- Keep static guards for clearly unsafe output field names such as
  `raw_transcript`, `generated_answer`, `answer_text`, `audio_bytes`, and
  `PRIVATE_`.
- Remove `transcript_window` from the broad source-text guard, or scope it only
  to event payload keys/serialization tests.
- Alternatively, rename the Plan 39-02 interface away from `transcript_window`
  everywhere, but that is more churn and does not improve privacy by itself.

## Nyquist Compliance

`workflow.nyquist_validation` is enabled, `39-RESEARCH.md` has a Validation
Architecture section, and `39-VALIDATION.md` exists, so this dimension applies.

| Plan | Task | RED/GREEN automated verify present | Status |
|------|------|------------------------------------|--------|
| 39-01 | 1 | RED pytest command with expected nonzero exit | PASS |
| 39-01 | 2 | Focused pytest, call-ready regression, no-bypass guard, mutation guard | PASS |
| 39-02 | 1 | RED pytest command with expected nonzero exit | PASS |
| 39-02 | 2 | Focused pytest, launch regression, fail-closed guard, privacy guard | PASS |
| 39-03 | 1 | RED pytest command with expected nonzero exit | PASS |
| 39-03 | 2 | Focused pytest, policy/call-ready/live-control regression, mutation guard | PASS |
| 39-04 | 1 | RED pytest command with expected nonzero exit | PASS |
| 39-04 | 2 | Focused pytest, gate/call-ready/live-control regression, standup separation guard | PASS |
| 39-05 | 1 | RED pytest command with expected nonzero exit | PASS |
| 39-05 | 2 | Focused suite, safety regression suite, full pytest, static guards | FAIL - one static guard is infeasible |

Sampling continuity is otherwise good: every implementation task has automated
validation, and each wave has at least two automated checks across its two tasks.
No watch-mode, Playwright/Cypress/Selenium, or delay-based validation was found.

## Structured Issues

```yaml
issues:
  - plan: "39-05"
    dimension: "verification_feasibility"
    severity: "blocker"
    task: 2
    description: "Final privacy guard rejects `transcript_window` in `saymo/analysis/realtime_policy.py`, but Plan 39-02 requires `resolve_realtime_response_decision(..., transcript_window: str, ...)` in that same file."
    fix_hint: "Revise 39-05 and 39-VALIDATION so privacy validation checks serialized event/decision payloads, or remove `transcript_window` from the broad source-text guard. Keep tests proving raw transcript windows are not emitted."
```

## Recommendation

Return to the planner for one revision. After the privacy guard is scoped so it
does not contradict the required policy interface, Phase 39 plans should be
ready for execution.

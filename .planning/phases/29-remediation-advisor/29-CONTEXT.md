# Phase 29: Remediation Advisor - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning
**Source:** Roadmap + Phase 27 rehearsal + Phase 28 scorecard implementation

<domain>
## Phase Boundary

Phase 29 turns existing readiness and reliability failures into concrete next
actions. It should add actionable hints for rehearsal, scorecard,
auto-preflight, hotkey doctor, and takeover checks, with each hint classified
by next-action type.

This phase does not add the multi-session soak runner or baseline drift gate;
that remains Phase 30.
</domain>

<decisions>
## Implementation Decisions

### Hint Taxonomy
- Add a small local taxonomy for remediation categories: config, macOS
  permission, audio-device routing, source data, review labeling, and retest.
- Hints should include a short title, action category, why it matters, concrete
  next command or step, and optional rerun command.
- Keep hints deterministic and rule-based; do not call an LLM for remediation.

### Integration Points
- Rehearsal hints should be derived from `RehearsalCheck` rows,
  `RehearsalDecision.blocked_reason`, and scorecard warnings.
- Scorecard hints should be derived from scorecard status, warnings, trigger
  metrics, playback metrics, and safety metrics.
- Auto-preflight hints should map blocking and warning checks to concrete
  commands or user actions.
- Hotkey doctor and takeover checks should get concise hints for Accessibility,
  missing listener process, and mic-routing failures.

### Rerun Contract
- Every user-facing hint should include a targeted rerun command where the
  affected check has one.
- Avoid forcing the user to rerun the entire autonomous workflow.
- Suggested reruns: `saymo auto-preflight`, `saymo hotkey-doctor`,
  `saymo takeover-check`, `saymo rehearsal`, `saymo session-scorecard`, and
  review-label commands for classifier/readiness issues.

### Output Style
- Render hints as compact terminal lines under a `remediation:` heading.
- Include category labels in output so the user can distinguish config,
  permission, audio routing, source data, review labeling, and retest.
- Do not leak raw transcript text, raw audio paths, or secrets in hints.

### Claude's Discretion
- Exact module boundaries may follow the Phase 28 scorecard pattern.
- It is acceptable to expose remediation helpers as pure analysis functions
  consumed by CLI commands.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `saymo.analysis.rehearsal` contains rehearsal checks and decisions.
- `saymo.analysis.session_scorecard` contains sanitized scorecard metrics and
  warnings.
- `saymo.commands.tests` contains `auto-preflight`, `rehearsal`,
  `session-scorecard`, `hotkey-doctor`, and `takeover-check`.
- `saymo.analysis.live_control` contains hotkey doctor reports and action
  vocabulary.

### Established Patterns
- Analysis modules use dataclasses and pure render/serialization helpers.
- CLI commands print concise line-oriented diagnostics.
- Tests assert exact snippets rather than depending on macOS runtime state.

### Integration Points
- Add a remediation analysis module and call it from existing diagnostic
  commands.
- Keep command-specific generation close to existing CLI output so Phase 30 can
  consume the same hint contract.
</code_context>

<specifics>
## Specific Ideas

- Dataclass: `RemediationHint(category, title, detail, action, rerun)`.
- Renderer output:
  - `remediation:`
  - `- [audio-device] Configure capture input: ...`
  - `  rerun: saymo auto-preflight -p personal`
- Suggested mapping examples:
  - missing capture/playback/provider device -> audio-device routing
  - missing hotkeys or blocked registration -> macOS permission/config
  - response cache empty -> source data
  - readiness missing labels -> review labeling
  - malformed audit rows -> retest/source data depending on context
</specifics>

<deferred>
## Deferred Ideas

- Soak-wide failure policy and baseline remediation belongs to Phase 30.
- Rich interactive fix wizard is future work.
- Automatically editing config or macOS settings remains out of scope.
</deferred>

---

*Phase: 29-remediation-advisor*
*Context gathered: 2026-07-06*


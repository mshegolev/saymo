# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into
future planning.*

## Milestone: v1.2 — Trigger Training Console

**Shipped:** 2026-05-20
**Phases:** 3 | **Plans:** 11 | **Sessions:** 1

### What Was Built
- Named trigger-capture sessions with local ledgers and summary commands.
- CLI filters, relabeling, review queue, and sanitized reports for saved
  trigger samples.
- Readiness and holdout evaluation commands for the local trigger classifier.
- Guarded per-profile live-assist configuration and `trigger-check --live-assist`
  diagnostics.

### What Worked
- Keeping phases aligned to user workflows made the feature easy to verify:
  capture a session, review samples, then decide whether a classifier is ready.
- Focused trigger tests covered the high-risk behavior without depending on
  macOS audio devices or model downloads.
- The audit pass caught planning/documentation drift after code had already
  shipped.

### What Was Inefficient
- Summary extraction produced no one-line accomplishments because summaries did
  not include that field.
- Some milestone archive details still required manual cleanup after
  `gsd-tools milestone complete`.

### Patterns Established
- Store live-call training artifacts locally under profile/session scope, then
  expose review commands before enabling runtime behavior.
- Treat learned behavior as opt-in and evidence-backed; deterministic gates
  remain the hard safety layer.
- Keep review reports sanitized by default.

### Key Lessons
1. Session metadata should be introduced before review/reporting features so
   later workflows can group evidence by meeting.
2. Classifier promotion needs both data readiness and model artifact checks;
   readiness alone is not enough.
3. Planning summaries should include concise accomplishment fields if the
   archive tooling is expected to extract them automatically.

### Cost Observations
- Model mix: not tracked in repo.
- Sessions: 1 main autonomous implementation/review session.
- Notable: focused phase verification was more actionable than full-suite runs
  that hit unrelated MLX/no-Metal baseline failures.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 4 | Introduced measured catch/say latency and sample review basics. |
| v1.1 | 1 | 3 | Added speaker context, classifier shadow mode, and provider probes. |
| v1.2 | 1 | 3 | Added session-aware review, relabeling, readiness, and guarded live assist. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | focused trigger/playback tests | phase-scoped | latency/sample tooling |
| v1.1 | focused trigger/provider tests | phase-scoped | speaker labels/classifier metadata |
| v1.2 | 50 focused trigger review/readiness/classifier tests | phase-scoped | review/readiness/session helpers |

### Top Lessons (Verified Across Milestones)

1. Real captured samples are the right substrate for trigger improvements, but
   they need safe local tooling before they should affect live calls.
2. Faster live-call behavior must stay tied to explicit diagnostics and
   conservative safety gates.
3. Milestone archive quality depends on keeping summaries, validation, and
   project state current before completion.

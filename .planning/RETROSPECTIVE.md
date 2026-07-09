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

## Milestone: v1.10 — Silent Breath Natural Pacing

**Shipped:** 2026-07-09
**Phases:** 1 | **Plans:** 1 | **Sessions:** 1

### What Was Built
- F5 natural pacing now uses silent pauses instead of audible breath splices.
- Sentence, clause, paragraph, and continuation pauses stay configurable.
- F5 pacing knobs participate in selector/cache fingerprints so stale cached
  WAVs are rejected after timing changes.
- A local F5 preview was generated for ear-based timing review.

### What Worked
- The initial RED test caught non-zero breath audio in the stitching path.
- The milestone audit found a real E2E cache invalidation gap before archive.
- Re-running the integration checker after the fix confirmed prepared and
  response cache flows now go stale correctly.

### What Was Inefficient
- `gsd-tools milestone complete` archived files but still required manual
  cleanup of active ROADMAP/REQUIREMENTS/MILESTONES state.
- Summary extraction did not populate one-line accomplishments automatically.

### Patterns Established
- Voice-quality changes must include cache fingerprint review, not only WAV
  output inspection.
- Live-call "breathing" behavior should be modeled as silence timing unless the
  user explicitly approves audible breath injection.

### Key Lessons
1. Generated audio fixes can be bypassed by stale caches unless synthesis
   parameters are part of metadata fingerprints.
2. Ear-review artifacts are useful, but the safety gate needs deterministic
   tests around sample values and cache invalidation.
3. Milestone audit should run before archive even when a phase-level
   verification already passed.

### Cost Observations
- Model mix: not tracked in repo.
- Sessions: 1 autonomous implementation and audit session.
- Notable: focused TTS/cache tests stayed fast enough to run repeatedly before
  the full suite.

---

## Milestone: v1.11 — F5 Gap Hardening

**Shipped:** 2026-07-09
**Phases:** 1 | **Plans:** 1 | **Sessions:** 1

### What Was Built
- Direct prepared-audio cache staleness regression for F5 pacing knob changes.
- Direct response-cache staleness regression for F5 pacing knob changes.
- Sanitized stale diagnostics checks for stable `voice_metadata_stale` reasons.
- Deterministic continuation-pause test proving `breath_interval_sentences`
  inserts zero-valued silence.
- Static/docs guard that keeps audible breath samples out of the F5 live-call
  synthesis path.

### What Worked
- The v1.10 audit output translated cleanly into one narrow hardening phase.
- The tests stayed fast enough to prove RED/GREEN behavior before a full-suite
  run.
- Adding `requirements-completed` metadata made the GSD milestone audit
  machine-checkable instead of prose-only.

### What Was Inefficient
- Phase summary metadata had to be added after initial completion because the
  first summary did not expose `requirements-completed` or `one_liner` fields.
- `gsd-tools milestone complete` still left active PROJECT/MILESTONES/ROADMAP
  cleanup for manual follow-up.

### Patterns Established
- F5 voice-quality hardening should cover both prepared-audio and
  response-cache invalidation, not only generated WAV samples.
- Breath-related live-call regressions need static path guards in addition to
  runtime audio assertions.

### Key Lessons
1. A passing integration check is stronger when every requirement has
   three-source evidence: requirements, summary metadata, and verification
   table.
2. Silence contracts should be expressed in sample windows so future audio
   changes cannot hide non-zero breath/noise layers.
3. Planning summaries should include extractor-friendly metadata before audit.

### Cost Observations
- Model mix: not tracked in repo.
- Sessions: 1 autonomous implementation, audit, and archive session.
- Notable: focused tests plus one full `uv run pytest -q` were sufficient for
  this hardening milestone.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 4 | Introduced measured catch/say latency and sample review basics. |
| v1.1 | 1 | 3 | Added speaker context, classifier shadow mode, and provider probes. |
| v1.2 | 1 | 3 | Added session-aware review, relabeling, readiness, and guarded live assist. |
| v1.10 | 1 | 1 | Added silent F5 breath pacing plus cache fingerprint invalidation. |
| v1.11 | 1 | 1 | Added direct F5 cache-staleness, continuation-silence, and static/docs guards. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | focused trigger/playback tests | phase-scoped | latency/sample tooling |
| v1.1 | focused trigger/provider tests | phase-scoped | speaker labels/classifier metadata |
| v1.2 | 50 focused trigger review/readiness/classifier tests | phase-scoped | review/readiness/session helpers |
| v1.10 | 552 full-suite tests | TTS/cache/selector plus full suite | silent-breath pacing and cache invalidation |
| v1.11 | 557 full-suite tests | cache metadata, response cache, F5 TTS, static guards | audit-ready hardening metadata |

### Top Lessons (Verified Across Milestones)

1. Real captured samples are the right substrate for trigger improvements, but
   they need safe local tooling before they should affect live calls.
2. Faster live-call behavior must stay tied to explicit diagnostics and
   conservative safety gates.
3. Milestone archive quality depends on keeping summaries, validation, and
   project state current before completion.

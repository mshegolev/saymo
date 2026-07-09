# Roadmap: Saymo v1.10 Silent Breath Natural Pacing

## Overview

This milestone removes audible breath/noise from the F5 natural pacing path
while preserving the perceived pause behavior that makes speech feel human.

## Phase 41: Silent Breath F5 Pacing

**Goal:** Replace audible breath splices with configurable silent breath pauses
and prove generated F5 WAV output contains silence at breath points.

**Requirements:** F5P-01, F5P-02, F5P-03, F5P-04, F5P-05

**Success Criteria:**
1. F5 natural pacing no longer calls `load_breath_sample()` for live-call output
   stitching.
2. Breath/paragraph/continuation points are materialized as zero-valued silence.
3. Config exposes silent breath pause timing without implying audible breath
   injection.
4. Tests fail against the current non-zero breath behavior and pass after the
   fix.
5. A short local F5 preview can be generated for ear-based review.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| F5P-01 | Phase 41 | Pending |
| F5P-02 | Phase 41 | Pending |
| F5P-03 | Phase 41 | Pending |
| F5P-04 | Phase 41 | Pending |
| F5P-05 | Phase 41 | Pending |

**Coverage:**
- v1.10 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0

## Next

Run `$gsd-plan-phase 41` or proceed directly with the focused implementation
because the user requested immediate execution after milestone creation.

# Phase 32: Benchmark Scoring and F5 Baseline - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning
**Source:** Autonomous defaults from v1.8 requirements, research, and Phase 31

<domain>
## Phase Boundary

Phase 32 turns the existing voice clone benchmark harness into file-backed
baseline evidence. It extends benchmark artifacts and docs only; it does not
install engines, download models, train models, change runtime `tts.engine`, or
run destructive cleanup.

This phase covers BEN-01 through BEN-05.
</domain>

<decisions>
## Implementation Decisions

### Benchmark Compatibility
- Preserve existing `scripts/voice_clone_benchmark.py` commands for F5 and
  Qwen3 Base.
- Existing run dirs stay under `~/.saymo/voice_benchmarks/<timestamp>-<engine>/`.
- Existing artifacts `manifest.json` and `blind-review.md` remain compatible.
- New artifacts are additive: `review.json` and `score-report.md`.

### Scoring Contract
- `review.json` is a human-fillable template keyed by generated clips.
- `score-report.md` is regenerated from manifest + review state and must mark
  dry-run, partial, complete, scored, rejected, or approved status clearly.
- A report must not claim promotion readiness unless scores exist.
- Transcript text must remain redacted; transcript length/path metadata is OK.

### Safety
- Phase 32 may run dry-runs and unit tests only by default.
- Real F5 generation remains a user-run command because it can be slow and uses
  local model assets.
- Candidate promotion is not in this phase; Phase 32 only creates baseline
  evidence format and F5 baseline gate.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` - BEN-01 through BEN-05.
- `.planning/ROADMAP.md` - Phase 32 goal and success criteria.
- `.planning/research/PITFALLS.md` - `score-report.md` and partial-run risks.
- `scripts/voice_clone_benchmark.py` - Existing benchmark harness.
- `tests/scripts/test_voice_clone_benchmark.py` - Existing benchmark tests.
- `docs/voice-clone-shootout.md` - User workflow docs to update.
- `saymo/analysis/voice_profile.py` - Profile metadata contract from Phase 31.
</canonical_refs>

<specifics>
## Specific Ideas

- Add `saymo/analysis/voice_benchmark.py` for artifact helpers.
- `write_outputs` in the script should call artifact helpers after every clip.
- `manifest.json` should include `expected_clips` and `run_status`.
- `review.json` should preserve already-entered scores when a partial run
  resumes or output is rewritten.
- `score-report.md` should include latency summary and clear gate status.
</specifics>

<deferred>
## Deferred Ideas

- Qwen3 install/download gates belong to Phase 33.
- Engine selector and runtime cache fingerprinting belong to Phase 34.
- Voice profile approval belongs to Phase 35.
</deferred>

---

*Phase: 32-benchmark-scoring-and-f5-baseline*
*Context gathered: 2026-07-07 via autonomous defaults*

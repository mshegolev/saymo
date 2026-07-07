---
milestone: v1.8
milestone_name: Call-ready Voice Clone
audited: 2026-07-07
status: passed
scores:
  requirements: 28/28
  phases: 5/5
  integration: 5/5
  flows: 5/5
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt:
  - phase: milestone
    items:
      - "Real audio/model quality still requires local user A/B scoring; v1.8 adds gates and evidence contracts, not an automatic subjective voice-quality verdict."
      - "Real non-dry preview depends on installed local TTS runtimes; tests cover audit/selector behavior without loading large models."
nyquist:
  compliant_phases:
    - 31-voice-asset-inventory-and-profile-setup
    - 32-benchmark-scoring-and-f5-baseline
    - 33-candidate-shootout-gates
    - 34-call-ready-engine-selector-and-fallback-chain
    - 35-preview-a-b-approval-and-safety-soak
  overall: complete
---

# Milestone v1.8 Audit: Call-ready Voice Clone

## Verdict

Audit passed. All 28 milestone requirements are implemented, mapped to phases,
and covered by phase verification evidence. The implementation keeps voice
assets and training datasets protected, adds benchmark evidence, gates
challenger engines, routes runtime synthesis through call-ready selector
checks, and requires explicit preview/approval evidence before live-call use.

## Scope

| Phase | Name | Status | Verification |
|-------|------|--------|--------------|
| 31 | Voice Asset Inventory and Profile Setup | complete | `31-VERIFICATION.md` passed |
| 32 | Benchmark Scoring and F5 Baseline | complete | `32-VERIFICATION.md` passed |
| 33 | Candidate Shootout Gates | complete | `33-VERIFICATION.md` passed |
| 34 | Call-ready Engine Selector and Fallback Chain | complete | `34-VERIFICATION.md` passed |
| 35 | Preview, A/B Approval, and Safety Soak | complete | `35-VERIFICATION.md` passed |

## Requirement Coverage

| Requirement Group | Requirements | Final Status | Evidence |
|-------------------|--------------|--------------|----------|
| Voice inventory | INV-01..INV-04 | satisfied | `voice-inventory`, protected classification, sanitized JSON/Markdown. |
| Voice profile | PROF-01..PROF-04 | satisfied | Profile manifests reference existing WAV/TXT, hash references, dry-run/apply split. |
| Benchmark baseline | BEN-01..BEN-05 | satisfied | Benchmark artifacts now include manifest, review, score report, and promotion readiness. |
| Candidate gates | CAND-01..CAND-05 | satisfied | Qwen dry-run stays import-free; real Qwen requires transcript and F5 baseline report; heavier candidates stay gated. |
| Runtime selector | RUN-01..RUN-05 | satisfied | Purpose-specific selector, metadata sidecars, stale-cache blockers, non-cloned live-call safeguards. |
| Preview and safety | SAFE-01..SAFE-05 | satisfied | Preview audit, score-backed approval/rejection, voice readiness in preflight/safety-soak. |

No orphaned requirements were found. All requirements in `.planning/REQUIREMENTS.md`
traceability are covered by phase summaries and verification evidence.

## Integration Check

Cross-phase integration is coherent:

- Phase 31 profile hashes feed Phase 34 selector/cache metadata.
- Phase 32 score reports feed Phase 33 Qwen gates and Phase 35 profile approval.
- Phase 33 challenger artifacts remain separate from production runtime config.
- Phase 34 selector blocks live-call use until Phase 35 approval marks the
  profile call-ready.
- Phase 35 safety-soak catches voice profile, metadata, and non-cloned live
  fallback blockers.

## E2E Flows

| Flow | Status | Evidence |
|------|--------|----------|
| Inventory -> profile | pass | `voice-inventory`, `voice-profile init/show/check`. |
| F5 baseline -> score report | pass | `voice_clone_benchmark.py` artifacts and scoring helpers. |
| F5 score -> Qwen gate | pass | `--baseline-report` required before real Qwen generation. |
| Profile approval -> live selector | pass | `voice-profile approve` writes approval; selector reads profile state. |
| Prepared cache -> live-call playback gate | pass | `.meta.json` sidecars and live selector readiness checks. |

## Verification Evidence

Phase evidence:

- Phase 31: focused 6 passed; full suite 386 passed, 1 skipped.
- Phase 32: focused 11 passed; full suite 389 passed, 1 skipped.
- Phase 33: focused 13 passed; full suite 391 passed, 1 skipped.
- Phase 34: focused 102 passed and 110 passed; full suite 402 passed, 1 skipped.
- Phase 35: focused 11 passed; full suite 407 passed, 1 skipped.

Final verification:

```bash
uv run pytest -q
```

Result: `407 passed, 1 skipped in 3.27s`

## Tech Debt

- Actual voice-quality promotion still needs local listening and A/B scoring.
  The system now enforces evidence and approval, but it cannot decide whether
  the voice sounds like the user without the user's review.
- Real preview/playback depends on local TTS runtimes and model files. Tests
  cover selector, audit, and safety logic without loading large models.

## Next Step

Run a real local F5 benchmark, fill `review.json`, approve the profile if the
score gate passes, then run `saymo auto-preflight -p personal` before using the
voice on a live call.

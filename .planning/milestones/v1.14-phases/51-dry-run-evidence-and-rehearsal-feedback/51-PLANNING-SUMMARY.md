# Phase 51 Planning Summary

Phase 51 is planned as a narrow RED/GREEN pair:

- `51-01-PLAN.md` - RED tests and contracts for sanitized dry-run artifacts, normalized latest-vs-previous comparison, rehearsal evidence references, scorecard loading, and safety-soak gating.
- `51-02-PLAN.md` - GREEN implementation for `LaunchEvidenceComparison`, flat `saymo dry-run-compare`, rehearsal `--launch-json`, and scorecard fallback from rehearsal-recorded launch evidence.

Wave structure:

| Wave | Plans | Dependency |
|------|-------|------------|
| 1 | `51-01` | `50-02` complete |
| 2 | `51-02` | `51-01` RED contracts |

Safety boundaries are locked from context: reuse launch-readiness artifacts, read saved JSON only, do not synthesize, play, record, mutate provider/launchd state, rebuild cache/model artifacts, access protected assets, or emit raw private content.

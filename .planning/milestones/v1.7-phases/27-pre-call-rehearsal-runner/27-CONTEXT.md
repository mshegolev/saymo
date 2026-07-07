# Phase 27 Context: Pre-call Rehearsal Runner

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Source:** Roadmap + existing v1.5/v1.6 implementation

<domain>
## Phase Boundary

Phase 27 adds a guided local rehearsal path for one profile. The rehearsal
should exercise the live-loop decision path without joining a real meeting and
without sending audio to the call output in dry-run mode.

It must produce a local artifact that later phases can use for scorecards and
soak gates. Phase 27 does not build the full scorecard, remediation advisor, or
baseline drift comparison.
</domain>

<decisions>
## Implementation Decisions

### Rehearsal Command
- Add a profile-scoped CLI command for pre-call rehearsal.
- Support a deterministic text path first so tests and users can rehearse
  trigger/addressing behavior without microphone capture.
- Keep dry-run as the default safety posture for new rehearsal behavior.

### Rehearsal Artifact
- Store sanitized JSON artifacts under a local directory by profile.
- Artifact should include profile, provider, transcript snippet, trigger result,
  addressing result, auto action, preflight checks, hotkey doctor summary,
  live-control state, pass/warn/fail checks, and created timestamp.
- Do not store raw audio or full local meeting transcripts.

### Checks
- Reuse existing `auto-preflight`, `hotkey-doctor`, addressing, trigger, and
  live-control helpers instead of duplicating detection logic.
- The phase should report would-speak/would-block decisions, not actually play
  audio.
- Blocking readiness failures make the rehearsal fail; nonblocking issues warn.

### Claude's Discretion
- Exact command name and module boundaries may follow local CLI patterns.
- JSON field layout may be optimized for Phase 28 scorecard consumption.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — Phase 27 requirements and success criteria.
- `.planning/REQUIREMENTS.md` — REH-01 through REH-04.

### Existing Runtime Behavior
- `saymo/commands/tests.py` — `auto-preflight`, `hotkey-doctor`,
  `trigger-check`, and session replay command patterns.
- `saymo/commands/core.py` — auto-mode addressing and handbrake gate behavior.
- `saymo/analysis/live_control.py` — live-control state, hotkey bindings,
  command queue, and audit helpers.
- `saymo/analysis/addressing.py` — shared addressing classification logic.
- `saymo/analysis/regression_replay.py` — sanitized JSON/Markdown artifact
  patterns for later scorecards.

### Tests
- `tests/test_trigger_check.py` — CLI fixture style for deterministic trigger
  checks and preflight coverage.
- `tests/test_hotkey_doctor.py` — hotkey doctor CLI coverage.
- `tests/analysis/test_live_control.py` — live-control state serialization and
  audit behavior.
</canonical_refs>

<specifics>
## Specific Ideas

- Suggested command: `saymo rehearsal -p personal --text "John, status?"`.
- Suggested flags: `--dry-run/--no-dry-run`, `--output-dir`, `--json-output`,
  `--provider`, and `--no-hotkey-probe`.
- Suggested local default: `~/.saymo/rehearsals/<profile>/<timestamp>.json`.
- Suggested auto action values: `answer_now`, `wait_for_confirmation`, `skip`.
- Suggested check statuses: `pass`, `warn`, `fail`.
</specifics>

<deferred>
## Deferred Ideas

- Full scorecard aggregation belongs to Phase 28.
- Remediation taxonomy belongs to Phase 29.
- Baseline drift and soak gates belong to Phase 30.
- Native UI/menu bar entry points remain beyond v1.7 unless a later phase
  explicitly changes scope.
</deferred>

---

*Phase: 27-pre-call-rehearsal-runner*
*Context gathered: 2026-05-22*


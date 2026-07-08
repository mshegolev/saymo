---
phase: 36-call-ready-preflight-and-cache-gate
verified: 2026-07-08T13:36:19Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "User can read grouped block/warn/info remediation with exact actions and rerun commands for each failed launch check."
  gaps_remaining: []
  regressions: []
---

# Phase 36: Call-Ready Preflight and Cache Gate Verification Report

**Phase Goal:** User can run one call-ready flow that proves daily-note readiness, prepared standup audio, response-cache coverage, approved cloned voice metadata, and remediation before a call.
**Verified:** 2026-07-08T13:36:19Z
**Status:** passed
**Re-verification:** Yes - after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User can run one call-ready command for a profile/provider and see a concise ready/not-ready result. | VERIFIED | `saymo/commands/call_ready.py:18` registers `call-ready`; `saymo/analysis/launch_readiness.py:112` emits one `call-ready: ready/not ready` line; smoke returned `call-ready: not ready` with exit 1 for current local blockers. |
| 2 | User can create or verify today's Obsidian daily note while separately blocking placeholder/empty standup content. | VERIFIED | `saymo/obsidian/daily_notes.py:42` preserves existing notes and creates missing notes; `saymo/obsidian/daily_notes.py:56` inspects usable content separately; `saymo/analysis/launch_sources.py:28` emits separate `daily_note_present` and `daily_note_source_ready` checks. |
| 3 | User can see whether prepared standup WAVs and response-cache variants are current for selected profile, voice, response library, and cloned voice fingerprint. | VERIFIED | Prepared audio validates voice/source metadata at `saymo/analysis/launch_sources.py:80`; response-cache coverage counts deterministic variants at `saymo/analysis/response_cache.py:578`; cloned-voice metadata exposes approval/fingerprints at `saymo/analysis/launch_cache.py:72`. |
| 4 | User can read grouped block/warn/info remediation with exact action and rerun commands for each failed launch check. | VERIFIED | Previous gap is closed: `daily_note_source_ready` now says to add usable note content and run `saymo prepare -p standup` at `saymo/analysis/launch_sources.py:44`; `prepared_standup_audio` now says `Run saymo prepare -p standup` at `saymo/analysis/launch_sources.py:146`; response-cache/voice rerun commands no longer include no-op `--prepare` (`saymo/analysis/launch_cache.py:114`). |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `saymo/analysis/launch_readiness.py` | Shared report contracts, full collector, renderer, artifact writer | VERIFIED | Dataclasses, blocking ready policy, full Phase 36 check order, grouped remediation, sanitization, and JSON artifact writer exist. |
| `saymo/commands/call_ready.py` | User-facing command with prepare, JSON, output, and exit status | VERIFIED | Click wrapper resolves provider, calls collector, writes optional artifact, preserves pure JSON stdout, uses `soft_wrap=True`, and exits 0/1 from `report.ready`. |
| `saymo/analysis/launch_sources.py` | Daily-note and prepared-audio checks | VERIFIED | Missing note creation remains behind `--prepare`; placeholder source remediation is exact; prepared WAV remediation points to the real `saymo prepare` command. |
| `saymo/obsidian/daily_notes.py` | Importable daily-note helpers | VERIFIED | Path, ensure, and privacy-safe source inspection helpers exist and are tested. |
| `saymo/analysis/response_cache.py` | Public response-cache coverage helper | VERIFIED | Reports exact ready/total counts plus bounded missing/stale variant-key examples without answer text. |
| `saymo/analysis/launch_cache.py` | Response-cache and cloned-voice launch checks | VERIFIED | Blocking checks cover disabled/partial/stale cache and unapproved/non-cloned voice metadata with sanitized metadata. |
| `saymo/analysis/cache_metadata.py` | Privacy-safe source digest metadata | VERIFIED | Source digest fields and `source_metadata_stale` rejection exist. |
| `saymo/analysis/remediation.py` | Launch-readiness remediation hints | VERIFIED | `hints_from_launch_readiness` maps failed/warning checks into source-data, voice-cache, and retest categories. |
| Tests under `tests/analysis/` and `tests/test_call_ready_cli.py` | Focused regression coverage | VERIFIED | Focused and full pytest suites pass, including explicit assertions for corrected remediation actions/reruns. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `saymo/commands/__init__.py` | `saymo.commands.call_ready` | bottom import | WIRED | `call_ready` is imported at `saymo/commands/__init__.py:383`, so Click decorators register the command. |
| `saymo/commands/call_ready.py` | `collect_launch_readiness` | direct import/call | WIRED | `profile`, resolved provider, and `prepare` are passed at `saymo/commands/call_ready.py:35`. |
| `saymo/commands/call_ready.py` | `write_launch_readiness_artifact` | `--output` path | WIRED | Artifact write happens before rendering at `saymo/commands/call_ready.py:41`; JSON stdout remains pure JSON. |
| `saymo/analysis/launch_readiness.py` | `saymo.analysis.launch_sources` | collector imports/calls | WIRED | Daily-note and prepared-audio checks are imported and appended at `saymo/analysis/launch_readiness.py:194`. |
| `saymo/analysis/launch_readiness.py` | `saymo.analysis.launch_cache` | collector imports/calls | WIRED | Response-cache and cloned-voice checks are imported and appended at `saymo/analysis/launch_readiness.py:190`. |
| `saymo/analysis/launch_sources.py` | `saymo.obsidian.daily_notes` | path, ensure, inspect helpers | WIRED | Uses `daily_note_path`, `ensure_daily_note`, and `inspect_standup_source` at `saymo/analysis/launch_sources.py:9`. |
| `saymo/analysis/launch_sources.py` | `saymo.analysis.cache_metadata` | prepared audio metadata check | WIRED | Builds and checks expected source-aware metadata at `saymo/analysis/launch_sources.py:88`. |
| `saymo/commands/core.py` | prepared WAV metadata writes | `saymo prepare` | WIRED | `prepare` exists at `saymo/commands/core.py:1351` and writes source-aware metadata with `source_sha256` references around `saymo/commands/core.py:1448`. |
| `saymo/commands/tests.py` | response cache rebuild | `saymo prepare-responses` | WIRED | `prepare-responses` exists at `saymo/commands/tests.py:296` and builds cache metadata at `saymo/commands/tests.py:312`. |
| `saymo/analysis/launch_cache.py` | `response_cache_coverage` | coverage helper | WIRED | Builds `ResponseCache` and calls coverage at `saymo/analysis/launch_cache.py:45`. |
| `saymo/analysis/launch_cache.py` | `resolve_voice_selector(..., purpose="live_call")` | selector decision | WIRED | Approved cloned-voice gate is based on live-call selector metadata at `saymo/analysis/launch_cache.py:79`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| LAUN-01 | 36-01, 36-04 | One call-ready command returns concise ready/not-ready. | SATISFIED | CLI registration, one top-level human line, JSON mode, and exit status verified. |
| LAUN-02 | 36-02, 36-04 | Create/verify today's Obsidian daily note without overwriting. | SATISFIED | `ensure_daily_note` preserves existing files; `--prepare` creates only missing notes and does not overwrite content. |
| LAUN-03 | 36-02, 36-04 | Daily-note source readiness separate from file existence, with placeholder blocker. | SATISFIED | Separate `daily_note_present` and `daily_note_source_ready` checks; smoke shows present note can still block as `placeholder_only`. |
| LAUN-04 | 36-02, 36-04 | Prepare or verify current standup audio without silently accepting stale WAVs. | SATISFIED | Prepared audio rejects missing/stale/source-stale metadata and remediation points to `saymo prepare -p <profile>`. |
| LAUN-05 | 36-03, 36-04 | Response-cache coverage counts plus stale/missing blockers. | SATISFIED | `response_cache_coverage` reports ready/total and bounded missing/stale variant-key examples; smoke shows `48/48 variants ready`. |
| LAUN-06 | 36-03, 36-04 | Approved cloned-voice metadata and stale-cache reasons visible. | SATISFIED | Report includes selected engine, voice profile, approval state, reference hashes/fingerprint, and stale reasons without raw reference text. |
| LAUN-07 | 36-01, 36-04 | Grouped remediation with exact action/rerun for every check. | SATISFIED | Grouped output now gives exact actions: edit note then `saymo prepare -p standup`, `Run saymo prepare -p standup`, and rerun `saymo call-ready -p standup --provider glip`. |

No orphaned Phase 36 requirements found. `REQUIREMENTS.md` maps LAUN-01 through LAUN-07 to Phase 36, and all are claimed by phase plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `saymo/analysis/launch_readiness.py` | 248 | `basic_provider_audio_placeholder` | Info | Intentional Phase 37 placeholder; it is info-only, `ok=True`, and does not claim provider/audio readiness. |
| `saymo/analysis/launch_sources.py` | 15 | `placeholder_only` token | Info | Intentional daily-note source-readiness reason, not a stub. |

No TODO/FIXME, empty implementation, console-log-only implementation, or blocker stub pattern was found in the Phase 36 implementation files.

### Human Verification Required

None for the Phase 36 automated decision. Live provider/audio behavior is explicitly deferred to Phase 37, daemon behavior to Phase 38, realtime fail-closed behavior to Phase 39, and scorecard/safety-soak evidence to Phase 40.

### Automated Verification Evidence

- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py -q` -> `15 passed in 0.19s`
- `uv run pytest tests/analysis/test_launch_readiness.py tests/test_call_ready_cli.py tests/analysis/test_response_cache.py tests/analysis/test_cache_metadata.py tests/scripts/test_ensure_obsidian_daily_note.py tests/test_trigger_check.py -q` -> `85 passed in 0.81s`
- `uv run pytest` -> `433 passed in 3.50s`
- `uv run saymo call-ready -p standup --provider glip` -> exit 1 for expected current local blockers, with actionable remediation:
  - `daily_note_source_ready`: add usable content to `/Users/m.v.shchegolev/Documents/Obsidian Vault/2026-07-08.md`, then run `saymo prepare -p standup`
  - `prepared_standup_audio`: run `saymo prepare -p standup`
  - rerun command: `saymo call-ready -p standup --provider glip`
- `uv run saymo call-ready -p standup --provider glip --json` -> exit 1 with valid sanitized JSON: `ready=false`, `check_count=6`, `ready_count=4`, `block_count=2`, response cache `48/48`, cloned voice ready, provider/audio deferred to Phase 37.

The GSD helper commands `verify artifacts` and `verify key-links` returned `No must_haves.* found in frontmatter` for the phase plan files, despite visible nested `must_haves` blocks. I therefore used the previous verification truths, roadmap success criteria, plan frontmatter, and manual code/wiring checks above as the verification contract.

### Gaps Summary

No blocking gaps remain. The previous remediation gap is closed, and the live CLI smoke confirms the user-facing actions now point to commands that actually remediate the current blockers. Phase 37-40 responsibilities remain intentionally deferred and are not Phase 36 gaps.

---

_Verified: 2026-07-08T13:36:19Z_
_Verifier: Claude (gsd-verifier)_

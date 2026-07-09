---
phase: 45-prosody-preview-corpus
verified: 2026-07-09T19:36:36Z
status: human_needed
score: 9/9 must-haves verified
human_verification:
  - test: "Run a non-dry-run selected corpus preview with the local approved F5 model, then listen to current and candidate clips."
    expected: "The command creates playable WAV files for the selected corpus entries and the current/candidate timing difference is audible enough for tuning."
    why_human: "Verification stayed local and did not touch ~/.saymo assets or real model caches; audio quality and model-backed synthesis require local assets plus listening."
---

# Phase 45: Prosody Preview Corpus Verification Report

**Phase Goal:** Users can tune F5 prosody against a richer sanitized corpus and selected subsets without committing private content.
**Verified:** 2026-07-09T19:36:36Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User can inspect a built-in sanitized F5 preview corpus from the CLI. | VERIFIED | `f5-presets corpus list` is registered and renders only ID/category/label columns in `saymo/commands/voice_clone.py:276`; CLI test verifies metadata output and phrase-text absence in `tests/test_voice_clone_cli.py:331`. |
| 2 | The built-in corpus covers acknowledgement, standup, multi_sentence, clause_heavy, and handoff answer shapes. | VERIFIED | `F5_PREVIEW_CORPUS` contains all five categories with two entries each in `saymo/tts/f5_corpus.py:19`; corpus contract test asserts the exact category tuple and minimum coverage in `tests/tts/test_f5_preview_corpus.py:24`. |
| 3 | Corpus entries have stable ids, categories, labels, and generic synthetic text. | VERIFIED | `F5PreviewCorpusEntry` is frozen with id/category/label/text fields in `saymo/tts/f5_corpus.py:9`; stable lookup and ordering helpers are implemented in `saymo/tts/f5_corpus.py:108`. |
| 4 | User can generate current-vs-candidate F5 timing previews from selected corpus categories. | VERIFIED | `--corpus` resolves entries and fans each item through current/candidate configs in `saymo/commands/voice_clone.py:356` and `saymo/commands/voice_clone.py:480`; CLI test verifies 4 records for the standup category in `tests/test_voice_clone_cli.py:401`. |
| 5 | User can generate current-vs-candidate F5 timing previews from selected corpus ids. | VERIFIED | `--corpus-id` is wired in `saymo/commands/voice_clone.py:362`, resolver metadata is passed to records in `saymo/commands/voice_clone.py:443`, and output names include corpus id/current/candidate in `saymo/commands/voice_clone.py:535`; CLI test verifies `standup-blocked` records and filenames in `tests/test_voice_clone_cli.py:439`. |
| 6 | Manual `--text` preview still works for one-off local checks. | VERIFIED | `--text` remains accepted and is mutually exclusive with corpus selectors in `saymo/commands/voice_clone.py:350`; manual preview regression verifies two sanitized records in `tests/test_voice_clone_cli.py:348`. |
| 7 | User can understand how to inspect and extend the safe built-in corpus without copying private content. | VERIFIED | Operator docs show `f5-presets corpus list`, category/id previews, and the manual one-off path in `docs/voice-clone-shootout.md:20`; naturalness guide points to the sanitized corpus path in `docs/VOICE-NATURALNESS.md:134`. |
| 8 | Preview artifacts expose corpus id/category/label and hashes/counts, not phrase text or private manual text. | VERIFIED | Timing records store `text_sha256`, `text_chars`, and optional `corpus.id/category/label` only in `saymo/analysis/f5_timing_review.py:16`; raw source text is explicitly discarded before writing artifacts in `saymo/analysis/f5_timing_review.py:54`; regression checks manifest/review/report for both corpus and manual raw-text absence in `tests/test_voice_clone_cli.py:476`. |
| 9 | Docs describe Phase 45 preview controls without adding timing metrics or source-type routing claims. | VERIFIED | Docs include corpus controls and privacy metadata in `docs/voice-clone-shootout.md:57`; grep found no `speech-rate`, `pause-distribution`, `source-type`, `automatic preset recommendation`, or `cache fingerprint routing` claims in the touched docs or Phase 45 code. |

**Score:** 9/9 plan must-have truths verified. Roadmap success criteria are automated-supported 3/3; final status is `human_needed` only because model-backed synthesis/listening was intentionally not run.

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `saymo/tts/f5_corpus.py` | Built-in F5 preview corpus and resolver contract | VERIFIED | Exists, substantive, contains frozen entry dataclass, all required categories, lookup/list/selection APIs, and category/id tests. |
| `saymo/commands/voice_clone.py` | Corpus inspection CLI and selected preview generation | VERIFIED | Exists, substantive, registers `f5-presets corpus list`, `--corpus`, `--corpus-id`, validation errors, and current/candidate preview fan-out. |
| `saymo/analysis/f5_timing_review.py` | Privacy-safe preview records and artifact writer | VERIFIED | Exists, substantive, stores hashes/counts and safe corpus metadata; does not persist raw source text. |
| `tests/tts/test_f5_preview_corpus.py` | Corpus contract tests | VERIFIED | Covers required categories, stable id/category lookup, category selection, id ordering, all selection, and unknown value errors. |
| `tests/test_voice_clone_cli.py` | CLI and artifact privacy regressions | VERIFIED | Covers corpus list privacy, manual preview sanitization, selected category/id previews, selection errors, and artifact raw-text absence. |
| `docs/voice-clone-shootout.md` | Operator workflow and artifact privacy docs | VERIFIED | Documents corpus list, selected previews, manual local preview, safe metadata, and prohibited private content. |
| `docs/VOICE-NATURALNESS.md` | Naturalness guide pointer to corpus tuning controls | VERIFIED | Documents repeatable sanitized F5 tuning with corpus list, category preview, and entry preview. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `voice_clone.py` | `f5_corpus.py` | Lazy import in corpus list command | WIRED | `list_f5_preview_corpus` is imported inside `f5_presets_corpus_list` and rendered in a table (`saymo/commands/voice_clone.py:281`). |
| `tests/test_voice_clone_cli.py` | `saymo f5-presets corpus list` | `CliRunner` command invocation | WIRED | CLI test invokes `["f5-presets", "corpus", "list"]` and asserts safe metadata only (`tests/test_voice_clone_cli.py:331`). |
| `voice_clone.py` | `f5_corpus.py` | `resolve_f5_preview_corpus_selection` for CLI options | WIRED | Corpus selections are resolved through the corpus API before preview item generation (`saymo/commands/voice_clone.py:443`). |
| `voice_clone.py` | `f5_timing_review.py` | `build_f5_timing_record` corpus metadata arguments | WIRED | Preview records receive source kind, corpus id/category/label, text hash input, output path, and dry-run state (`saymo/commands/voice_clone.py:505`). |
| `tests/test_voice_clone_cli.py` | `f5_corpus.py` | Raw-text absence assertion uses selected corpus entry | WIRED | Test imports and resolves `standup-blocked`, then asserts `entry.text` is absent from persisted artifacts (`tests/test_voice_clone_cli.py:476`). |
| `docs/voice-clone-shootout.md` | `saymo f5-presets preview` | Documented examples for `--corpus` and `--corpus-id` | WIRED | Operator docs show both selected subset preview commands and the sanitized artifact contract (`docs/voice-clone-shootout.md:20`). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| CORP-01 | `45-01-PLAN.md` | Richer sanitized phrase corpus covers short acknowledgements, standup updates, multi-sentence answers, clause-heavy responses, and direct handoff replies. | SATISFIED | `.planning/REQUIREMENTS.md:11`; corpus categories/entries in `saymo/tts/f5_corpus.py:19`; corpus tests in `tests/tts/test_f5_preview_corpus.py:24`. |
| CORP-02 | `45-02-PLAN.md` | A/B timing previews from selected corpus subsets compare current and candidate presets across realistic answer shapes. | SATISFIED | `.planning/REQUIREMENTS.md:14`; preview options and current/candidate fan-out in `saymo/commands/voice_clone.py:348`; selected category/id tests in `tests/test_voice_clone_cli.py:401`. |
| CORP-03 | `45-03-PLAN.md` | Preview corpus can be extended or inspected without copying private meeting transcript text, prompts, voice samples, training datasets, secrets, or raw audio into committed artifacts. | SATISFIED | `.planning/REQUIREMENTS.md:17`; artifact writer stores hashes/counts and safe metadata only in `saymo/analysis/f5_timing_review.py:16`; final raw-text absence regression in `tests/test_voice_clone_cli.py:476`; no tracked `manifest.json`, `review.json`, `timing-report.md`, WAV, or MP3 artifacts found. |

No orphaned Phase 45 requirements were found. `ROADMAP.md` and `.planning/REQUIREMENTS.md` map exactly CORP-01, CORP-02, and CORP-03 to Phase 45.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | - | - | No blocker TODO/FIXME/placeholder/empty-handler/console-log patterns were found in the Phase 45 files. The only `return {}` match is `_read_yaml_config()` returning an empty config mapping for missing config files, unrelated to this phase. |

### Human Verification Required

### 1. Non-Dry-Run F5 Corpus Preview Listening

**Test:** With the local approved F5 model and private assets available, run `saymo f5-presets preview calm --corpus-id standup-blocked --output-dir <local-run>` without `--dry-run`, then listen to the current and candidate WAVs.
**Expected:** The command creates playable current/candidate WAV files using the selected corpus entry, and the timing difference is audible enough for an operator to choose a preset.
**Why human:** The verification request explicitly avoided touching `~/.saymo` assets and real model caches. Audio quality and local model-backed synthesis cannot be proven by static code inspection alone.

### Gaps Summary

No code or wiring gaps were found. Automated checks verify the corpus contract, CLI inspection, selected subset preview records, sanitized persisted artifacts, docs, and requirement coverage. Human verification remains for the real audio-listening loop only.

---

_Verified: 2026-07-09T19:36:36Z_
_Verifier: Claude (gsd-verifier)_

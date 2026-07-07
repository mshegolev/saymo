# v1.8 Research Summary: Call-ready Voice Clone

**Synthesized:** 2026-07-07
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

## Key Decision

v1.8 should not replace Saymo's audio stack. It should add a small,
local-by-default voice-readiness layer around the existing TTS factory,
prepare/speak/auto flow, benchmark harness, rehearsal, scorecard, and
safety-soak commands.

The call-ready path is:

1. Inventory local voice assets without mutation.
2. Create a protected voice profile that references existing samples and
   transcript sidecars.
3. Establish a comparable F5 baseline with score evidence.
4. Gate Qwen3 Base and later candidates behind dry-runs, transcripts, and
   score reports.
5. Activate only an approved engine/fallback chain.
6. Enforce preview, A/B approval, cache fingerprinting, rehearsal, and
   safety-soak before cloned audio reaches a real call.

## Stack Additions

- Reuse `f5tts_clone`, `scripts/voice_clone_benchmark.py`,
  `saymo/tts/factory.py`, response cache, rehearsal, session-scorecard, and
  safety-soak.
- Add read-only voice inventory and voice-profile metadata under `~/.saymo/`.
- Add benchmark scoring artifacts: `review.json`, `score-report.md`, and
  approval metadata linked to profile and run id.
- Add a runtime selector/fallback layer above the existing TTS factory, not
  inside individual engines.
- Keep Qwen3 Base as an isolated, dry-run-first challenger. Keep CosyVoice
  blocked until Qwen3 has a score report.
- Prefer the internal Nexus3 PyPI mirror for approved package installs, but do
  not hardcode it in public docs or committed project config.

## Feature Table Stakes

- User can see active voice engine, model files, datasets, caches, benchmark
  runs, and protected assets in a read-only inventory.
- User can create a voice profile that points at existing reference WAV/TXT
  files without rewriting samples or datasets.
- User can validate reference quality before running real benchmarks.
- User can run comparable benchmark runs across F5 and candidate engines with
  stable phrase ids, manifests, latency, blind review, and score reports.
- User can approve an engine only through explicit benchmark evidence.
- User can activate an engine/fallback chain for prepare/live purposes and see
  whether a fallback is cloned or non-cloned.
- Rehearsal, scorecard, safety-soak, and preflight understand voice profile,
  benchmark approval, selected engine, cache fingerprint, and fallback status.
- Preview output is allowed before approval; real call output is blocked until
  the voice profile is approved.

## Architecture

Recommended modules:

- `saymo/analysis/voice_inventory.py` for read-only asset discovery.
- `saymo/analysis/voice_profile.py` for profile manifests, reference hashes,
  approvals, and fallback metadata.
- `saymo/analysis/voice_benchmark.py` for benchmark manifests, scoring, and
  approval artifacts extracted from the current script.
- `saymo/analysis/voice_readiness.py` for one pass/warn/fail readiness report
  consumed by preflight, rehearsal, scorecards, and safety-soak.
- `saymo/tts/selector.py` for approved engine/fallback resolution while still
  constructing engines through `get_tts_engine`.
- `saymo/commands/voice_clone.py` for CLI commands that are not training
  commands.

## Watch Out For

- Do not treat voice samples, training datasets, or fine-tuned models as
  disposable cache.
- Do not run package installs, model downloads, or training from inventory,
  profile setup, benchmark dry-run, preflight, or docs tests.
- Do not confuse Qwen3 Base shootout via official `qwen_tts` with the existing
  production `qwen3_clone` MLX path.
- Do not let CosyVoice or GPT-SoVITS start before F5 and Qwen3 score reports
  justify the next candidate.
- Do not promote an engine just because a WAV was generated; require scored
  blind review and approval artifacts.
- Do not let old safety-soak pass while voice readiness is unapproved or
  unknown.
- Do not silently fall back to Piper or macOS `say` in a live call while the
  user expects cloned voice.

## Recommended Phase Shape

1. **Phase 31:** Voice Asset Inventory and Profile Setup.
2. **Phase 32:** Benchmark Scoring and F5 Baseline.
3. **Phase 33:** Candidate Shootout Gates.
4. **Phase 34:** Call-ready Engine Selector and Fallback Chain.
5. **Phase 35:** Preview, A/B Approval, and Safety Soak.

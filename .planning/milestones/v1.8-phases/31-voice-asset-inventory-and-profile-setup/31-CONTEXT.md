# Phase 31: Voice Asset Inventory and Profile Setup - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning
**Source:** Autonomous defaults from v1.8 requirements and research

<domain>
## Phase Boundary

Phase 31 delivers the read-only local voice inventory and protected voice
profile/reference contracts for Saymo. It does not run benchmarks, install
models, download packages, train models, delete files, modify runtime engine
selection, or route audio to calls.

This phase covers requirements INV-01 through INV-04 and PROF-01 through
PROF-04. The user should be able to inspect local voice state and create a
profile manifest that references existing voice samples and transcript sidecars
without mutating source assets.
</domain>

<decisions>
## Implementation Decisions

### Safety and Scope
- Inventory is read-only. It may stat, hash, inspect audio metadata, classify
  paths, and write optional reports, but it must never delete, move, rewrite,
  transcribe, normalize, train, install, or download.
- Voice samples, training datasets, fine-tuned models/adapters, and F5 runtime
  assets are protected local state.
- Profile setup references existing files and stores hashes/metadata. It does
  not copy or trim audio and does not rewrite sidecar transcripts.
- Profile writes are explicit via apply-style command behavior; dry-run output
  is the default for proposed changes where mutation is possible.
- Sanitized exports must omit raw transcript text and secrets. Transcript
  presence, path, byte size, and character count are acceptable.

### CLI Shape
- Add voice clone management commands separately from training commands so
  read-only/profile work is not confused with `train-*`.
- Preferred commands for this phase:
  - `saymo voice-inventory`
  - `saymo voice-inventory --json-output <path>`
  - `saymo voice-profile init --profile <name> --voice-sample <wav> --ref-text-file <txt> --engine <engine> --dry-run`
  - `saymo voice-profile init ... --apply`
  - `saymo voice-profile show --profile <name>`
  - `saymo voice-profile check --profile <name>`
- Use existing Click/Rich command patterns and `SaymoConfig` dataclasses.

### Storage
- Store profile manifests under `~/.saymo/voice_profiles/<profile>/profile.json`
  by default.
- Store optional inventory reports wherever the user passes `--json-output`;
  do not create timestamped reports unless explicitly requested by command
  design.
- Profile manifests should store path strings, hashes, audio metadata, engine,
  language, approval state, and timestamps.

### Validation
- Tests must use temporary directories and fake assets. They must prove no
  source asset contents or mtimes are changed by inventory/profile checks.
- Audio metadata tests may use small generated WAV fixtures through existing
  `soundfile` dependency.
- No test may require real local models, `~/F5TTS`, `~/.saymo`, Qwen packages,
  or network access.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/REQUIREMENTS.md` - Phase 31 requirement IDs and acceptance scope.
- `.planning/ROADMAP.md` - Phase 31 goal, success criteria, and plan list.
- `.planning/research/SUMMARY.md` - Synthesized v1.8 direction and risks.
- `.planning/research/STACK.md` - Stack reuse, internal PyPI notes, and storage boundaries.
- `.planning/research/FEATURES.md` - User workflows and table-stakes behavior.
- `.planning/research/ARCHITECTURE.md` - Proposed modules and data flow.
- `.planning/research/PITFALLS.md` - Phase 31 pitfalls and prevention strategy.

### Existing Code
- `saymo/config.py` - Dataclass config style and known TTS engine config fields.
- `saymo/tts/factory.py` - Known engine names and deferred optional imports.
- `saymo/tts/f5tts.py` - F5 runtime defaults, reference sample, and transcript handling.
- `saymo/commands/voice_train.py` - Existing voice recording/training command style.
- `saymo/commands/core.py` - Main Click registration and existing command structure.
- `tests/tts/test_factory.py` - Existing TTS test style.
- `tests/scripts/test_voice_clone_benchmark.py` - Existing voice benchmark test style.

### User-Facing Docs
- `docs/voice-clone-shootout.md` - Current shootout baseline and command examples.
- `docs/F5TTS-VOICE-CLONING.md` - F5 baseline config and operational notes.
- `docs/VOICE-TRAINING.md` - Existing training workflow, which this phase must not invoke implicitly.
</canonical_refs>

<specifics>
## Specific Ideas

- Use a simple dataclass model such as `VoiceAssetRecord`,
  `VoiceInventoryReport`, `VoiceProfileManifest`, and `VoiceProfileCheck`.
- Inventory should classify conventional roots:
  - `~/.saymo/voice_samples`
  - `~/.saymo/training_dataset*`
  - `~/.saymo/models`
  - `~/.saymo/audio_cache`
  - `~/.saymo/voice_benchmarks`
  - `~/F5TTS`
- Inventory should also inspect configured F5 paths from `config.tts.f5tts`
  and known engines from `saymo.tts.factory.KNOWN_ENGINES`.
- Use SHA-256 for files small enough to hash in tests and reference files.
  For large model directories, size/path/status classification is enough.
- Profile approval starts false; approval is Phase 35, not Phase 31.
</specifics>

<deferred>
## Deferred Ideas

- Benchmark scoring and `score-report.md` belong to Phase 32.
- Qwen3/CosyVoice install/download gates belong to Phase 33.
- Runtime selector/fallback integration belongs to Phase 34.
- Preview, A/B approval, preflight, rehearsal, scorecard, and safety-soak
  voice readiness belong to Phase 35.
- Destructive cleanup of model assets is explicitly out of scope.
</deferred>

---

*Phase: 31-voice-asset-inventory-and-profile-setup*
*Context gathered: 2026-07-07 via autonomous defaults*

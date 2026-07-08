# Phase 33: Candidate Shootout Gates - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning
**Source:** Autonomous defaults from v1.8 requirements and prior phases

<domain>
## Phase Boundary

Phase 33 hardens challenger gates around Qwen3 Base and later candidates. It
does not install packages, download models, run real Qwen generation locally,
train LoRA, add CosyVoice adapter code, or change production runtime config.
</domain>

<decisions>
## Implementation Decisions

- Qwen3 Base dry-run must remain import-free and download-free.
- Real Qwen3 Base benchmark requires an explicit reference transcript and a
  completed F5 baseline score report path.
- Qwen3 Base benchmark artifacts must state they are the official
  `qwen_tts` Base benchmark path, not the production `qwen3_clone` MLX runtime.
- CosyVoice/GPT-SoVITS/LoRA remain blocked by docs and candidate gate helpers
  until score reports justify opening those tracks.
- Internal Nexus3 PyPI is an install preference for approved isolated runtimes,
  not a committed package source and not a model-weight source.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` - CAND-01 through CAND-05.
- `.planning/ROADMAP.md` - Phase 33 goal and success criteria.
- `.planning/research/STACK.md` - Internal PyPI/Nexus and runtime isolation notes.
- `.planning/research/PITFALLS.md` - Qwen3 Base vs `qwen3_clone` and CosyVoice gate risks.
- `scripts/voice_clone_benchmark.py` - Existing Qwen3 Base dry-run/real-run path.
- `saymo/analysis/voice_benchmark.py` - Score-report artifact helper from Phase 32.
- `docs/voice-clone-shootout.md` - User-facing command docs.
- `docs/qwen3-base-voice-clone-notes.md` - Existing Qwen3 gate note.
- `docs/cosyvoice-voice-clone-notes.md` - Existing CosyVoice blocked note.
</canonical_refs>

<specifics>
## Specific Ideas

- Add `--baseline-report` to Qwen3 Base real benchmark and fail if missing or
  not promotion-ready enough for baseline evidence.
- Keep Qwen dry-run free from the baseline-report requirement.
- Add a gate helper that reads `score-report.md` text and checks for required
  lines such as `run status: complete` and `score status: scored`.
- Store Qwen benchmark settings like `benchmark_path: official_qwen_tts_base`
  and `runtime_engine: not_qwen3_clone`.
</specifics>

<deferred>
## Deferred Ideas

- Actual Qwen installation/download/use remains user-approved and may require
  network access outside this phase.
- CosyVoice adapter implementation is still deferred.
- Runtime `qwen3_clone` promotion belongs to later runtime/approval phases.
</deferred>

---

*Phase: 33-candidate-shootout-gates*
*Context gathered: 2026-07-07 via autonomous defaults*

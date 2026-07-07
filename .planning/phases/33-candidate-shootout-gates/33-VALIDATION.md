# Phase 33 Validation Strategy

**Created:** 2026-07-07

## Must Prove

- Qwen dry-run remains import/download free.
- Qwen real-run fails fast without transcript.
- Qwen real-run fails fast without a completed/scored F5 baseline report.
- Qwen benchmark artifacts state that they are official Base benchmark output,
  not proof that production `qwen3_clone` is call-ready.
- Docs keep CosyVoice/GPT-SoVITS/LoRA and package installs gated.

## Automated Coverage

- Script tests for Qwen dry-run, missing transcript, missing/invalid baseline
  report, and benchmark settings metadata.
- Score-report helper tests.

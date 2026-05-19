# Milestone Audit: v1.1 Call Intelligence Loop

status: passed

## Scope

Milestone v1.1 targeted Advanced Call Intelligence: saved call samples and
live-call probes should explain who spoke, why Saymo would answer, and where
provider-specific latency is spent without adding required cloud services or
risky live-call behavior changes.

## Requirement Coverage

- SPK-01: captured trigger samples can carry local speaker labels without cloud
  diarization.
- SPK-02: `trigger-eval` groups records, misses, false positives, and current
  answer counts by `me`, `other`, and `unknown`.
- SPK-03: `trigger-samples label` updates a sample's speaker label locally.
- CLF-01: `trigger-samples decision` marks answer decisions as accepted,
  rejected, or unlabeled.
- CLF-02: `trigger-classifier train` trains only after accepted/rejected label
  thresholds are satisfied.
- CLF-03: `trigger-eval --classifier-shadow` and
  `trigger-check --classifier-shadow` compare learned confidence against the
  deterministic gate without changing live decisions.
- LAT-01: `provider-latency` runs a provider-specific probe through the
  existing Chrome provider abstraction.
- LAT-02: provider latency reports capture, transcription, trigger decision,
  provider unmute, playback start, playback duration, and mute recovery.
- LAT-03: provider latency history is exported as local JSON and Markdown by
  profile/provider.
- INT-01: trigger samples distinguish plain name mentions from true handoffs,
  so `mentioned_me` does not trigger an answer while `asked_to_speak` still
  covers direct questions and floor handoff phrases.

## Cross-Phase Integration

- Phase 5 speaker labels are loaded by the shared trigger-sample reader used by
  Phase 6 classifier training and Phase 6/7 diagnostics.
- Phase 6 classifier shadow mode uses deterministic trigger/addressing output
  as comparison data, preserving the safe live-call gate.
- Phase 7 provider probes reuse existing provider automation and playback
  routing rather than introducing a separate call-control path.
- Post-phase mention/handoff refinement reuses the deterministic addressing
  gate and only changes sample classification/reporting, preserving live-call
  safety.

## Verification

- Phase 5 verification: passed; full suite at that point reported 243 passed.
- Phase 6 verification: passed; full suite at that point reported 250 passed.
- Phase 7 verification: passed; full suite at that point reported 252 passed.
- Post-merge CI for Phase 5, Phase 6, and Phase 7 passed on `main`.
- Post-phase mention/handoff refinement verification: focus tests passed
  locally and Python CI passed on `main`.

## Residual Notes

- Speaker-aware evaluation and classifier quality depend on real labeled call
  samples accumulating under `~/.saymo/trigger_samples/`.
- Provider latency history is meaningful only after probing real active calls.
- Enabling the classifier in live auto-mode remains deferred until enough
  shadow-mode evidence exists.

## Result

v1.1 passed milestone audit with 10/10 v1.1 requirements satisfied and no
critical integration gaps.

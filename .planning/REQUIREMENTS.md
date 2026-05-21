# Requirements: Saymo v1.5 Live Review + Safe Approved Speak

**Defined:** 2026-05-21
**Core Value:** Saymo must reliably catch when the user is expected to answer
and respond fast enough that the call still feels live.

## v1.5 Requirements

Requirements for milestone v1.5 Live Review + Safe Approved Speak.

### Post-call Review Queue

- [x] **REV-05**: User can open a prioritized post-call review queue for one
  capture session that surfaces likely handoffs, questions, name mentions,
  unlabeled speaker windows, and classifier-critical samples before ordinary
  speech.
- [x] **REV-06**: User can apply category, speaker, and answer-decision labels
  from that queue without manually editing JSON files or losing the sample's
  original metadata.
- [x] **REV-07**: User can see review progress for one session, including
  remaining unknown speakers, unlabeled answer decisions, accepted/rejected
  counts, and whether classifier readiness blockers remain.

### Addressing v2

- [x] **INT-02**: User can distinguish direct handoffs from incidental name
  mentions such as "I helped John" or "John Doe" without treating every
  recognized name as `addressed_to_me`.
- [x] **INT-03**: User can see an addressing explanation in `trigger-check`
  that names the matched phrase, surrounding evidence, decision path, and why
  Saymo will answer, wait for confirmation, or skip.
- [x] **INT-04**: User can tune addressing behavior per profile with explicit
  patterns for handoff phrases, mention-only contexts, and surname/full-name
  ambiguity without hardcoding private names in source.
- [x] **INT-05**: User can replay saved false-positive and true-handoff samples
  against Addressing v2 and verify that known name-mention false positives are
  skipped.

### Speaker Bootstrap

- [x] **SPKR-04**: User can bootstrap speaker labels for a completed session
  without requiring always-on real-time diarization, using either reviewed
  diarization suggestions or a lightweight manual grouping workflow.
- [x] **SPKR-05**: User can apply session-scoped speaker labels in bulk while
  preserving manual labels as authoritative and keeping suggestion/audit
  metadata inspectable.
- [x] **QUAL-04**: User can see speaker coverage and classifier-readiness
  impact after bootstrap, including `me`, `other`, and `unknown` counts by
  session and category.

### Approved Draft Playback

- [x] **COCK-03**: User can route an explicitly approved answer draft through
  the existing local TTS and playback path into the configured call output
  device.
- [x] **COCK-04**: User can preview, monitor, cancel, or timeout approved draft
  playback before or during live-call output.
- [x] **AUD-03**: User can inspect audit events for approved draft playback,
  including draft id, action id, TTS engine, output route, playback start/end,
  cancellation, and blocked reasons.
- [x] **SAFE-01**: Saymo refuses to play unapproved generated draft text and
  keeps existing manual takeover and confirmation safety behavior intact.

### Regression Replay

- [x] **REG-01**: User can replay one saved capture session through current
  addressing, question, speaker, and classifier logic without re-recording
  audio.
- [x] **REG-02**: User can see session-level regression metrics for false
  handoffs, missed handoffs, question noise, speaker coverage, review coverage,
  and live-assist readiness.
- [x] **REG-03**: User can compare regression results before and after tuning
  and export a sanitized report that omits raw audio and secrets.

## Future Requirements

Deferred beyond v1.5.

### Native Capture

- User can use optional native macOS system-audio capture without BlackHole
  when OS permissions and entitlements are available.

### Cockpit UI

- User can use a richer desktop/browser cockpit after the CLI/TUI data
  contracts and approved playback flow are proven.

### Meeting Bot Integrations

- User can optionally connect a meeting bot or provider API for organizations
  that prefer bot-based capture.

### Cross-meeting Speaker Identity

- User can map recurring speakers across meetings through reviewed local
  speaker fingerprints.

### Semantic Meeting Search

- User can run local semantic/vector search across many meeting ledgers after
  transcript storage and sanitized exports are stable.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-speaking generated drafts without explicit approval | Live-call safety requires a human approval action before generated text reaches the call. |
| Required diarization dependency in the base install | Saymo must remain usable when optional ML backends, tokens, or model downloads are unavailable. |
| Real-time diarization inside `saymo auto` | Offline/bootstrap speaker labels are the lower-risk path until speaker quality is proven. |
| Native macOS capture | Useful, but less urgent than fixing false positives and approved playback in the current BlackHole path. |
| GUI-first cockpit | CLI/TUI contracts should remain the source of truth until safety and playback behavior are verified. |
| Meeting bot that joins calls | This milestone stays focused on the local assistant listening through the user's machine. |
| Training voice-clone models from call recordings | Captured call audio is for trigger/review/regression behavior, not voice identity training. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REV-05 | Phase 18 | Complete |
| REV-06 | Phase 18 | Complete |
| REV-07 | Phase 18 | Complete |
| INT-02 | Phase 19 | Complete |
| INT-03 | Phase 19 | Complete |
| INT-04 | Phase 19 | Complete |
| INT-05 | Phase 19 | Complete |
| SPKR-04 | Phase 20 | Complete |
| SPKR-05 | Phase 20 | Complete |
| QUAL-04 | Phase 20 | Complete |
| COCK-03 | Phase 21 | Complete |
| COCK-04 | Phase 21 | Complete |
| AUD-03 | Phase 21 | Complete |
| SAFE-01 | Phase 21 | Complete |
| REG-01 | Phase 22 | Complete |
| REG-02 | Phase 22 | Complete |
| REG-03 | Phase 22 | Complete |

**Coverage:**
- v1.5 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-05-21*
*Last updated: 2026-05-21 after initial v1.5 definition*

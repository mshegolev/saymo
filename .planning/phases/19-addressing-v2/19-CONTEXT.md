# Phase 19 Context: Addressing v2

## Goal

Stop treating every recognized name as an addressed-to-me handoff while keeping
true handoff detection explainable and tunable.

## Requirements

- INT-02: distinguish direct handoffs from incidental first-name/full-name
  mentions.
- INT-03: `trigger-check` explains matched phrase, surrounding evidence,
  decision path, and final action.
- INT-04: per-profile config can tune handoff and mention-only patterns.
- INT-05: saved false-positive/true-handoff samples can be replayed through the
  improved deterministic addressing layer.

## Existing System

- `saymo.analysis.addressing` owns deterministic addressing decisions.
- `saymo.analysis.trigger_capture.classify_trigger_sample` persists the
  addressing label and reason into sample JSON.
- `trigger-check`, provider latency diagnostics, trigger capture, answer draft,
  and auto mode all use the same deterministic addressing decision.

## Design Decisions

- Keep deterministic addressing as the live-call safety boundary.
- Make plain non-question name mentions skip unless they match an explicit
  handoff pattern or are a bare name call.
- Add configured `meetings.<profile>.addressing.handoff_patterns` and
  `mention_only_patterns` regexes with `{trigger}` placeholders.
- Print explanation fields in `trigger-check` without exposing secrets or
  changing response-cache behavior.


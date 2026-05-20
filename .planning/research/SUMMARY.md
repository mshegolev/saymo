# v1.3 Research Summary: Local Diarization Assist

## Stack Additions

- Add a backend-neutral diarization layer under `saymo.analysis`.
- Use optional backend imports; start with a disabled-by-default pyannote-style
  adapter.
- Store session sidecars locally under the existing trigger-sample/session
  hierarchy.

## Feature Table Stakes

- Backend availability diagnostics.
- Configurable local backend/model/device/token.
- Session diarization command.
- Speaker cluster summary and mapping.
- Review-first suggestion promotion.
- Speaker quality and conflict reports.

## Watch Outs

- Diarization clusters are not identity labels until mapped or reviewed.
- Optional model access and tokens must stay out of committed files and
  sanitized reports.
- Do not put real-time diarization into `saymo auto` until offline quality is
  proven.

## Roadmap Implication

Phase 11 should establish optional backend contracts. Phase 12 should write
session suggestions. Phase 13 should add review, promotion, and quality gates.

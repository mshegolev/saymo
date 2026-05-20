# v1.4 Research: Stack

## Scope

Milestone v1.4 adds local meeting memory and a live answer cockpit on top of
existing trigger-capture sessions, speaker labels, local source plugins, Ollama
composition, and BlackHole playback. The stack should preserve Saymo's
local-by-default model and avoid turning meeting bots or cloud APIs into the
main direction.

## Findings

- Similar local meeting assistants usually center on transcription, summaries,
  searchable archives, or meeting bots. Saymo's differentiator is a local
  "listen and answer as me" workflow with explicit user approval before speech.
- Existing session-ledger and trigger-sample storage should be extended before
  introducing a separate database. JSONL/JSON remains easy to audit, migrate,
  sanitize, and test.
- Search can start with deterministic local indexes over transcript segments
  and metadata. SQLite FTS or a vector index can be added later if simple
  keyword/time/speaker search is insufficient.
- Answer drafts can reuse the existing local LLM composer path. The new work is
  context assembly, citation metadata, confidence/trigger evidence, and a
  review gate before playback.
- The cockpit should start as CLI/TUI-friendly commands and hotkey-compatible
  actions, because current live-call control is already CLI/provider based.

## Recommended Stack Shape

- Add a meeting-memory module under `saymo.analysis` for transcript segments,
  indexes, session summaries, and cited retrieval results.
- Extend existing `trigger_sessions` storage instead of replacing it.
- Add answer-draft data contracts that keep draft text, source citations,
  trigger evidence, and approval state separate from audio playback.
- Add a local audit ledger for trigger decisions, generated drafts, user
  actions, and spoken responses.
- Keep native macOS capture and bot-join integrations as future optional
  directions, not required stack additions for v1.4.

## References

- https://github.com/Zackriya-Solutions/meetily
- https://github.com/paberr/ownscribe
- https://github.com/pretyflaco/meetscribe
- https://github.com/silverstein/minutes
- https://github.com/OpenWhispr/openwhispr
- https://github.com/Vexa-ai/vexa
- https://github.com/Meeting-BaaS/speaking-meeting-bot
- https://github.com/pipecat-ai/pipecat

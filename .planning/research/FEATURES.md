# v1.4 Research: Features

## Table Stakes

- Full-session transcript ledger: user can keep chronological transcript
  segments for a recorded meeting, including timestamps, confidence, source
  window, and speaker label/suggestion metadata.
- Meeting summaries: user can inspect a concise summary, questions, handoffs,
  and action items for one session without opening raw JSON.
- Local meeting search: user can search current or past sessions by profile,
  date, speaker, keyword, category, or trigger status.
- Ask a meeting: user can ask a question about one session and get a local
  answer with citations back to transcript segments.
- Source-grounded answer draft: when addressed, Saymo can draft an answer using
  meeting context plus configured Jira/Confluence/Obsidian/file sources.
- Explicit action gate: user chooses speak, edit, skip, or takeover before a
  generated draft is played into the call.
- Audit trail: user can review why Saymo triggered, what it drafted, what
  sources it used, and what action was taken.

## Differentiators

- Saymo is not primarily another post-meeting summarizer; it is a live local
  assistant for moments where the user is expected to answer.
- The cockpit makes live assistance inspectable: trigger evidence, draft,
  citations, confidence, and the next action are visible before speech.
- The same local session memory supports post-call training, missed-trigger
  debugging, and live answer grounding.
- Manual takeover remains a first-class action, not an exception.

## Anti-Features

- Do not make Saymo auto-speak unreviewed generated answers by default.
- Do not require cloud transcription, cloud LLMs, or a remote meeting bot.
- Do not store raw audio, transcript, or source snippets in committed files.
- Do not add a broad desktop GUI before the CLI/TUI control path is proven.

# v1.4 Research: Pitfalls

## Privacy And Storage Risk

- Full transcripts are more sensitive than trigger samples. Keep storage local,
  configurable, and easy to purge/export in sanitized form.
- Source snippets from Jira, Confluence, Obsidian, or files may include private
  project names. Reports and committed docs must use sanitized examples only.
- A meeting ask command should cite local evidence without copying large raw
  transcripts into logs by default.

## Live-Call Safety Risk

- A confident-looking draft can still be wrong or stale. Keep explicit
  approval before playback and show source evidence beside the draft.
- Trigger evidence and answer confidence are different signals. Do not collapse
  them into a single "safe to speak" boolean.
- Hotkeys and cockpit commands must preserve manual takeover as a normal path.

## Product Scope Risk

- Meeting-bot direction can distract from Saymo's core value. Bot join,
  screen-share, and cloud streaming are future integrations, not the main v1.4
  milestone.
- A GUI can become expensive before the core workflow is proven. Start with
  commands/TUI-compatible output and stable data contracts.
- Native macOS capture would be valuable but may require OS-version checks,
  permissions, and entitlements. Treat it as future optional capture work.

## Integration Risk

- Existing trigger sessions may have partial transcript data. Commands should
  report incomplete ledgers instead of failing.
- Transcript search can become slow as sessions grow. Keep indexes incremental
  and profile/session-scoped first.
- Answer drafts must compose from stale or missing source plugins gracefully and
  show diagnostics when sources were unavailable.

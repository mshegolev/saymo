<!--
Thanks for your PR! A few prompts below to help reviewers move quickly.
Delete sections that don't apply.
-->

## What

<!-- One or two sentences. What does this change do? -->

## Why

<!-- Motivation. Link the issue if there is one: "Fixes #123". -->

## How

<!-- Brief notes on the approach if it's non-obvious.
     Skip for trivial changes. -->

## Testing

<!-- How did you verify this works? Mark all that apply. -->

- [ ] `uv run pytest` passes locally
- [ ] Manual smoke test via CLI (note the command)
- [ ] Audio quality verified with `saymo train-eval` or `saymo test-tts` (for TTS changes)
- [ ] Tested on a real call (for provider/audio routing changes)
- [ ] N/A — docs / chore only

## Checklist

- [ ] Code follows the conventions in [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- [ ] No personal data, secrets, or codenames hardcoded — config.yaml is the right place
- [ ] If a prompt or default config changed, `config.example.yaml` is updated to match
- [ ] If a public CLI command/flag changed, `README.md` and `docs/` are updated
- [ ] [`CHANGELOG.md`](../CHANGELOG.md) `[Unreleased]` section reflects user-facing changes

## Screenshots / output

<!-- For UI/audio/CLI output changes, paste a sample. -->

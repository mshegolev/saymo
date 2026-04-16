"""Obsidian daily notes source — reads markdown files from vault."""


class ObsidianSource:
    name = "obsidian"
    description = "Read daily notes from Obsidian vault"

    async def fetch(self, config) -> dict | None:
        from saymo.obsidian.daily_notes import read_standup_notes

        vault = config.obsidian.vault_path
        if not vault:
            return None

        notes = read_standup_notes(
            vault, config.obsidian.subfolder, config.obsidian.date_format
        )

        if not notes.get("yesterday") and not notes.get("today"):
            return None

        return notes

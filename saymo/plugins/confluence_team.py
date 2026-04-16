"""Confluence/JIRA team source — fetches tasks for all team members."""

import yaml
from pathlib import Path


class ConfluenceTeamSource:
    name = "confluence_team"
    description = "JIRA tasks for whole team (scrum mode)"

    async def fetch(self, config) -> dict | None:
        from saymo.jira_source.confluence_tasks import fetch_team_tasks, team_tasks_to_notes

        # Read team members from config
        team_members = None
        cfg_path = Path(__file__).parent.parent.parent / "config.yaml"
        if cfg_path.exists():
            raw = yaml.safe_load(cfg_path.read_text()) or {}
            if "team" in raw and isinstance(raw["team"], dict):
                team_members = raw["team"]

        daily = await fetch_team_tasks(config.jira, team_members)
        if not any(m.today or m.yesterday for m in daily.members.values()):
            return None
        return team_tasks_to_notes(daily)

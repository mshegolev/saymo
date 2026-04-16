"""Confluence/JIRA source — fetches tasks using same JQL as update_confluence.py."""

from saymo.plugins.base import SourcePlugin


class ConfluenceSource:
    name = "confluence"
    description = "JIRA tasks (same JQL as update_confluence.py)"

    async def fetch(self, config) -> dict | None:
        from saymo.jira_source.confluence_tasks import fetch_daily_tasks, tasks_to_notes
        daily = await fetch_daily_tasks(config.jira)
        if not daily.today and not daily.yesterday:
            return None
        return tasks_to_notes(daily)

"""Simple JIRA source — basic JQL query for current user's tasks."""


class JiraSimpleSource:
    name = "jira"
    description = "Simple JIRA query (assignee = currentUser, updated last day)"

    async def fetch(self, config) -> dict | None:
        from saymo.jira_source.tasks import fetch_standup_data

        data = await fetch_standup_data(config.jira)
        if not data.tasks:
            return None

        tasks_text = "\n".join(data.task_summary_lines)
        return {
            "yesterday": tasks_text,
            "today": "(plan based on task statuses)",
            "yesterday_date": "вчера",
            "today_date": "сегодня",
        }

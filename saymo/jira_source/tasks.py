"""JIRA task fetcher for stand-up reports.

Uses the official ``jira`` Python SDK with token-based auth. Both the
Jira server URL and the PAT/token come from ``config.yaml`` —
nothing is hardcoded here.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from saymo.config import JiraConfig

logger = logging.getLogger("saymo.jira")


@dataclass
class JiraTask:
    key: str
    summary: str
    status: str
    issue_type: str
    updated: str = ""


@dataclass
class StandupData:
    tasks: list[JiraTask] = field(default_factory=list)
    fetched_at: str = ""

    @property
    def task_summary_lines(self) -> list[str]:
        """One-line summary per task for LLM prompt."""
        return [f"[{t.key}] {t.summary} (status: {t.status})" for t in self.tasks]


def _create_jira_client(config: JiraConfig):
    """Create a JIRA client using token-based auth from user config."""
    from jira import JIRA

    return JIRA(
        server=config.url,
        token_auth=config.token,
        options={"verify": False},
    )


def _fetch_tasks_sync(config: JiraConfig) -> StandupData:
    """Synchronous JIRA fetch (runs in thread)."""
    import warnings
    warnings.filterwarnings("ignore")

    client = _create_jira_client(config)
    issues = client.search_issues(
        config.user_query,
        maxResults=config.max_results,
    )

    tasks = []
    for issue in issues:
        tasks.append(JiraTask(
            key=issue.key,
            summary=issue.fields.summary,
            status=str(issue.fields.status),
            issue_type=str(issue.fields.issuetype),
            updated=str(issue.fields.updated)[:10] if issue.fields.updated else "",
        ))

    logger.info(f"Fetched {len(tasks)} tasks from JIRA")
    return StandupData(
        tasks=tasks,
        fetched_at=datetime.now().isoformat(),
    )


async def fetch_standup_data(config: JiraConfig) -> StandupData:
    """Fetch JIRA tasks for stand-up report (async wrapper)."""
    return await asyncio.to_thread(_fetch_tasks_sync, config)

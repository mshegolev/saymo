"""JIRA task fetcher for standup reports. Wraps selfhelper JiraCrud."""

import asyncio
import logging
import sys
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
    """Create JiraCrud instance using selfhelper or direct config."""
    if config.use_selfhelper_config:
        sys.path.insert(0, config.selfhelper_path)
        from scripts.jira_crud import JiraCrud
        return JiraCrud()
    else:
        # Direct JIRA connection without selfhelper
        from jira import JIRA
        client = JIRA(
            server=config.url,
            token_auth=config.token,
            options={"verify": False},
        )
        return client


def _fetch_tasks_sync(config: JiraConfig) -> StandupData:
    """Synchronous JIRA fetch (runs in thread)."""
    import warnings
    warnings.filterwarnings("ignore")

    jira_crud = _create_jira_client(config)

    if config.use_selfhelper_config:
        # Use JiraCrud.jira property to get the underlying JIRA client
        issues = jira_crud.jira.search_issues(
            config.user_query,
            maxResults=config.max_results,
        )
    else:
        issues = jira_crud.search_issues(
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
    """Fetch JIRA tasks for standup report (async wrapper)."""
    return await asyncio.to_thread(_fetch_tasks_sync, config)

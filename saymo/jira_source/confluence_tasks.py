"""Fetch tasks using the same logic as update_confluence.py.

Reuses the JQL from TaskSyncer to get today's active tasks
and yesterday's tasks from the previous business day.
"""

import asyncio
import logging
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from saymo.config import JiraConfig

logger = logging.getLogger("saymo.jira.confluence")

# Same JQL as update_confluence.py TaskSyncer.get_today_tasks()
TODAY_JQL = """project = "Data Platform Engineering" AND \
(status in ("In Progress", "Blocked", "Review") OR \
status changed from "In Progress" to Closed during (now(), -1d)) \
AND assignee in (m.v.shchegolev, oleg.o.korytov)"""


@dataclass
class TaskInfo:
    key: str
    summary: str
    status: str
    assignee: str = ""


@dataclass
class DailyTasks:
    today: list[TaskInfo] = field(default_factory=list)
    yesterday: list[TaskInfo] = field(default_factory=list)
    today_date: str = ""
    yesterday_date: str = ""


def _get_previous_business_day() -> datetime:
    """Calculate previous business day (skip weekends)."""
    today = datetime.today()
    one_day = timedelta(days=1)
    previous = today - one_day
    while previous.weekday() >= 5:  # Saturday=5, Sunday=6
        previous -= one_day
    return previous


def _fetch_sync(config: JiraConfig) -> DailyTasks:
    """Synchronous fetch of today + yesterday tasks from JIRA."""
    warnings.filterwarnings("ignore")

    sys.path.insert(0, config.selfhelper_path)
    from jira import JIRA
    from config.constants import JIRA_URL, JIRA_TOKEN

    jira = JIRA(server=JIRA_URL, token_auth=JIRA_TOKEN, options={"verify": False})

    # Today's tasks — same JQL as update_confluence.py
    today_issues = jira.search_issues(TODAY_JQL, maxResults=30)
    today_tasks = []
    for issue in today_issues:
        assignee = ""
        if issue.fields.assignee:
            assignee = getattr(issue.fields.assignee, 'displayName',
                              getattr(issue.fields.assignee, 'name', ''))
        today_tasks.append(TaskInfo(
            key=issue.key,
            summary=issue.fields.summary,
            status=str(issue.fields.status),
            assignee=assignee,
        ))

    # Yesterday's tasks — tasks updated on previous business day
    prev_day = _get_previous_business_day()
    prev_str = prev_day.strftime("%Y-%m-%d")
    next_str = (prev_day + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_jql = (
        f'project = "Data Platform Engineering" '
        f'AND assignee = m.v.shchegolev '
        f'AND updated >= "{prev_str}" AND updated < "{next_str}" '
        f'ORDER BY updated DESC'
    )

    yesterday_issues = jira.search_issues(yesterday_jql, maxResults=30)
    yesterday_tasks = []
    for issue in yesterday_issues:
        yesterday_tasks.append(TaskInfo(
            key=issue.key,
            summary=issue.fields.summary,
            status=str(issue.fields.status),
        ))

    logger.info(f"Fetched {len(today_tasks)} today + {len(yesterday_tasks)} yesterday tasks")

    return DailyTasks(
        today=today_tasks,
        yesterday=yesterday_tasks,
        today_date=datetime.today().strftime("%Y-%m-%d"),
        yesterday_date=prev_str,
    )


async def fetch_daily_tasks(config: JiraConfig) -> DailyTasks:
    """Async wrapper for JIRA task fetch."""
    return await asyncio.to_thread(_fetch_sync, config)


def tasks_to_notes(daily: DailyTasks) -> dict:
    """Convert DailyTasks to notes dict format for composer."""
    yesterday_lines = []
    for t in daily.yesterday:
        yesterday_lines.append(f"- [{t.key}] {t.summary} (status: {t.status})")

    today_lines = []
    for t in daily.today:
        today_lines.append(f"- [{t.key}] {t.summary} (status: {t.status})")

    return {
        "yesterday": "\n".join(yesterday_lines) if yesterday_lines else None,
        "today": "\n".join(today_lines) if today_lines else None,
        "yesterday_date": daily.yesterday_date,
        "today_date": daily.today_date,
    }

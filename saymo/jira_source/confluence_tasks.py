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


@dataclass
class TeamDailyTasks:
    """Tasks grouped by team member."""
    members: dict[str, DailyTasks] = field(default_factory=dict)
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


DEFAULT_TEAM_MEMBERS = {
    "m.v.shchegolev": "Михаил",
    "oleg.o.korytov": "Олег",
}


def _fetch_team_sync(config: JiraConfig, team_members: dict | None = None) -> TeamDailyTasks:
    """Fetch tasks for all team members."""
    warnings.filterwarnings("ignore")

    sys.path.insert(0, config.selfhelper_path)
    from jira import JIRA
    from config.constants import JIRA_URL, JIRA_TOKEN

    jira = JIRA(server=JIRA_URL, token_auth=JIRA_TOKEN, options={"verify": False})

    prev_day = _get_previous_business_day()
    prev_str = prev_day.strftime("%Y-%m-%d")
    next_str = (prev_day + timedelta(days=1)).strftime("%Y-%m-%d")

    members = team_members or DEFAULT_TEAM_MEMBERS

    result = TeamDailyTasks(
        today_date=datetime.today().strftime("%Y-%m-%d"),
        yesterday_date=prev_str,
    )

    for username, display_name in members.items():
        # Today
        today_jql = (
            f'project = "Data Platform Engineering" '
            f'AND (status in ("In Progress", "Blocked", "Review") '
            f'OR status changed from "In Progress" to Closed during (now(), -1d)) '
            f'AND assignee = {username}'
        )
        today_issues = jira.search_issues(today_jql, maxResults=30)
        today_tasks = [
            TaskInfo(
                key=i.key, summary=i.fields.summary,
                status=str(i.fields.status), assignee=display_name,
            )
            for i in today_issues
        ]

        # Yesterday
        yesterday_jql = (
            f'project = "Data Platform Engineering" '
            f'AND assignee = {username} '
            f'AND updated >= "{prev_str}" AND updated < "{next_str}" '
            f'ORDER BY updated DESC'
        )
        yesterday_issues = jira.search_issues(yesterday_jql, maxResults=30)
        yesterday_tasks = [
            TaskInfo(
                key=i.key, summary=i.fields.summary,
                status=str(i.fields.status), assignee=display_name,
            )
            for i in yesterday_issues
        ]

        result.members[display_name] = DailyTasks(
            today=today_tasks,
            yesterday=yesterday_tasks,
            today_date=result.today_date,
            yesterday_date=prev_str,
        )
        logger.info(f"{display_name}: {len(today_tasks)} today + {len(yesterday_tasks)} yesterday")

    return result


async def fetch_daily_tasks(config: JiraConfig) -> DailyTasks:
    """Async wrapper for personal task fetch."""
    return await asyncio.to_thread(_fetch_sync, config)


async def fetch_team_tasks(config: JiraConfig, team_members: dict | None = None) -> TeamDailyTasks:
    """Async wrapper for team task fetch."""
    return await asyncio.to_thread(_fetch_team_sync, config, team_members)


def team_tasks_to_notes(team: TeamDailyTasks) -> dict:
    """Convert TeamDailyTasks to notes dict for team scrum composer."""
    yesterday_lines = []
    today_lines = []

    for name, tasks in team.members.items():
        if tasks.yesterday:
            yesterday_lines.append(f"\n{name}:")
            for t in tasks.yesterday:
                yesterday_lines.append(f"  - {t.summary} (status: {t.status})")
        if tasks.today:
            today_lines.append(f"\n{name}:")
            for t in tasks.today:
                today_lines.append(f"  - {t.summary} (status: {t.status})")

    return {
        "yesterday": "\n".join(yesterday_lines) if yesterday_lines else None,
        "today": "\n".join(today_lines) if today_lines else None,
        "yesterday_date": team.yesterday_date,
        "today_date": team.today_date,
    }


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

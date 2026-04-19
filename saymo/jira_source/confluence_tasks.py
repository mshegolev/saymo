"""Fetch tasks from JIRA for the speech composer.

Both the Jira project key and the team-member mapping are supplied through
``config.yaml`` — no project-specific identifiers or usernames are hardcoded
in source.
"""

import asyncio
import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from saymo.config import JiraConfig

logger = logging.getLogger("saymo.jira.confluence")


# JQL templates — ``{project_key}`` and ``{assignees}`` / ``{assignee}`` are
# resolved at runtime from config. Keep templates here instead of string-
# concatenating inside functions so users can override them in config too.
PERSONAL_TODAY_JQL = (
    'project = "{project_key}" AND '
    '(status in ("In Progress", "Blocked", "Review") OR '
    'status changed from "In Progress" to Closed during (now(), -1d)) AND '
    'assignee = currentUser()'
)

PERSONAL_YESTERDAY_JQL = (
    'project = "{project_key}" AND assignee = currentUser() '
    'AND updated >= "{yesterday}" AND updated < "{today}" '
    'ORDER BY updated DESC'
)

TEAM_TODAY_JQL = (
    'project = "{project_key}" AND '
    '(status in ("In Progress", "Blocked", "Review") OR '
    'status changed from "In Progress" to Closed during (now(), -1d)) AND '
    'assignee = {assignee}'
)

TEAM_YESTERDAY_JQL = (
    'project = "{project_key}" AND assignee = {assignee} '
    'AND updated >= "{yesterday}" AND updated < "{today}" '
    'ORDER BY updated DESC'
)


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


def _jira_client(config: JiraConfig):
    """Build a JIRA client using token-based auth from user config."""
    from jira import JIRA
    return JIRA(server=config.url, token_auth=config.token, options={"verify": False})


def _project_key(config: JiraConfig) -> str:
    """Extract the configured Jira project key. Empty when user didn't set one."""
    return getattr(config, "project_key", "") or ""


def _fetch_sync(config: JiraConfig) -> DailyTasks:
    """Synchronous fetch of today + yesterday tasks for the current user."""
    warnings.filterwarnings("ignore")

    jira = _jira_client(config)

    prev_day = _get_previous_business_day()
    prev_str = prev_day.strftime("%Y-%m-%d")
    next_str = (prev_day + timedelta(days=1)).strftime("%Y-%m-%d")
    project_key = _project_key(config)

    today_jql = PERSONAL_TODAY_JQL.format(project_key=project_key)
    yesterday_jql = PERSONAL_YESTERDAY_JQL.format(
        project_key=project_key, yesterday=prev_str, today=next_str
    )

    today_issues = jira.search_issues(today_jql, maxResults=30)
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

    yesterday_issues = jira.search_issues(yesterday_jql, maxResults=30)
    yesterday_tasks = [
        TaskInfo(key=i.key, summary=i.fields.summary, status=str(i.fields.status))
        for i in yesterday_issues
    ]

    logger.info(f"Fetched {len(today_tasks)} today + {len(yesterday_tasks)} yesterday tasks")
    return DailyTasks(
        today=today_tasks,
        yesterday=yesterday_tasks,
        today_date=datetime.today().strftime("%Y-%m-%d"),
        yesterday_date=prev_str,
    )


# Team-member map is always supplied by the caller via ``config.yaml`` —
# either ``meetings.<profile>.team_members`` or a top-level ``team`` section.
# Empty default ensures no personal usernames end up in source control.
DEFAULT_TEAM_MEMBERS: dict[str, str] = {}


def _fetch_team_sync(config: JiraConfig, team_members: dict | None = None) -> TeamDailyTasks:
    """Fetch tasks for each configured team member."""
    warnings.filterwarnings("ignore")

    jira = _jira_client(config)

    prev_day = _get_previous_business_day()
    prev_str = prev_day.strftime("%Y-%m-%d")
    next_str = (prev_day + timedelta(days=1)).strftime("%Y-%m-%d")
    project_key = _project_key(config)

    members = team_members or DEFAULT_TEAM_MEMBERS
    if not members:
        logger.warning("No team members configured — returning empty TeamDailyTasks")

    result = TeamDailyTasks(
        today_date=datetime.today().strftime("%Y-%m-%d"),
        yesterday_date=prev_str,
    )

    for username, display_name in members.items():
        today_jql = TEAM_TODAY_JQL.format(project_key=project_key, assignee=username)
        yesterday_jql = TEAM_YESTERDAY_JQL.format(
            project_key=project_key, assignee=username,
            yesterday=prev_str, today=next_str,
        )

        today_issues = jira.search_issues(today_jql, maxResults=30)
        yesterday_issues = jira.search_issues(yesterday_jql, maxResults=30)

        today_tasks = [
            TaskInfo(key=i.key, summary=i.fields.summary,
                     status=str(i.fields.status), assignee=display_name)
            for i in today_issues
        ]
        yesterday_tasks = [
            TaskInfo(key=i.key, summary=i.fields.summary,
                     status=str(i.fields.status), assignee=display_name)
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
    """Convert DailyTasks to notes dict for the personal composer."""
    yesterday_lines = [f"- {t.summary} (status: {t.status})" for t in daily.yesterday]
    today_lines = [f"- {t.summary} (status: {t.status})" for t in daily.today]
    return {
        "yesterday": "\n".join(yesterday_lines) if yesterday_lines else None,
        "today": "\n".join(today_lines) if today_lines else None,
        "yesterday_date": daily.yesterday_date,
        "today_date": daily.today_date,
    }

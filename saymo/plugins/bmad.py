"""BMAD sprint status source for daily standup summaries."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from saymo.plugins.base import SourcePlugin

logger = logging.getLogger("saymo.plugins.bmad")

_ACTIVE = {"in-progress", "in progress", "started", "doing", "review"}
_BLOCKED = {"blocked", "impeded"}
_PLANNED = {"planned", "backlog", "ready", "ready-for-dev", "queued"}
_COMPLETED = {"completed", "complete", "done"}


def _read_yaml(path: Path) -> dict | None:
    try:
        with path.open(encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
    except FileNotFoundError:
        return None
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Could not read BMAD status file %s: %s", path, exc)
        return None
    return value if isinstance(value, dict) else None


def _sprint_stories(data: dict | None) -> list[dict]:
    if not data:
        return []
    stories = data.get("stories")
    if not isinstance(stories, list):
        return []
    return [story for story in stories if isinstance(story, dict)]


def _workflow_stories(data: dict | None) -> list[dict]:
    if not data:
        return []
    phases = data.get("phases")
    if not isinstance(phases, dict):
        return []
    implementation = phases.get("phase_4_implementation")
    if not isinstance(implementation, dict):
        return []
    stories = implementation.get("stories")
    if not isinstance(stories, dict):
        return []
    story_list = stories.get("story_list")
    if not isinstance(story_list, list):
        return []
    return [story for story in story_list if isinstance(story, dict)]


def _status(story: dict) -> str:
    return str(story.get("status") or "").strip().lower().replace("_", "-")


def _story_label(story: dict) -> str:
    identifier = str(story.get("id") or "").strip()
    title = str(story.get("title") or story.get("name") or "").strip()
    if identifier and title:
        return f"{identifier}: {title}"
    return identifier or title or "Untitled story"


def _in_current_sprint(story: dict, sprint_number: object) -> bool:
    story_sprint = story.get("sprint")
    if sprint_number is None or story_sprint is None:
        return True
    return str(story_sprint) == str(sprint_number)


class BmadSource(SourcePlugin):
    name = "bmad"
    description = "Local BMAD sprint and workflow status"

    async def fetch(self, config) -> dict | None:
        bmad_config = getattr(config, "bmad", None)
        if bmad_config is None:
            return None

        project_path = Path(bmad_config.project_path).expanduser()
        sprint_data = _read_yaml(project_path / bmad_config.sprint_status_file)
        workflow_data = _read_yaml(project_path / bmad_config.workflow_status_file)
        if sprint_data is None and workflow_data is None:
            return None

        sprint = sprint_data.get("sprint") if sprint_data else None
        sprint = sprint if isinstance(sprint, dict) else {}
        sprint_number = sprint.get("number")

        stories = _sprint_stories(sprint_data)
        if not stories:
            stories = _workflow_stories(workflow_data)
        stories = [story for story in stories if _in_current_sprint(story, sprint_number)]

        active = [story for story in stories if _status(story) in _ACTIVE]
        blocked = [story for story in stories if _status(story) in _BLOCKED]
        planned = [story for story in stories if _status(story) in _PLANNED]
        completed_count = sum(_status(story) in _COMPLETED for story in stories)

        # BMAD versions differ in where they keep aggregate counts. Prefer the
        # story list when present, then use their explicit metrics as fallback.
        total_count = len(stories)
        phases = (workflow_data or {}).get("phases")
        phases = phases if isinstance(phases, dict) else {}
        workflow_phase = phases.get("phase_4_implementation", {})
        workflow_summary = workflow_phase.get("stories", {}) if isinstance(workflow_phase, dict) else {}
        metrics = (sprint_data or {}).get("metrics", {})
        if not total_count:
            total_count = int(
                workflow_summary.get("total", 0)
                or (metrics.get("total_stories", 0) if isinstance(metrics, dict) else 0)
                or 0
            )
            completed_count = int(
                workflow_summary.get("completed", 0)
                or (metrics.get("completed_stories", 0) if isinstance(metrics, dict) else 0)
                or 0
            )
            active_count = int(workflow_summary.get("in_progress", 0) or 0)
            blocked_count = int(
                workflow_summary.get("blocked", 0)
                or (metrics.get("blocked_stories", 0) if isinstance(metrics, dict) else 0)
                or 0
            )
        else:
            active_count = len(active)
            blocked_count = len(blocked)

        try:
            max_stories = max(1, int(getattr(bmad_config, "max_stories", 5) or 5))
        except (TypeError, ValueError):
            max_stories = 5
        parts = []
        if sprint_number is not None:
            parts.append(f"BMAD sprint {sprint_number}")
        if sprint.get("goal"):
            parts.append(f"Goal: {sprint['goal']}")
        if total_count:
            parts.append(
                f"Progress: {completed_count}/{total_count} stories completed, "
                f"{active_count} in progress, {blocked_count} blocked"
            )
        for label, items in (
            ("In progress", active),
            ("Blocked", blocked),
            ("Next", planned),
        ):
            if items:
                titles = "; ".join(_story_label(story) for story in items[:max_stories])
                parts.append(f"{label}: {titles}")

        summary = ". ".join(parts).strip()
        if not summary:
            return None
        return {
            "yesterday": None,
            "today": summary,
            "yesterday_date": "",
            "today_date": "",
        }

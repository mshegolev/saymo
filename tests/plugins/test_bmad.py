import asyncio
from types import SimpleNamespace

from saymo.plugins.bmad import BmadSource


def _config(root, *, max_stories=5):
    return SimpleNamespace(
        bmad=SimpleNamespace(
            project_path=str(root),
            sprint_status_file="bmad/sprint-status.yaml",
            workflow_status_file="bmad/workflow-status.yaml",
            max_stories=max_stories,
        )
    )


def test_fetch_uses_workflow_story_list_when_sprint_list_is_empty(tmp_path):
    bmad_dir = tmp_path / "bmad"
    bmad_dir.mkdir()
    (bmad_dir / "sprint-status.yaml").write_text(
        "sprint:\n  number: 1\nstories: []\n", encoding="utf-8"
    )
    (bmad_dir / "workflow-status.yaml").write_text(
        """phases:
  phase_4_implementation:
    stories:
      total: 3
      completed: 1
      in_progress: 1
      blocked: 0
      story_list:
        - id: S1.1
          title: Finish setup
          sprint: 1
          status: in_progress
        - id: S1.2
          title: Add plugin
          sprint: 1
          status: planned
        - id: S2.1
          title: Later work
          sprint: 2
          status: planned
""",
        encoding="utf-8",
    )

    result = asyncio.run(BmadSource().fetch(_config(tmp_path)))

    assert result is not None
    assert result["yesterday"] is None
    assert "Progress: 0/2 stories completed, 1 in progress, 0 blocked" in result["today"]
    assert "S1.1: Finish setup" in result["today"]
    assert "S1.2: Add plugin" in result["today"]
    assert "Later work" not in result["today"]


def test_fetch_reads_sprint_stories_and_limits_story_titles(tmp_path):
    bmad_dir = tmp_path / "bmad"
    bmad_dir.mkdir()
    (bmad_dir / "sprint-status.yaml").write_text(
        """sprint:
  number: 4
  goal: Ship BMAD support
stories:
  - id: S4.1
    title: Build source
    sprint: 4
    status: in-progress
  - id: S4.2
    title: Review source
    sprint: 4
    status: blocked
  - id: S5.1
    title: Future story
    sprint: 5
    status: planned
""",
        encoding="utf-8",
    )

    result = asyncio.run(BmadSource().fetch(_config(tmp_path, max_stories=1)))

    assert result is not None
    assert "BMAD sprint 4" in result["today"]
    assert "Goal: Ship BMAD support" in result["today"]
    assert "S4.1: Build source" in result["today"]
    assert "S4.2: Review source" in result["today"]
    assert "Future story" not in result["today"]


def test_fetch_returns_none_when_status_files_are_missing(tmp_path):
    assert asyncio.run(BmadSource().fetch(_config(tmp_path))) is None

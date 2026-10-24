# BMAD source plugin

Saymo can use a local BMAD Method project as a standup content source. The
plugin reads sprint and workflow status YAML and reports sprint progress,
in-progress or blocked stories, and planned stories. It does not modify BMAD
artifacts.

Configure the BMAD project root and select the source:

```yaml
speech:
  source: bmad

bmad:
  project_path: "/path/to/project"
  sprint_status_file: "bmad/sprint-status.yaml"
  workflow_status_file: "bmad/workflow-status.yaml"
  max_stories: 5
```

If `sprint-status.yaml` has no story entries, Saymo falls back to
`phase_4_implementation.stories.story_list` in `workflow-status.yaml`. The
source supports story records with `id`, `title` (or `name`), `sprint`, and
`status` fields. If neither configured file exists or contains usable status
data, `saymo prepare` reports that the source has no content.

Check that the plugin is discovered with:

```bash
saymo list-plugins
```

# Summary 07-03: Latency History Export and Docs

## Completed

- Added provider latency report dataclasses and local JSON/Markdown export.
- Wrote history under `~/.saymo/provider_latency/<profile>/<provider>/` by
  default, with `--output-dir` override.
- Documented the command in README, Quick Start, and PRD.

## Files

- `saymo/analysis/provider_latency.py`
- `README.md`
- `docs/QUICK-START.md`
- `docs/PRD.md`
- `tests/test_provider_latency.py`

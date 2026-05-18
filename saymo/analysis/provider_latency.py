"""Provider latency probe reports and local history export."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProviderLatencySegment:
    """One measured step in a provider latency probe."""

    name: str
    duration_ms: float
    status: str = "ok"
    detail: str = ""


@dataclass(frozen=True)
class ProviderLatencyReport:
    """Serializable provider latency probe result."""

    profile: str
    provider: str
    created_at: str
    status: str
    transcript: str
    action: str
    audio_path: str
    blocked_step: str = ""
    blocked_reason: str = ""
    segments: list[ProviderLatencySegment] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["segments"] = [asdict(segment) for segment in self.segments]
        return data


def write_latency_history(
    report: ProviderLatencyReport,
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Write report history as JSON and Markdown under profile/provider."""
    base_dir = (
        Path(output_dir).expanduser()
        if output_dir
        else Path.home() / ".saymo" / "provider_latency"
    )
    history_dir = (
        base_dir
        / _safe_path_part(report.profile)
        / _safe_path_part(report.provider)
    )
    history_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_timestamp(report.created_at)
    json_path = history_dir / f"{stem}.json"
    md_path = history_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_latency_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_latency_markdown(report: ProviderLatencyReport) -> str:
    """Render a compact Markdown latency report."""
    lines = [
        "# Saymo Provider Latency Probe",
        "",
        f"profile: {report.profile}",
        f"provider: {report.provider}",
        f"created_at: {report.created_at}",
        f"probe: {report.status}",
        f"action: {report.action}",
    ]
    if report.blocked_step:
        lines.append(f"blocked: {report.blocked_step}: {report.blocked_reason}")
    lines.extend(["", "## Segments", ""])
    for segment in report.segments:
        detail = f" — {segment.detail}" if segment.detail else ""
        lines.append(
            f"- {segment.name}: {segment.duration_ms:.0f} ms"
            f" ({segment.status}){detail}"
        )
    return "\n".join(lines) + "\n"


def _safe_path_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", (value or "default").strip())
    return safe.strip("._-") or "default"


def _safe_timestamp(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_.-]+", "-", value.strip())
    return safe.strip("-") or "latency"

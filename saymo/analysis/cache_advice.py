"""Read-only advice for expensive voice cache regeneration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from saymo.analysis.cache_metadata import (
    build_voice_cache_metadata,
    check_voice_cache_metadata,
)
from saymo.analysis.response_cache import (
    ResponseCache,
    build_library,
    response_cache_coverage,
)


@dataclass(frozen=True)
class CacheAdvice:
    key: str
    title: str
    status: str
    reason: str = ""
    ok: bool = False
    expensive: bool = False
    warning: str = ""
    action: str = ""
    rerun: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def prepared_audio_cache_advice(
    config,
    audio_path: str | Path,
    *,
    profile: str,
    team: bool = False,
) -> CacheAdvice:
    """Return read-only repair advice for one prepared standup WAV."""
    path = Path(audio_path).expanduser()
    expected = build_voice_cache_metadata(config, purpose="prepare")
    check = check_voice_cache_metadata(path, expected)
    if check.valid:
        return CacheAdvice(
            key="prepared_audio",
            title="prepared audio",
            status="ready",
            ok=True,
            action="No regeneration needed; prepared audio is current.",
            metadata={"team": bool(team), "path_name": path.name},
        )

    status = _status_from_reason(check.blocked_reason)
    expensive = _is_f5(config, purpose="prepare") and status in {"missing", "stale"}
    return CacheAdvice(
        key="prepared_audio",
        title="prepared audio",
        status=status,
        reason=check.blocked_reason,
        ok=False,
        expensive=expensive,
        warning=_f5_warning(
            "F5 regeneration can be expensive; this rebuilds only today's prepared audio."
        )
        if expensive
        else "",
        action=f"Run saymo prepare -p {profile} to rebuild prepared audio only.",
        rerun=f"saymo auto-preflight -p {profile}",
        metadata={
            "team": bool(team),
            "path_name": path.name,
            "blocked_reason": check.blocked_reason,
        },
    )


def response_cache_advice(config, *, profile: str) -> CacheAdvice:
    """Return read-only repair advice for the response cache."""
    if not config.responses.enabled:
        return CacheAdvice(
            key="response_cache",
            title="response cache",
            status="disabled",
            reason="response_cache_disabled",
            ok=False,
            expensive=False,
            action="Set responses.enabled=true, then run saymo prepare-responses.",
            rerun=f"saymo auto-preflight -p {profile}",
            metadata={"ready": 0, "total": 0, "missing_count": 0, "stale_count": 0},
        )

    library = build_library(config.responses.library)
    cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None
    cache = ResponseCache(
        library=library,
        cache_dir=cache_dir,
        confidence_threshold=config.responses.confidence_threshold,
        voice_metadata=build_voice_cache_metadata(config, purpose="response_cache"),
    )
    coverage = response_cache_coverage(cache)
    missing_count = len(coverage.missing)
    stale_count = len(coverage.stale)
    if coverage.ready == coverage.total:
        return CacheAdvice(
            key="response_cache",
            title="response cache",
            status="ready",
            ok=True,
            action="No regeneration needed; response cache is current.",
            metadata={
                "ready": coverage.ready,
                "total": coverage.total,
                "missing_count": 0,
                "stale_count": 0,
                "cache_dir": str(coverage.cache_dir),
            },
        )

    status = _response_status(missing_count=missing_count, stale_count=stale_count)
    expensive = _is_f5(config, purpose="response_cache")
    reason = _response_reason(missing_count=missing_count, stale_count=stale_count)
    return CacheAdvice(
        key="response_cache",
        title="response cache",
        status=status,
        reason=reason,
        ok=False,
        expensive=expensive,
        warning=_f5_warning(
            "F5 regeneration can be expensive; avoid saymo prepare-responses --force "
            "unless intentionally rebuilding every response."
        )
        if expensive
        else "",
        action="Run saymo prepare-responses to rebuild only missing or stale variants.",
        rerun=f"saymo auto-preflight -p {profile}",
        metadata={
            "ready": coverage.ready,
            "total": coverage.total,
            "missing_count": missing_count,
            "stale_count": stale_count,
            "missing_examples": list(coverage.missing),
            "stale_examples": list(coverage.stale),
            "cache_dir": str(coverage.cache_dir),
        },
    )


def _status_from_reason(reason: str) -> str:
    if reason in {"audio_missing", "voice_metadata_missing"}:
        return "missing"
    if reason in {"voice_metadata_stale", "source_metadata_stale"}:
        return "stale"
    return "blocked"


def _response_status(*, missing_count: int, stale_count: int) -> str:
    if missing_count and stale_count:
        return "partial"
    if stale_count:
        return "stale"
    if missing_count:
        return "missing"
    return "partial"


def _response_reason(*, missing_count: int, stale_count: int) -> str:
    parts = []
    if missing_count:
        parts.append(f"missing={missing_count}")
    if stale_count:
        parts.append(f"stale={stale_count}")
    return " ".join(parts) or "partial"


def _is_f5(config, *, purpose: str) -> bool:
    try:
        from saymo.tts.selector import resolve_voice_selector

        return resolve_voice_selector(config, purpose=purpose).selected_engine == "f5tts_clone"
    except Exception:
        return config.tts.engine == "f5tts_clone" or config.tts.realtime_engine == "f5tts_clone"


def _f5_warning(message: str) -> str:
    return message

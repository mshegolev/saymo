"""Optional local diarization contracts and availability diagnostics."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable

from saymo.config import DiarizationConfig


DEFAULT_PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"


@dataclass(frozen=True)
class DiarizationConfigView:
    """Normalized optional diarization settings used by runtime helpers."""

    enabled: bool
    engine: str
    model: str
    device: str
    min_speakers: int
    max_speakers: int
    auth_token_env: str

    @classmethod
    def from_config(cls, config: DiarizationConfig | Any) -> "DiarizationConfigView":
        enabled = bool(getattr(config, "enabled", False))
        raw_engine = str(getattr(config, "engine", "") or "").strip().lower()
        engine = raw_engine or "disabled"
        if not enabled:
            engine = "disabled"
        model = str(getattr(config, "model", "") or "").strip()
        if not model:
            model = DEFAULT_PYANNOTE_MODEL
        device = str(getattr(config, "device", "") or "").strip().lower() or "cpu"
        min_speakers = _safe_int(getattr(config, "min_speakers", 1), 1)
        max_speakers = _safe_int(getattr(config, "max_speakers", min_speakers), min_speakers)
        if min_speakers < 1:
            min_speakers = 1
        if max_speakers < min_speakers:
            max_speakers = min_speakers
        token_env = str(getattr(config, "auth_token_env", "") or "").strip()
        return cls(
            enabled=enabled,
            engine=engine,
            model=model,
            device=device,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            auth_token_env=token_env,
        )


@dataclass(frozen=True)
class DiarizationAvailability:
    """Result of checking whether the configured backend can run locally."""

    engine: str
    available: bool
    status: str
    reason: str
    model: str
    device: str
    token_env: str = ""
    token_available: bool = False
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiarizationSegment:
    """One backend-neutral speaker segment."""

    speaker_id: str
    start_seconds: float
    end_seconds: float
    confidence: float = 0.0


@dataclass(frozen=True)
class DiarizationResult:
    """A backend-neutral diarization result for one capture session."""

    profile: str
    session_id: str
    engine: str
    model: str
    created_at: str
    segments: tuple[DiarizationSegment, ...]


def check_diarization_availability(
    config: DiarizationConfig | Any,
    *,
    import_checker: Callable[[str], bool] | None = None,
) -> DiarizationAvailability:
    """Return local availability diagnostics for the configured backend."""
    view = DiarizationConfigView.from_config(config)
    if view.engine == "disabled":
        return DiarizationAvailability(
            engine="disabled",
            available=False,
            status="disabled",
            reason="diarization is disabled",
            model=view.model,
            device=view.device,
            token_env=view.auth_token_env,
            token_available=False,
        )

    if view.engine != "pyannote":
        return DiarizationAvailability(
            engine=view.engine,
            available=False,
            status="unsupported_engine",
            reason=f"unsupported diarization engine: {view.engine}",
            model=view.model,
            device=view.device,
            missing=(view.engine,),
        )

    token_available = bool(view.auth_token_env and os.environ.get(view.auth_token_env))
    if not view.auth_token_env or not token_available:
        return DiarizationAvailability(
            engine=view.engine,
            available=False,
            status="missing_token",
            reason=(
                "pyannote requires a token env var"
                if view.auth_token_env
                else "pyannote token env var is not configured"
            ),
            model=view.model,
            device=view.device,
            token_env=view.auth_token_env,
            token_available=False,
            missing=("token",),
        )

    checker = import_checker or _module_available
    if not checker("pyannote.audio"):
        return DiarizationAvailability(
            engine=view.engine,
            available=False,
            status="missing_dependency",
            reason="install optional pyannote.audio backend before diarization",
            model=view.model,
            device=view.device,
            token_env=view.auth_token_env,
            token_available=True,
            missing=("pyannote.audio",),
        )

    return DiarizationAvailability(
        engine=view.engine,
        available=True,
        status="ready",
        reason="diarization backend is available",
        model=view.model,
        device=view.device,
        token_env=view.auth_token_env,
        token_available=True,
    )


def diarization_result_to_json(result: DiarizationResult) -> dict[str, Any]:
    """Serialize a diarization result to JSON-compatible primitives."""
    data = asdict(result)
    data["segments"] = [asdict(segment) for segment in result.segments]
    return data


def diarization_result_from_json(data: dict[str, Any]) -> DiarizationResult:
    """Load a diarization result from JSON-compatible primitives."""
    segments = tuple(
        DiarizationSegment(
            speaker_id=str(item.get("speaker_id", "") or "SPEAKER_UNKNOWN"),
            start_seconds=max(0.0, float(item.get("start_seconds", 0.0) or 0.0)),
            end_seconds=max(0.0, float(item.get("end_seconds", 0.0) or 0.0)),
            confidence=_clamp_confidence(item.get("confidence", 0.0)),
        )
        for item in data.get("segments", ())
        if isinstance(item, dict)
    )
    return DiarizationResult(
        profile=str(data.get("profile", "") or ""),
        session_id=str(data.get("session_id", "") or ""),
        engine=str(data.get("engine", "") or ""),
        model=str(data.get("model", "") or ""),
        created_at=str(data.get("created_at", "") or ""),
        segments=segments,
    )


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))

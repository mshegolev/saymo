"""Optional local diarization contracts and availability diagnostics."""

from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from saymo.config import DiarizationConfig


DEFAULT_PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"
SPEAKER_LABELS = ("me", "other", "unknown")
SPEAKER_SUGGESTION_STATUSES = (
    "suggested",
    "accepted",
    "rejected",
    "overridden",
)


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


@dataclass(frozen=True)
class TriggerSampleSpeakerSuggestion:
    """Reviewable speaker suggestion for one trigger sample."""

    sample_path: str
    session_sequence: int
    current_speaker: str
    speaker_id: str
    suggested_speaker: str
    confidence: float
    overlap_seconds: float
    status: str = "suggested"
    reviewed_speaker: str = "unknown"
    reviewed_at: str = ""


@dataclass(frozen=True)
class DiarizationSessionSidecar:
    """Persisted diarization sidecar for one trigger-capture session."""

    profile: str
    session_id: str
    engine: str
    model: str
    created_at: str
    segments: tuple[DiarizationSegment, ...]
    speaker_mappings: dict[str, str]
    suggestions: tuple[TriggerSampleSpeakerSuggestion, ...]


@dataclass(frozen=True)
class SpeakerClusterSummary:
    """Aggregate display data for one diarization speaker id."""

    speaker_id: str
    segment_count: int
    sample_count: int
    start_seconds: float
    end_seconds: float
    confidence: float
    mapped_label: str


@dataclass(frozen=True)
class SpeakerQualityConflict:
    """One manual-vs-suggested speaker-label conflict."""

    sample_name: str
    speaker_id: str
    current_speaker: str
    suggested_speaker: str
    status: str


@dataclass(frozen=True)
class SpeakerQualityReport:
    """Sanitized speaker-suggestion quality report for one session."""

    profile: str
    session_id: str
    total_suggestions: int
    unknown_speaker_labels: int
    unknown_speaker_ratio: float
    accepted_suggestions: int
    rejected_suggestions: int
    overridden_suggestions: int
    pending_suggestions: int
    confidence_buckets: dict[str, int]
    conflicts: tuple[SpeakerQualityConflict, ...]


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


def session_diarization_path(base_dir: Path, profile: str, session_id: str) -> Path:
    """Return the local diarization sidecar path for a session."""
    return (
        Path(base_dir).expanduser()
        / profile
        / "_sessions"
        / f"{session_id}.diarization.json"
    )


def build_session_speaker_suggestions(
    samples: list[Any],
    segments: tuple[DiarizationSegment, ...],
    *,
    window_seconds: float = 8.0,
    speaker_mappings: dict[str, str] | None = None,
) -> tuple[TriggerSampleSpeakerSuggestion, ...]:
    """Match diarization segments to sample windows by maximum overlap."""
    mappings = speaker_mappings or {}
    suggestions: list[TriggerSampleSpeakerSuggestion] = []
    window = max(0.1, float(window_seconds or 8.0))
    for sample in samples:
        sequence = _safe_int(getattr(sample, "session_sequence", 0), 0)
        if sequence <= 0:
            continue
        sample_start = (sequence - 1) * window
        sample_end = sample_start + window
        best_segment: DiarizationSegment | None = None
        best_overlap = 0.0
        for segment in segments:
            overlap = _overlap_seconds(
                sample_start,
                sample_end,
                segment.start_seconds,
                segment.end_seconds,
            )
            if overlap > best_overlap:
                best_segment = segment
                best_overlap = overlap
        if best_segment is None or best_overlap <= 0:
            continue
        current_speaker = _normalize_speaker(getattr(sample, "speaker", "unknown"))
        suggested = _normalize_speaker(mappings.get(best_segment.speaker_id, "unknown"))
        suggestions.append(
            TriggerSampleSpeakerSuggestion(
                sample_path=str(getattr(sample, "path", "")),
                session_sequence=sequence,
                current_speaker=current_speaker,
                speaker_id=best_segment.speaker_id,
                suggested_speaker=suggested,
                confidence=best_segment.confidence,
                overlap_seconds=round(best_overlap, 3),
                status="suggested",
            )
        )
    return tuple(suggestions)


def write_session_diarization(
    base_dir: Path,
    sidecar: DiarizationSessionSidecar,
) -> Path:
    """Write a session diarization sidecar JSON file."""
    path = session_diarization_path(base_dir, sidecar.profile, sidecar.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_sidecar_to_json(sidecar), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_session_diarization(path: Path) -> DiarizationSessionSidecar:
    """Load a session diarization sidecar."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
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
    suggestions = tuple(
        TriggerSampleSpeakerSuggestion(
            sample_path=str(item.get("sample_path", "") or ""),
            session_sequence=_safe_int(item.get("session_sequence", 0), 0),
            current_speaker=_normalize_speaker(item.get("current_speaker")),
            speaker_id=str(item.get("speaker_id", "") or ""),
            suggested_speaker=_normalize_speaker(item.get("suggested_speaker")),
            confidence=_clamp_confidence(item.get("confidence", 0.0)),
            overlap_seconds=max(0.0, float(item.get("overlap_seconds", 0.0) or 0.0)),
            status=_normalize_suggestion_status(item.get("status")),
            reviewed_speaker=_normalize_speaker(item.get("reviewed_speaker")),
            reviewed_at=str(item.get("reviewed_at", "") or ""),
        )
        for item in data.get("suggestions", ())
        if isinstance(item, dict)
    )
    mappings = {
        str(key): _normalize_speaker(value)
        for key, value in (data.get("speaker_mappings") or {}).items()
    }
    return DiarizationSessionSidecar(
        profile=str(data.get("profile", "") or ""),
        session_id=str(data.get("session_id", "") or ""),
        engine=str(data.get("engine", "") or ""),
        model=str(data.get("model", "") or ""),
        created_at=str(data.get("created_at", "") or ""),
        segments=segments,
        speaker_mappings=mappings,
        suggestions=suggestions,
    )


def apply_speaker_mapping(
    sidecar: DiarizationSessionSidecar,
    speaker_id: str,
    label: str,
) -> DiarizationSessionSidecar:
    """Return a sidecar with a speaker-id mapping applied to suggestions."""
    normalized = _normalize_speaker(label)
    mappings = dict(sidecar.speaker_mappings)
    mappings[speaker_id] = normalized
    suggestions = tuple(
        TriggerSampleSpeakerSuggestion(
            sample_path=item.sample_path,
            session_sequence=item.session_sequence,
            current_speaker=item.current_speaker,
            speaker_id=item.speaker_id,
            suggested_speaker=normalized if item.speaker_id == speaker_id else item.suggested_speaker,
            confidence=item.confidence,
            overlap_seconds=item.overlap_seconds,
            status=item.status,
            reviewed_speaker=item.reviewed_speaker,
            reviewed_at=item.reviewed_at,
        )
        for item in sidecar.suggestions
    )
    return DiarizationSessionSidecar(
        profile=sidecar.profile,
        session_id=sidecar.session_id,
        engine=sidecar.engine,
        model=sidecar.model,
        created_at=sidecar.created_at,
        segments=sidecar.segments,
        speaker_mappings=mappings,
        suggestions=suggestions,
    )


def speaker_cluster_summary(
    sidecar: DiarizationSessionSidecar,
) -> dict[str, SpeakerClusterSummary]:
    """Return cluster summaries keyed by diarization speaker id."""
    speaker_ids = sorted({segment.speaker_id for segment in sidecar.segments})
    summaries: dict[str, SpeakerClusterSummary] = {}
    for speaker_id in speaker_ids:
        segments = [segment for segment in sidecar.segments if segment.speaker_id == speaker_id]
        suggestions = [
            suggestion
            for suggestion in sidecar.suggestions
            if suggestion.speaker_id == speaker_id
        ]
        confidence = (
            sum(segment.confidence for segment in segments) / len(segments)
            if segments
            else 0.0
        )
        summaries[speaker_id] = SpeakerClusterSummary(
            speaker_id=speaker_id,
            segment_count=len(segments),
            sample_count=len(suggestions),
            start_seconds=min((segment.start_seconds for segment in segments), default=0.0),
            end_seconds=max((segment.end_seconds for segment in segments), default=0.0),
            confidence=round(confidence, 3),
            mapped_label=sidecar.speaker_mappings.get(speaker_id, "unknown"),
        )
    return summaries


def find_sample_speaker_suggestion(
    sidecar: DiarizationSessionSidecar,
    sample_path: str | Path,
    *,
    session_sequence: int = 0,
) -> TriggerSampleSpeakerSuggestion | None:
    """Find the sidecar suggestion for a sample path.

    Matching tolerates category moves after diarization by falling back to the
    session sequence plus filename when an exact path match is not available.
    """
    path = Path(sample_path)
    exact = str(path)
    expanded = str(path.expanduser())
    name = path.name
    for suggestion in sidecar.suggestions:
        suggestion_path = Path(suggestion.sample_path)
        if suggestion.sample_path in {exact, expanded}:
            return suggestion
        if str(suggestion_path) in {exact, expanded}:
            return suggestion
        if (
            session_sequence
            and suggestion.session_sequence == session_sequence
            and suggestion_path.name == name
        ):
            return suggestion
    return None


def review_speaker_suggestion(
    sidecar: DiarizationSessionSidecar,
    *,
    sample_path: str | Path,
    action: str,
    label: str | None = None,
    session_sequence: int = 0,
    reviewed_at: str = "",
) -> tuple[DiarizationSessionSidecar, TriggerSampleSpeakerSuggestion]:
    """Return a sidecar with one suggestion reviewed.

    Accepted and overridden labels are stored separately from the original
    suggested label so audit/reporting can still compare them later.
    """
    suggestion = find_sample_speaker_suggestion(
        sidecar,
        sample_path,
        session_sequence=session_sequence,
    )
    if suggestion is None:
        raise ValueError(f"Speaker suggestion not found for sample: {sample_path}")

    normalized_action = str(action or "").strip().lower()
    if normalized_action == "accept":
        if suggestion.suggested_speaker == "unknown":
            raise ValueError("Cannot accept an unknown speaker suggestion; use --label")
        status = "accepted"
        reviewed_speaker = suggestion.suggested_speaker
    elif normalized_action == "reject":
        status = "rejected"
        reviewed_speaker = "unknown"
    elif normalized_action == "override":
        status = "overridden"
        reviewed_speaker = _require_speaker_label(label)
    else:
        raise ValueError("action must be accept, reject, or override")

    reviewed = TriggerSampleSpeakerSuggestion(
        sample_path=suggestion.sample_path,
        session_sequence=suggestion.session_sequence,
        current_speaker=suggestion.current_speaker,
        speaker_id=suggestion.speaker_id,
        suggested_speaker=suggestion.suggested_speaker,
        confidence=suggestion.confidence,
        overlap_seconds=suggestion.overlap_seconds,
        status=status,
        reviewed_speaker=reviewed_speaker,
        reviewed_at=reviewed_at,
    )
    suggestions = tuple(
        reviewed
        if _same_sample_suggestion(
            item,
            sample_path,
            session_sequence=session_sequence,
        )
        else item
        for item in sidecar.suggestions
    )
    return (
        DiarizationSessionSidecar(
            profile=sidecar.profile,
            session_id=sidecar.session_id,
            engine=sidecar.engine,
            model=sidecar.model,
            created_at=sidecar.created_at,
            segments=sidecar.segments,
            speaker_mappings=dict(sidecar.speaker_mappings),
            suggestions=suggestions,
        ),
        reviewed,
    )


def build_speaker_quality_report(
    sidecar: DiarizationSessionSidecar,
    *,
    sample_speakers: Mapping[str, str] | None = None,
) -> SpeakerQualityReport:
    """Build sanitized quality metrics for one session sidecar."""
    speaker_lookup = _normalized_sample_speaker_lookup(sample_speakers or {})
    total = len(sidecar.suggestions)
    status_counts = {status: 0 for status in SPEAKER_SUGGESTION_STATUSES}
    buckets = {"high": 0, "medium": 0, "low": 0}
    unknown = 0
    conflicts: list[SpeakerQualityConflict] = []

    for suggestion in sidecar.suggestions:
        status = _normalize_suggestion_status(suggestion.status)
        status_counts[status] += 1
        bucket = _confidence_bucket(suggestion.confidence)
        buckets[bucket] += 1
        current = _current_sample_speaker(suggestion, speaker_lookup)
        if current == "unknown":
            unknown += 1
        suggested = suggestion.suggested_speaker
        if current != "unknown" and suggested != "unknown" and current != suggested:
            conflicts.append(
                SpeakerQualityConflict(
                    sample_name=Path(suggestion.sample_path).name,
                    speaker_id=suggestion.speaker_id,
                    current_speaker=current,
                    suggested_speaker=suggested,
                    status=status,
                )
            )

    return SpeakerQualityReport(
        profile=sidecar.profile,
        session_id=sidecar.session_id,
        total_suggestions=total,
        unknown_speaker_labels=unknown,
        unknown_speaker_ratio=unknown / total if total else 0.0,
        accepted_suggestions=status_counts["accepted"],
        rejected_suggestions=status_counts["rejected"],
        overridden_suggestions=status_counts["overridden"],
        pending_suggestions=status_counts["suggested"],
        confidence_buckets=buckets,
        conflicts=tuple(conflicts),
    )


def render_speaker_quality_report(report: SpeakerQualityReport) -> str:
    """Render a sanitized markdown speaker quality report."""
    lines = [
        "# Saymo Speaker Quality Report",
        "",
        f"profile: {report.profile}",
        f"session: {report.session_id}",
        f"suggestions: {report.total_suggestions}",
        (
            "unknown coverage: "
            f"{report.unknown_speaker_labels}/{report.total_suggestions} "
            f"({report.unknown_speaker_ratio:.0%})"
        ),
        f"accepted suggestions: {report.accepted_suggestions}",
        f"rejected suggestions: {report.rejected_suggestions}",
        f"overridden suggestions: {report.overridden_suggestions}",
        f"pending suggestions: {report.pending_suggestions}",
        f"confidence high: {report.confidence_buckets.get('high', 0)}",
        f"confidence medium: {report.confidence_buckets.get('medium', 0)}",
        f"confidence low: {report.confidence_buckets.get('low', 0)}",
        f"manual conflicts: {len(report.conflicts)}",
    ]
    if report.conflicts:
        lines.extend(["", "## Conflicts"])
        for conflict in report.conflicts:
            lines.append(
                "- "
                f"{conflict.sample_name}: "
                f"manual={conflict.current_speaker} "
                f"suggested={conflict.suggested_speaker} "
                f"speaker_id={conflict.speaker_id} "
                f"status={conflict.status}"
            )
    return "\n".join(lines) + "\n"


def run_pyannote_diarization(
    *,
    audio_path: Path,
    config: DiarizationConfig | Any,
    profile: str,
    session_id: str,
    created_at: str,
) -> DiarizationResult:
    """Run the optional pyannote backend for one audio file."""
    view = DiarizationConfigView.from_config(config)
    status = check_diarization_availability(config)
    if not status.available:
        raise RuntimeError(status.reason)

    from pyannote.audio import Pipeline  # type: ignore

    token = os.environ.get(view.auth_token_env) if view.auth_token_env else None
    pipeline = Pipeline.from_pretrained(view.model, use_auth_token=token)
    if view.device and view.device != "cpu" and hasattr(pipeline, "to"):
        try:
            import torch

            pipeline.to(torch.device(view.device))
        except Exception:
            pass
    diarization = pipeline(
        str(audio_path),
        min_speakers=view.min_speakers,
        max_speakers=view.max_speakers,
    )
    segments: list[DiarizationSegment] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            DiarizationSegment(
                speaker_id=str(speaker),
                start_seconds=float(turn.start),
                end_seconds=float(turn.end),
                confidence=0.0,
            )
        )
    return DiarizationResult(
        profile=profile,
        session_id=session_id,
        engine=view.engine,
        model=view.model,
        created_at=created_at,
        segments=tuple(segments),
    )


def _sidecar_to_json(sidecar: DiarizationSessionSidecar) -> dict[str, Any]:
    return {
        "profile": sidecar.profile,
        "session_id": sidecar.session_id,
        "engine": sidecar.engine,
        "model": sidecar.model,
        "created_at": sidecar.created_at,
        "segments": [asdict(segment) for segment in sidecar.segments],
        "speaker_mappings": dict(sidecar.speaker_mappings),
        "suggestions": [asdict(suggestion) for suggestion in sidecar.suggestions],
    }


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


def _normalize_speaker(value: Any) -> str:
    label = str(value or "").strip().lower()
    return label if label in SPEAKER_LABELS else "unknown"


def _require_speaker_label(value: Any) -> str:
    label = str(value or "").strip().lower()
    if label not in SPEAKER_LABELS:
        allowed = ", ".join(SPEAKER_LABELS)
        raise ValueError(f"speaker label must be one of: {allowed}")
    return label


def _normalize_suggestion_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status in SPEAKER_SUGGESTION_STATUSES:
        return status
    return "suggested"


def _same_sample_suggestion(
    suggestion: TriggerSampleSpeakerSuggestion,
    sample_path: str | Path,
    *,
    session_sequence: int = 0,
) -> bool:
    path = Path(sample_path)
    suggestion_path = Path(suggestion.sample_path)
    if suggestion.sample_path == str(path):
        return True
    if str(suggestion_path) == str(path.expanduser()):
        return True
    return (
        bool(session_sequence)
        and suggestion.session_sequence == session_sequence
        and suggestion_path.name == path.name
    )


def _normalized_sample_speaker_lookup(
    sample_speakers: Mapping[str, str],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for raw_path, speaker in sample_speakers.items():
        normalized = _normalize_speaker(speaker)
        text = str(raw_path)
        lookup[text] = normalized
        lookup[str(Path(text).expanduser())] = normalized
        lookup[Path(text).name] = normalized
    return lookup


def _current_sample_speaker(
    suggestion: TriggerSampleSpeakerSuggestion,
    sample_speakers: Mapping[str, str],
) -> str:
    path = Path(suggestion.sample_path)
    for key in (
        suggestion.sample_path,
        str(path),
        str(path.expanduser()),
        path.name,
    ):
        if key in sample_speakers:
            return _normalize_speaker(sample_speakers[key])
    return suggestion.current_speaker


def _confidence_bucket(confidence: float) -> str:
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.5:
        return "medium"
    return "low"


def _overlap_seconds(
    start_a: float,
    end_a: float,
    start_b: float,
    end_b: float,
) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))

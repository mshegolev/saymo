"""Local full-session meeting memory ledgers and retrieval helpers."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from saymo.analysis.trigger_sessions import SESSION_LEDGER_DIR, TriggerSession


MEMORY_LEDGER_SUFFIX = ".transcript.json"
_SPEAKER_LABELS = {"me", "other", "unknown"}


@dataclass(frozen=True)
class TranscriptSegment:
    """One chronological transcript segment in a local meeting ledger."""

    sequence: int
    start_seconds: float
    end_seconds: float
    created_at: str
    transcript: str
    category: str = "unknown"
    speaker: str = "unknown"
    confidence: float = 0.0
    source_window: str = ""
    trigger: bool = False
    question: bool = False
    will_answer: bool = False
    addressing: str = ""
    reason: str = ""


@dataclass(frozen=True)
class MeetingMemoryLedger:
    """Persisted local transcript memory for one captured meeting session."""

    profile: str
    session_id: str
    session_name: str = ""
    created_at: str = ""
    updated_at: str = ""
    retain_transcripts: bool = True
    source_sample_count: int = 0
    incomplete_segments: int = 0
    window_seconds: float = 8.0
    segments: tuple[TranscriptSegment, ...] = field(default_factory=tuple)
    path: Path | None = None


@dataclass(frozen=True)
class MeetingMemorySummary:
    """Concise summary data derived from a meeting-memory ledger."""

    profile: str
    session_id: str
    session_name: str
    total_segments: int
    transcript_segments: int
    incomplete_segments: int
    categories: dict[str, int]
    speakers: dict[str, int]
    questions: tuple[TranscriptSegment, ...]
    handoffs: tuple[TranscriptSegment, ...]
    action_items: tuple[TranscriptSegment, ...]


@dataclass(frozen=True)
class MeetingSearchFilters:
    """Filters for local meeting-memory search."""

    profile: str | None = None
    session_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    speaker: str | None = None
    category: str | None = None
    keyword: str | None = None


@dataclass(frozen=True)
class MeetingSearchResult:
    """One cited meeting-memory search hit."""

    profile: str
    session_id: str
    session_name: str
    sequence: int
    start_seconds: float
    end_seconds: float
    speaker: str
    category: str
    created_at: str
    transcript: str
    citation: str
    score: float


@dataclass(frozen=True)
class MeetingAskAnswer:
    """Deterministic answer to a question with transcript citations."""

    question: str
    answer: str
    citations: tuple[MeetingSearchResult, ...]
    insufficient_evidence: bool = False


def meeting_memory_base_dir(config=None, samples_dir: str | None = None) -> Path:
    """Resolve the base directory for local meeting memory/session files."""
    if samples_dir:
        return Path(samples_dir).expanduser()
    memory = getattr(config, "meeting_memory", None)
    configured = str(getattr(memory, "base_dir", "") or "")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".saymo" / "trigger_samples"


def meeting_transcript_path(base_dir: Path, profile: str, session_id: str) -> Path:
    """Return the transcript ledger path for one profile/session."""
    return (
        Path(base_dir).expanduser()
        / profile
        / SESSION_LEDGER_DIR
        / f"{session_id}{MEMORY_LEDGER_SUFFIX}"
    )


def write_meeting_ledger(base_dir: Path, ledger: MeetingMemoryLedger) -> Path:
    """Write a meeting-memory transcript ledger JSON sidecar."""
    path = ledger.path or meeting_transcript_path(base_dir, ledger.profile, ledger.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "profile": ledger.profile,
        "session_id": ledger.session_id,
        "session_name": ledger.session_name,
        "created_at": ledger.created_at,
        "updated_at": ledger.updated_at,
        "retain_transcripts": ledger.retain_transcripts,
        "source_sample_count": ledger.source_sample_count,
        "incomplete_segments": ledger.incomplete_segments,
        "window_seconds": ledger.window_seconds,
        "segments": [asdict(segment) for segment in ledger.segments],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_meeting_ledger(path: Path) -> MeetingMemoryLedger:
    """Load a meeting-memory transcript ledger JSON sidecar."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    segments = tuple(
        TranscriptSegment(
            sequence=_safe_int(item.get("sequence"), 0),
            start_seconds=_safe_float(item.get("start_seconds"), 0.0),
            end_seconds=_safe_float(item.get("end_seconds"), 0.0),
            created_at=str(item.get("created_at") or ""),
            transcript=str(item.get("transcript") or ""),
            category=str(item.get("category") or "unknown"),
            speaker=_normalize_speaker(item.get("speaker")),
            confidence=_clamp01(item.get("confidence")),
            source_window=str(item.get("source_window") or ""),
            trigger=bool(item.get("trigger")),
            question=bool(item.get("question")),
            will_answer=bool(item.get("will_answer")),
            addressing=str(item.get("addressing") or ""),
            reason=str(item.get("reason") or ""),
        )
        for item in data.get("segments", [])
        if isinstance(item, dict)
    )
    return MeetingMemoryLedger(
        profile=str(data.get("profile") or _profile_from_memory_path(path)),
        session_id=str(data.get("session_id") or _session_id_from_memory_path(path)),
        session_name=str(data.get("session_name") or ""),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or ""),
        retain_transcripts=bool(data.get("retain_transcripts", True)),
        source_sample_count=_safe_int(data.get("source_sample_count"), len(segments)),
        incomplete_segments=_safe_int(
            data.get("incomplete_segments"),
            sum(1 for segment in segments if not segment.transcript),
        ),
        window_seconds=_safe_float(data.get("window_seconds"), 8.0),
        segments=segments,
        path=Path(path),
    )


def list_meeting_ledgers(
    base_dir: Path,
    *,
    profile: str | None = None,
) -> tuple[MeetingMemoryLedger, ...]:
    """Load local meeting-memory ledgers, newest first."""
    root = Path(base_dir).expanduser()
    if profile:
        paths = sorted((root / profile / SESSION_LEDGER_DIR).glob(f"*{MEMORY_LEDGER_SUFFIX}"))
    else:
        paths = sorted(root.glob(f"*/{SESSION_LEDGER_DIR}/*{MEMORY_LEDGER_SUFFIX}"))
    ledgers: list[MeetingMemoryLedger] = []
    for path in paths:
        try:
            ledgers.append(load_meeting_ledger(path))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return tuple(sorted(ledgers, key=lambda item: (item.updated_at, item.session_id), reverse=True))


def build_meeting_ledger_from_samples(
    *,
    base_dir: Path,
    profile: str,
    session_id: str,
    session: TriggerSession | None = None,
    window_seconds: float = 8.0,
    retain_transcripts: bool = True,
    updated_at: str | None = None,
) -> MeetingMemoryLedger:
    """Build a transcript ledger from trigger-capture sample metadata."""
    records = list(iter_session_sample_windows(base_dir, profile, session_id))
    now = updated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    session_name = session.session_name if session else ""
    created_at = session.started_at if session else now
    segments: list[TranscriptSegment] = []
    for index, record in enumerate(records, start=1):
        sequence = _safe_int(record.data.get("session_sequence"), index)
        start_seconds = max(0.0, (sequence - 1) * window_seconds)
        transcript = str(record.data.get("transcript") or "")
        confidence = _segment_confidence(record.data)
        segments.append(
            TranscriptSegment(
                sequence=sequence,
                start_seconds=start_seconds,
                end_seconds=start_seconds + window_seconds,
                created_at=str(record.data.get("created_at") or ""),
                transcript=transcript if retain_transcripts else "",
                category=str(record.data.get("category") or record.path.parent.name),
                speaker=_normalize_speaker(record.data.get("speaker")),
                confidence=confidence,
                source_window=_relative_source_window(base_dir, record.path),
                trigger=bool(record.data.get("trigger")),
                question=bool(record.data.get("question")),
                will_answer=bool(record.data.get("will_answer")),
                addressing=str(record.data.get("addressing") or ""),
                reason=str(record.data.get("reason") or ""),
            )
        )
    segments = sorted(segments, key=lambda item: (item.sequence, item.created_at))
    incomplete = sum(1 for segment in segments if not segment.transcript)
    return MeetingMemoryLedger(
        profile=profile,
        session_id=session_id,
        session_name=session_name or session_id,
        created_at=created_at,
        updated_at=now,
        retain_transcripts=retain_transcripts,
        source_sample_count=len(records),
        incomplete_segments=incomplete,
        window_seconds=window_seconds,
        segments=tuple(segments),
        path=meeting_transcript_path(base_dir, profile, session_id),
    )


@dataclass(frozen=True)
class SessionSampleWindow:
    """Loaded trigger sample metadata plus its local JSON path."""

    path: Path
    data: dict[str, Any]


def iter_session_sample_windows(
    base_dir: Path,
    profile: str,
    session_id: str,
) -> tuple[SessionSampleWindow, ...]:
    """Return sample metadata windows for one profile/session."""
    root = Path(base_dir).expanduser() / profile
    records: list[SessionSampleWindow] = []
    for path in sorted(root.glob("*/*.json")):
        if path.parent.name == SESSION_LEDGER_DIR:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict) or data.get("session_id") != session_id:
            continue
        records.append(SessionSampleWindow(path=path, data=data))
    return tuple(
        sorted(
            records,
            key=lambda item: (
                _safe_int(item.data.get("session_sequence"), 0),
                str(item.data.get("created_at") or ""),
                str(item.path),
            ),
        )
    )


def summarize_meeting_ledger(
    ledger: MeetingMemoryLedger,
    *,
    max_items: int = 5,
) -> MeetingMemorySummary:
    """Build concise summary data for one meeting-memory ledger."""
    categories = Counter(segment.category or "unknown" for segment in ledger.segments)
    speakers = Counter(_normalize_speaker(segment.speaker) for segment in ledger.segments)
    questions = [
        segment
        for segment in ledger.segments
        if segment.question or _looks_like_question(segment.transcript)
    ]
    handoffs = [
        segment
        for segment in ledger.segments
        if segment.will_answer or segment.category == "asked_to_speak"
    ]
    action_items = [
        segment
        for segment in ledger.segments
        if _looks_like_action_item(segment.transcript)
    ]
    return MeetingMemorySummary(
        profile=ledger.profile,
        session_id=ledger.session_id,
        session_name=ledger.session_name,
        total_segments=len(ledger.segments),
        transcript_segments=sum(1 for segment in ledger.segments if segment.transcript),
        incomplete_segments=sum(1 for segment in ledger.segments if not segment.transcript),
        categories=dict(sorted(categories.items())),
        speakers=dict(sorted(speakers.items())),
        questions=tuple(questions[:max_items]),
        handoffs=tuple(handoffs[:max_items]),
        action_items=tuple(action_items[:max_items]),
    )


def render_meeting_summary(summary: MeetingMemorySummary, *, include_text: bool = True) -> str:
    """Render a concise local markdown summary for one meeting session."""
    lines = [
        f"# Meeting Summary: {summary.session_id}",
        "",
        f"- profile: {summary.profile}",
        f"- name: {summary.session_name}",
        f"- segments: {summary.total_segments}",
        f"- transcript segments: {summary.transcript_segments}",
        f"- incomplete coverage: {summary.incomplete_segments}",
        f"- categories: {_format_counts(summary.categories)}",
        f"- speakers: {_format_counts(summary.speakers)}",
        "",
        "## Questions",
    ]
    lines.extend(_render_segment_list(summary.questions, include_text=include_text))
    lines.append("")
    lines.append("## Handoffs")
    lines.extend(_render_segment_list(summary.handoffs, include_text=include_text))
    lines.append("")
    lines.append("## Action Items")
    lines.extend(_render_segment_list(summary.action_items, include_text=include_text))
    return "\n".join(lines).rstrip() + "\n"


def search_meeting_memory(
    base_dir: Path,
    filters: MeetingSearchFilters,
    *,
    limit: int = 20,
) -> tuple[MeetingSearchResult, ...]:
    """Search local meeting-memory ledgers with simple deterministic filters."""
    terms = _keyword_terms(filters.keyword or "")
    results: list[MeetingSearchResult] = []
    for ledger in list_meeting_ledgers(base_dir, profile=filters.profile):
        if filters.session_id and not (
            ledger.session_id == filters.session_id
            or ledger.session_id.startswith(filters.session_id)
        ):
            continue
        for segment in ledger.segments:
            if filters.date_from and segment.created_at and segment.created_at < filters.date_from:
                continue
            if filters.date_to and segment.created_at and segment.created_at > filters.date_to:
                continue
            if filters.speaker and segment.speaker != filters.speaker:
                continue
            if filters.category and segment.category != filters.category:
                continue
            text = segment.transcript or ""
            if terms and not _segment_matches_terms(segment, terms):
                continue
            score = _segment_score(segment, terms)
            results.append(
                MeetingSearchResult(
                    profile=ledger.profile,
                    session_id=ledger.session_id,
                    session_name=ledger.session_name,
                    sequence=segment.sequence,
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    speaker=segment.speaker,
                    category=segment.category,
                    created_at=segment.created_at,
                    transcript=text,
                    citation=_citation(ledger.session_id, segment),
                    score=score,
                )
            )
    results.sort(key=lambda item: (-item.score, item.created_at, item.session_id, item.sequence))
    return tuple(results[: max(0, limit)])


def answer_meeting_question(
    question: str,
    *,
    base_dir: Path,
    filters: MeetingSearchFilters,
    max_citations: int = 5,
) -> MeetingAskAnswer:
    """Answer a meeting question with cited local transcript evidence."""
    terms = _keyword_terms(question)
    query = " ".join(terms) or question
    results = search_meeting_memory(
        base_dir,
        MeetingSearchFilters(
            profile=filters.profile,
            session_id=filters.session_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            speaker=filters.speaker,
            category=filters.category,
            keyword=query,
        ),
        limit=max_citations,
    )
    if not results and terms:
        # Fall back to question/handoff windows from the selected scope.
        fallback = []
        for result in search_meeting_memory(
            base_dir,
            MeetingSearchFilters(
                profile=filters.profile,
                session_id=filters.session_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                speaker=filters.speaker,
            ),
            limit=50,
        ):
            if result.category in {"asked_to_speak", "question"}:
                fallback.append(result)
        results = tuple(fallback[:max_citations])
    if not results:
        return MeetingAskAnswer(
            question=question,
            answer="Недостаточно данных в локальной памяти встречи, чтобы ответить с цитатами.",
            citations=(),
            insufficient_evidence=True,
        )
    evidence = "; ".join(
        f"{_clip(result.transcript, 120)} [{result.citation}]"
        for result in results
        if result.transcript
    )
    if not evidence:
        return MeetingAskAnswer(
            question=question,
            answer="Найдены только пустые фрагменты без текста; ответ с цитатами невозможен.",
            citations=results,
            insufficient_evidence=True,
        )
    return MeetingAskAnswer(
        question=question,
        answer=f"По найденным фрагментам: {evidence}",
        citations=results,
        insufficient_evidence=False,
    )


def render_meeting_search_results(results: Iterable[MeetingSearchResult]) -> str:
    """Render search results as grep-friendly text."""
    lines = []
    for result in results:
        lines.append(
            f"{result.citation} profile={result.profile} speaker={result.speaker} "
            f"category={result.category} score={result.score:.2f} "
            f"text={_clip(result.transcript, 180)}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def render_meeting_ask_answer(answer: MeetingAskAnswer) -> str:
    """Render a meeting ask answer and citations."""
    lines = [
        f"question: {answer.question}",
        f"answer: {answer.answer}",
        f"insufficient evidence: {'yes' if answer.insufficient_evidence else 'no'}",
        "citations:",
    ]
    if answer.citations:
        for result in answer.citations:
            lines.append(
                f"- {result.citation} speaker={result.speaker} "
                f"category={result.category} text={_clip(result.transcript, 160)}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def render_sanitized_meeting_export(ledger: MeetingMemoryLedger) -> str:
    """Render a sanitized markdown export for one local meeting session."""
    summary = summarize_meeting_ledger(ledger)
    lines = [
        f"# Sanitized Meeting Export: {ledger.session_id}",
        "",
        f"- profile: {ledger.profile}",
        f"- session name: {ledger.session_name}",
        f"- segments: {summary.total_segments}",
        f"- transcript segments: {summary.transcript_segments}",
        f"- incomplete coverage: {summary.incomplete_segments}",
        f"- categories: {_format_counts(summary.categories)}",
        f"- speakers: {_format_counts(summary.speakers)}",
        "",
        "## Questions",
    ]
    lines.extend(_render_sanitized_segments(ledger.session_id, summary.questions))
    lines.append("")
    lines.append("## Handoffs")
    lines.extend(_render_sanitized_segments(ledger.session_id, summary.handoffs))
    lines.append("")
    lines.append("## Action Items")
    lines.extend(_render_sanitized_segments(ledger.session_id, summary.action_items))
    lines.append("")
    lines.append("## Sanitization")
    lines.append("- raw audio: omitted")
    lines.append("- source sample paths: omitted")
    lines.append("- secrets and config values: omitted")
    return "\n".join(lines).rstrip() + "\n"


def _render_segment_list(
    segments: Iterable[TranscriptSegment],
    *,
    include_text: bool,
) -> list[str]:
    rendered = []
    for segment in segments:
        prefix = (
            f"- [{segment.sequence}] {segment.start_seconds:.1f}-{segment.end_seconds:.1f}s "
            f"speaker={segment.speaker} category={segment.category}"
        )
        if include_text and segment.transcript:
            rendered.append(f"{prefix}: {_clip(segment.transcript, 180)}")
        else:
            rendered.append(prefix)
    return rendered or ["- none"]


def _render_sanitized_segments(
    session_id: str,
    segments: Iterable[TranscriptSegment],
) -> list[str]:
    rendered = []
    for segment in segments:
        rendered.append(
            f"- {_citation(session_id, segment)} "
            f"speaker={segment.speaker} category={segment.category}: "
            f"{_clip(segment.transcript, 160)}"
        )
    return rendered or ["- none"]


def _citation(session_id: str, segment: TranscriptSegment) -> str:
    return (
        f"{session_id}#{segment.sequence}"
        f"@{segment.start_seconds:.1f}-{segment.end_seconds:.1f}s"
    )


def _keyword_terms(text: str) -> tuple[str, ...]:
    raw = re.findall(r"[\wа-яА-ЯёЁ]+", (text or "").lower(), flags=re.UNICODE)
    stop = {
        "и",
        "в",
        "на",
        "по",
        "что",
        "как",
        "это",
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "is",
        "are",
        "you",
        "can",
    }
    return tuple(term for term in raw if len(term) > 2 and term not in stop)


def _segment_matches_terms(segment: TranscriptSegment, terms: tuple[str, ...]) -> bool:
    haystack = " ".join(
        [
            segment.transcript,
            segment.category,
            segment.speaker,
            segment.addressing,
            segment.reason,
        ]
    ).lower()
    return all(term in haystack for term in terms)


def _segment_score(segment: TranscriptSegment, terms: tuple[str, ...]) -> float:
    text = segment.transcript.lower()
    score = segment.confidence
    score += sum(text.count(term) for term in terms)
    if segment.question:
        score += 0.5
    if segment.will_answer or segment.category == "asked_to_speak":
        score += 0.75
    return score


def _format_counts(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in counts.items()) or "none"


def _segment_confidence(data: Mapping[str, Any]) -> float:
    if "confidence" in data:
        return _clamp01(data.get("confidence"))
    transcript = str(data.get("transcript") or "")
    if not transcript:
        return 0.0
    rms = _safe_float(data.get("rms"), 0.0)
    peak = _safe_float(data.get("peak"), 0.0)
    if peak <= 0:
        return 0.5
    return max(0.5, min(0.95, 0.55 + min(0.4, rms * 10)))


def _looks_like_question(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "?",
        "что",
        "как",
        "где",
        "когда",
        "почему",
        "зачем",
        "кто",
        "сколько",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
    )
    return any(marker in lowered for marker in markers)


def _looks_like_action_item(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "надо",
        "нужно",
        "сделать",
        "проверить",
        "подготовить",
        "доделать",
        "заберу",
        "беру",
        "todo",
        "action item",
        "follow up",
    )
    return any(marker in lowered for marker in markers)


def _normalize_speaker(value: Any) -> str:
    speaker = str(value or "").strip().lower()
    return speaker if speaker in _SPEAKER_LABELS else "unknown"


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _clamp01(value: Any) -> float:
    parsed = _safe_float(value, 0.0)
    return max(0.0, min(1.0, parsed))


def _relative_source_window(base_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(Path(base_dir).expanduser()))
    except ValueError:
        return Path(path).name


def _profile_from_memory_path(path: Path) -> str:
    try:
        return Path(path).parents[1].name
    except IndexError:
        return ""


def _session_id_from_memory_path(path: Path) -> str:
    name = Path(path).name
    if name.endswith(MEMORY_LEDGER_SUFFIX):
        return name[: -len(MEMORY_LEDGER_SUFFIX)]
    return Path(path).stem


def _clip(text: str, limit: int) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"

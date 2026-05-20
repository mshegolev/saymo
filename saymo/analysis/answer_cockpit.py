"""Answer draft, cockpit, and audit contracts for live meeting assistance."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from saymo.analysis.meeting_memory import MeetingAskAnswer, MeetingSearchResult


@dataclass(frozen=True)
class TriggerEvidence:
    """Evidence that a transcript window is addressed to the user."""

    transcript: str
    profile: str = ""
    session_id: str = ""
    trigger: bool = False
    question: bool = False
    will_answer: bool = False
    addressing: str = ""
    reason: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class SourceEvidence:
    """Bounded diagnostic view of one configured answer source."""

    name: str
    status: str
    fetched_at: str
    summary: str = ""
    diagnostic: str = ""


@dataclass(frozen=True)
class DraftCitation:
    """Citation copied into an answer draft."""

    citation: str
    transcript: str
    speaker: str
    category: str


@dataclass(frozen=True)
class AnswerDraft:
    """Reviewable draft that is not approved for live speech by itself."""

    draft_id: str
    profile: str
    session_id: str
    question: str
    created_at: str
    trigger_evidence: TriggerEvidence
    citations: tuple[DraftCitation, ...] = field(default_factory=tuple)
    sources: tuple[SourceEvidence, ...] = field(default_factory=tuple)
    draft_text: str = ""
    confidence: float = 0.0
    composer: str = "deterministic"
    action_state: str = "pending"


def build_trigger_evidence(
    *,
    transcript: str,
    profile: str = "",
    session_id: str = "",
    trigger: bool = False,
    question: bool = True,
    will_answer: bool = False,
    addressing: str = "",
    reason: str = "",
    confidence: float | None = None,
) -> TriggerEvidence:
    """Build normalized trigger evidence for a draft."""
    text = " ".join((transcript or "").split())
    inferred_question = question or text.endswith("?") or _has_question_marker(text)
    inferred_confidence = (
        _clamp01(confidence)
        if confidence is not None
        else _trigger_confidence(text=text, trigger=trigger, question=inferred_question, will_answer=will_answer)
    )
    return TriggerEvidence(
        transcript=text,
        profile=profile,
        session_id=session_id,
        trigger=trigger,
        question=inferred_question,
        will_answer=will_answer,
        addressing=addressing,
        reason=reason,
        confidence=inferred_confidence,
    )


def source_evidence_from_payload(
    name: str,
    payload: Mapping[str, Any] | None,
    *,
    fetched_at: str | None = None,
    diagnostic: str = "",
) -> SourceEvidence:
    """Convert a source plugin payload into bounded source evidence."""
    now = fetched_at or _now()
    if payload is None:
        return SourceEvidence(
            name=name,
            status="empty",
            fetched_at=now,
            diagnostic=diagnostic or "source returned no content",
        )
    parts = []
    for key in ("yesterday", "today", "summary", "content"):
        value = payload.get(key)
        if value:
            parts.append(str(value))
    summary = _clip("\n".join(parts), 700)
    if not summary:
        return SourceEvidence(
            name=name,
            status="empty",
            fetched_at=now,
            diagnostic=diagnostic or "source payload had no usable text",
        )
    return SourceEvidence(name=name, status="available", fetched_at=now, summary=summary)


def source_evidence_error(
    name: str,
    error: BaseException | str,
    *,
    fetched_at: str | None = None,
) -> SourceEvidence:
    """Create a source evidence error without exposing secrets."""
    message = str(error)
    message = re.sub(r"([A-Za-z_]*TOKEN[A-Za-z_]*=)[^\s]+", r"\1<redacted>", message)
    return SourceEvidence(
        name=name,
        status="error",
        fetched_at=fetched_at or _now(),
        diagnostic=_clip(message, 240),
    )


def build_answer_draft(
    *,
    profile: str,
    session_id: str,
    question: str,
    trigger_evidence: TriggerEvidence,
    meeting_answer: MeetingAskAnswer,
    sources: Iterable[SourceEvidence] = (),
    composer_text: str | None = None,
    composer: str = "deterministic",
    created_at: str | None = None,
) -> AnswerDraft:
    """Build a reviewable answer draft from meeting and source evidence."""
    created = created_at or _now()
    source_tuple = tuple(sources)
    citations = tuple(_draft_citation(result) for result in meeting_answer.citations)
    draft_text = " ".join((composer_text or "").split())
    if not draft_text:
        draft_text = _deterministic_draft_text(meeting_answer, source_tuple)
        composer = "deterministic"
    confidence = _draft_confidence(
        trigger_evidence=trigger_evidence,
        citation_count=len(citations),
        sources=source_tuple,
        insufficient_evidence=meeting_answer.insufficient_evidence,
    )
    draft_id = _draft_id(profile, session_id, created)
    return AnswerDraft(
        draft_id=draft_id,
        profile=profile,
        session_id=session_id,
        question=question,
        created_at=created,
        trigger_evidence=trigger_evidence,
        citations=citations,
        sources=source_tuple,
        draft_text=draft_text,
        confidence=confidence,
        composer=composer,
        action_state="pending",
    )


def answer_draft_to_json(draft: AnswerDraft) -> dict[str, Any]:
    """Serialize an answer draft to JSON-compatible primitives."""
    return {
        **asdict(draft),
        "citations": [asdict(item) for item in draft.citations],
        "sources": [asdict(item) for item in draft.sources],
        "trigger_evidence": asdict(draft.trigger_evidence),
    }


def answer_draft_from_json(data: Mapping[str, Any]) -> AnswerDraft:
    """Load an answer draft from JSON-compatible primitives."""
    trigger_data = data.get("trigger_evidence") or {}
    return AnswerDraft(
        draft_id=str(data.get("draft_id") or ""),
        profile=str(data.get("profile") or ""),
        session_id=str(data.get("session_id") or ""),
        question=str(data.get("question") or ""),
        created_at=str(data.get("created_at") or ""),
        trigger_evidence=TriggerEvidence(
            transcript=str(trigger_data.get("transcript") or ""),
            profile=str(trigger_data.get("profile") or ""),
            session_id=str(trigger_data.get("session_id") or ""),
            trigger=bool(trigger_data.get("trigger")),
            question=bool(trigger_data.get("question")),
            will_answer=bool(trigger_data.get("will_answer")),
            addressing=str(trigger_data.get("addressing") or ""),
            reason=str(trigger_data.get("reason") or ""),
            confidence=_clamp01(trigger_data.get("confidence")),
        ),
        citations=tuple(
            DraftCitation(
                citation=str(item.get("citation") or ""),
                transcript=str(item.get("transcript") or ""),
                speaker=str(item.get("speaker") or "unknown"),
                category=str(item.get("category") or "unknown"),
            )
            for item in data.get("citations", [])
            if isinstance(item, dict)
        ),
        sources=tuple(
            SourceEvidence(
                name=str(item.get("name") or ""),
                status=str(item.get("status") or "unknown"),
                fetched_at=str(item.get("fetched_at") or ""),
                summary=str(item.get("summary") or ""),
                diagnostic=str(item.get("diagnostic") or ""),
            )
            for item in data.get("sources", [])
            if isinstance(item, dict)
        ),
        draft_text=str(data.get("draft_text") or ""),
        confidence=_clamp01(data.get("confidence")),
        composer=str(data.get("composer") or "deterministic"),
        action_state=str(data.get("action_state") or "pending"),
    )


def write_answer_draft(path: Path, draft: AnswerDraft) -> Path:
    """Write an answer draft JSON file."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(answer_draft_to_json(draft), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def load_answer_draft(path: Path) -> AnswerDraft:
    """Load an answer draft JSON file."""
    return answer_draft_from_json(json.loads(Path(path).read_text(encoding="utf-8")))


def render_answer_draft(draft: AnswerDraft) -> str:
    """Render a reviewable answer draft for CLI/cockpit use."""
    lines = [
        f"draft: {draft.draft_id}",
        f"profile: {draft.profile}",
        f"session: {draft.session_id or '-'}",
        f"composer: {draft.composer}",
        f"confidence: {draft.confidence:.2f}",
        f"state: {draft.action_state}",
        f"question: {draft.question}",
        "trigger:",
        (
            f"- trigger={'yes' if draft.trigger_evidence.trigger else 'no'} "
            f"question={'yes' if draft.trigger_evidence.question else 'no'} "
            f"will_answer={'yes' if draft.trigger_evidence.will_answer else 'no'} "
            f"confidence={draft.trigger_evidence.confidence:.2f} "
            f"addressing={draft.trigger_evidence.addressing or '-'}"
        ),
        "sources:",
    ]
    if draft.sources:
        for source in draft.sources:
            detail = source.diagnostic or _clip(source.summary, 120)
            lines.append(
                f"- {source.name}: {source.status} fetched_at={source.fetched_at} {detail}".rstrip()
            )
    else:
        lines.append("- none")
    lines.append("citations:")
    if draft.citations:
        for citation in draft.citations:
            lines.append(
                f"- {citation.citation} speaker={citation.speaker} "
                f"category={citation.category} text={_clip(citation.transcript, 140)}"
            )
    else:
        lines.append("- none")
    lines.append("draft text:")
    lines.append(draft.draft_text or "(empty)")
    return "\n".join(lines) + "\n"


def _draft_citation(result: MeetingSearchResult) -> DraftCitation:
    return DraftCitation(
        citation=result.citation,
        transcript=result.transcript,
        speaker=result.speaker,
        category=result.category,
    )


def _deterministic_draft_text(
    meeting_answer: MeetingAskAnswer,
    sources: tuple[SourceEvidence, ...],
) -> str:
    if meeting_answer.insufficient_evidence:
        base = "Не уверен, нужно перепроверить по встрече."
    else:
        base = meeting_answer.answer
    available_sources = [source for source in sources if source.status == "available"]
    if available_sources:
        source_bits = "; ".join(
            f"{source.name}: {_clip(source.summary, 120)}" for source in available_sources[:3]
        )
        return f"{base} Дополнительный контекст: {source_bits}"
    return base


def _draft_confidence(
    *,
    trigger_evidence: TriggerEvidence,
    citation_count: int,
    sources: tuple[SourceEvidence, ...],
    insufficient_evidence: bool,
) -> float:
    confidence = 0.2 + trigger_evidence.confidence * 0.35
    confidence += min(0.3, citation_count * 0.08)
    confidence += min(0.2, sum(1 for source in sources if source.status == "available") * 0.06)
    if insufficient_evidence:
        confidence -= 0.25
    return max(0.05, min(0.95, confidence))


def _trigger_confidence(*, text: str, trigger: bool, question: bool, will_answer: bool) -> float:
    confidence = 0.15
    if text:
        confidence += 0.2
    if question:
        confidence += 0.2
    if trigger:
        confidence += 0.2
    if will_answer:
        confidence += 0.2
    return max(0.0, min(0.95, confidence))


def _has_question_marker(text: str) -> bool:
    lowered = text.lower()
    markers = ("?", "что", "как", "почему", "когда", "where", "what", "why", "how", "when")
    return any(marker in lowered for marker in markers)


def _draft_id(profile: str, session_id: str, created_at: str) -> str:
    raw = f"{profile}-{session_id or 'session'}-{created_at}"
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", raw).strip("-._")
    return slug or "draft"


def _clip(text: str, limit: int) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def _clamp01(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, parsed))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

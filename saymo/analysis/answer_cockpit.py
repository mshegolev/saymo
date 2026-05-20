"""Answer draft, cockpit, and audit contracts for live meeting assistance."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from saymo.analysis.meeting_memory import MeetingAskAnswer, MeetingSearchResult
from saymo.analysis.trigger_sessions import SESSION_LEDGER_DIR


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


@dataclass(frozen=True)
class CockpitState:
    """Current review/control state for one answer draft."""

    profile: str
    session_id: str
    draft: AnswerDraft
    state: str = "pending"
    selected_action: str = ""
    approved_text: str = ""
    updated_at: str = ""
    available_actions: tuple[str, ...] = ("speak", "edit", "skip", "takeover")


@dataclass(frozen=True)
class AuditEvent:
    """Sanitized local audit event for answer cockpit decisions."""

    event_id: str
    event_type: str
    profile: str
    session_id: str
    draft_id: str
    created_at: str
    action: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


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


def cockpit_state_path(base_dir: Path, profile: str, session_id: str) -> Path:
    """Return local cockpit state sidecar path for one session."""
    return (
        Path(base_dir).expanduser()
        / profile
        / SESSION_LEDGER_DIR
        / f"{session_id}.cockpit.json"
    )


def answer_audit_path(base_dir: Path, profile: str, session_id: str) -> Path:
    """Return local answer audit JSONL path for one session."""
    return (
        Path(base_dir).expanduser()
        / profile
        / SESSION_LEDGER_DIR
        / f"{session_id}.answer-audit.jsonl"
    )


def build_cockpit_state(draft: AnswerDraft, *, updated_at: str | None = None) -> CockpitState:
    """Create pending cockpit state for a draft."""
    return CockpitState(
        profile=draft.profile,
        session_id=draft.session_id,
        draft=draft,
        state=draft.action_state or "pending",
        selected_action="",
        approved_text="",
        updated_at=updated_at or _now(),
    )


def cockpit_state_to_json(state: CockpitState) -> dict[str, Any]:
    """Serialize cockpit state to JSON-compatible primitives."""
    return {
        "profile": state.profile,
        "session_id": state.session_id,
        "draft": answer_draft_to_json(state.draft),
        "state": state.state,
        "selected_action": state.selected_action,
        "approved_text": state.approved_text,
        "updated_at": state.updated_at,
        "available_actions": list(state.available_actions),
    }


def cockpit_state_from_json(data: Mapping[str, Any]) -> CockpitState:
    """Load cockpit state from JSON-compatible primitives."""
    draft = answer_draft_from_json(data.get("draft") or {})
    return CockpitState(
        profile=str(data.get("profile") or draft.profile),
        session_id=str(data.get("session_id") or draft.session_id),
        draft=draft,
        state=str(data.get("state") or "pending"),
        selected_action=str(data.get("selected_action") or ""),
        approved_text=str(data.get("approved_text") or ""),
        updated_at=str(data.get("updated_at") or ""),
        available_actions=tuple(data.get("available_actions") or ("speak", "edit", "skip", "takeover")),
    )


def write_cockpit_state(base_dir: Path, state: CockpitState) -> Path:
    """Write cockpit state sidecar for one session."""
    path = cockpit_state_path(base_dir, state.profile, state.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cockpit_state_to_json(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_cockpit_state(path: Path) -> CockpitState:
    """Load cockpit state sidecar."""
    return cockpit_state_from_json(json.loads(Path(path).read_text(encoding="utf-8")))


def apply_cockpit_action(
    state: CockpitState,
    *,
    action: str,
    edited_text: str | None = None,
    at: str | None = None,
) -> tuple[CockpitState, AuditEvent]:
    """Apply one explicit cockpit action without implicit audio playback."""
    normalized = action.strip().lower()
    if normalized not in {"speak", "edit", "skip", "takeover"}:
        raise ValueError("action must be one of: speak, edit, skip, takeover")
    now = at or _now()
    approved_text = state.draft.draft_text
    if normalized == "edit":
        approved_text = " ".join((edited_text or "").split())
        if not approved_text:
            raise ValueError("edited_text is required for edit action")
        new_state = "edited"
        summary = "draft edited and approved for review"
    elif normalized == "speak":
        new_state = "approved_to_speak"
        summary = "draft approved to speak; playback not started by this command"
    elif normalized == "skip":
        approved_text = ""
        new_state = "skipped"
        summary = "draft skipped"
    else:
        approved_text = ""
        new_state = "takeover"
        summary = "manual takeover selected"
    updated = CockpitState(
        profile=state.profile,
        session_id=state.session_id,
        draft=AnswerDraft(
            draft_id=state.draft.draft_id,
            profile=state.draft.profile,
            session_id=state.draft.session_id,
            question=state.draft.question,
            created_at=state.draft.created_at,
            trigger_evidence=state.draft.trigger_evidence,
            citations=state.draft.citations,
            sources=state.draft.sources,
            draft_text=state.draft.draft_text,
            confidence=state.draft.confidence,
            composer=state.draft.composer,
            action_state=new_state,
        ),
        state=new_state,
        selected_action=normalized,
        approved_text=approved_text,
        updated_at=now,
        available_actions=state.available_actions,
    )
    event = AuditEvent(
        event_id=_event_id(state.profile, state.session_id, state.draft.draft_id, now, normalized),
        event_type="cockpit_action",
        profile=state.profile,
        session_id=state.session_id,
        draft_id=state.draft.draft_id,
        created_at=now,
        action=normalized,
        summary=summary,
        metadata={
            "state": new_state,
            "confidence": round(state.draft.confidence, 4),
            "citation_count": len(state.draft.citations),
            "playback_started": False,
        },
    )
    return updated, event


def audit_event_to_json(event: AuditEvent) -> dict[str, Any]:
    """Serialize audit event to JSON-compatible primitives."""
    return asdict(event)


def audit_event_from_json(data: Mapping[str, Any]) -> AuditEvent:
    """Load audit event from JSON-compatible primitives."""
    return AuditEvent(
        event_id=str(data.get("event_id") or ""),
        event_type=str(data.get("event_type") or ""),
        profile=str(data.get("profile") or ""),
        session_id=str(data.get("session_id") or ""),
        draft_id=str(data.get("draft_id") or ""),
        created_at=str(data.get("created_at") or ""),
        action=str(data.get("action") or ""),
        summary=str(data.get("summary") or ""),
        metadata=dict(data.get("metadata") or {}),
    )


def append_audit_event(base_dir: Path, event: AuditEvent) -> Path:
    """Append one event to the local answer audit JSONL ledger."""
    path = answer_audit_path(base_dir, event.profile, event.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit_event_to_json(event), ensure_ascii=False) + "\n")
    return path


def load_audit_events(path: Path) -> tuple[AuditEvent, ...]:
    """Load local answer audit events from JSONL."""
    events: list[AuditEvent] = []
    if not Path(path).exists():
        return ()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(audit_event_from_json(payload))
    return tuple(events)


def draft_created_event(draft: AnswerDraft, *, at: str | None = None) -> AuditEvent:
    """Build an audit event for a displayed/generated draft."""
    created = at or _now()
    return AuditEvent(
        event_id=_event_id(draft.profile, draft.session_id, draft.draft_id, created, "draft"),
        event_type="draft_shown",
        profile=draft.profile,
        session_id=draft.session_id,
        draft_id=draft.draft_id,
        created_at=created,
        summary="draft shown in answer cockpit",
        metadata={
            "confidence": round(draft.confidence, 4),
            "citation_count": len(draft.citations),
            "source_count": len(draft.sources),
            "action_state": draft.action_state,
        },
    )


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


def render_cockpit_state(state: CockpitState) -> str:
    """Render current cockpit state and available actions."""
    lines = [
        "# Answer Cockpit",
        "",
        f"state: {state.state}",
        f"profile: {state.profile}",
        f"session: {state.session_id or '-'}",
        f"draft: {state.draft.draft_id}",
        f"confidence: {state.draft.confidence:.2f}",
        f"selected action: {state.selected_action or '-'}",
        f"available actions: {', '.join(state.available_actions)}",
        "",
        "## Trigger Evidence",
        (
            f"- trigger={'yes' if state.draft.trigger_evidence.trigger else 'no'} "
            f"question={'yes' if state.draft.trigger_evidence.question else 'no'} "
            f"will_answer={'yes' if state.draft.trigger_evidence.will_answer else 'no'} "
            f"confidence={state.draft.trigger_evidence.confidence:.2f} "
            f"addressing={state.draft.trigger_evidence.addressing or '-'}"
        ),
        "",
        "## Draft",
        state.approved_text or state.draft.draft_text or "(empty)",
        "",
        "## Citations",
    ]
    if state.draft.citations:
        for citation in state.draft.citations:
            lines.append(
                f"- {citation.citation} speaker={citation.speaker} "
                f"category={citation.category} text={_clip(citation.transcript, 140)}"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Sources")
    if state.draft.sources:
        for source in state.draft.sources:
            detail = source.diagnostic or _clip(source.summary, 120)
            lines.append(f"- {source.name}: {source.status} {detail}".rstrip())
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def render_audit_events(events: Iterable[AuditEvent]) -> str:
    """Render audit events as grep-friendly lines."""
    lines = []
    for event in events:
        lines.append(
            f"{event.created_at} type={event.event_type} action={event.action or '-'} "
            f"profile={event.profile} session={event.session_id} draft={event.draft_id} "
            f"summary={event.summary}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def render_sanitized_audit_report(events: Iterable[AuditEvent]) -> str:
    """Render sanitized markdown audit report."""
    events = tuple(events)
    lines = [
        "# Answer Cockpit Audit Report",
        "",
        f"- events: {len(events)}",
        "- raw audio: omitted",
        "- secrets and config values: omitted",
        "",
        "## Events",
    ]
    for event in events:
        lines.append(
            f"- {event.created_at}: type={event.event_type}, action={event.action or '-'}, "
            f"state={event.metadata.get('state', '-')}, draft={event.draft_id}, "
            f"summary={event.summary}"
        )
    if not events:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


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


def _event_id(profile: str, session_id: str, draft_id: str, created_at: str, event: str) -> str:
    raw = f"{profile}-{session_id}-{draft_id}-{created_at}-{event}"
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", raw).strip("-._")
    return slug or "event"


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

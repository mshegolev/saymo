"""Tests for answer draft contracts and rendering."""

from saymo.analysis.answer_cockpit import (
    TriggerEvidence,
    append_audit_event,
    answer_draft_from_json,
    answer_draft_to_json,
    apply_cockpit_action,
    build_answer_draft,
    build_cockpit_state,
    build_trigger_evidence,
    draft_created_event,
    load_audit_events,
    render_audit_events,
    render_cockpit_state,
    render_sanitized_audit_report,
    render_answer_draft,
    source_evidence_error,
    source_evidence_from_payload,
    write_cockpit_state,
    load_cockpit_state,
)
from saymo.analysis.meeting_memory import MeetingAskAnswer, MeetingSearchResult


def _meeting_answer():
    result = MeetingSearchResult(
        profile="daily",
        session_id="daily-1",
        session_name="daily",
        sequence=1,
        start_seconds=0.0,
        end_seconds=8.0,
        speaker="other",
        category="asked_to_speak",
        created_at="2026-05-20T10:00:00",
        transcript="John, what is the release status?",
        citation="daily-1#1@0.0-8.0s",
        score=2.0,
    )
    return MeetingAskAnswer(
        question="What is the release status?",
        answer="По найденным фрагментам: release status [daily-1#1@0.0-8.0s]",
        citations=(result,),
    )


def test_build_trigger_evidence_infers_question_and_confidence():
    evidence = build_trigger_evidence(
        transcript="John, what is the status?",
        profile="daily",
        session_id="daily-1",
        trigger=True,
        will_answer=True,
        addressing="addressed_to_me",
    )

    assert evidence.question is True
    assert evidence.confidence > 0.7
    assert evidence.profile == "daily"


def test_build_answer_draft_preserves_citations_and_sources():
    source = source_evidence_from_payload(
        "jira",
        {"today": "Release verification is in progress"},
        fetched_at="2026-05-20T10:00:00+00:00",
    )
    draft = build_answer_draft(
        profile="daily",
        session_id="daily-1",
        question="What is the release status?",
        trigger_evidence=TriggerEvidence(
            transcript="John, what is the release status?",
            trigger=True,
            question=True,
            will_answer=True,
            confidence=0.9,
        ),
        meeting_answer=_meeting_answer(),
        sources=(source,),
        created_at="2026-05-20T10:00:00+00:00",
    )

    assert draft.action_state == "pending"
    assert draft.confidence > 0.6
    assert draft.citations[0].citation == "daily-1#1@0.0-8.0s"
    assert draft.sources[0].status == "available"
    assert "Release verification" in draft.draft_text


def test_answer_draft_json_round_trip_and_render():
    draft = build_answer_draft(
        profile="daily",
        session_id="daily-1",
        question="What is the release status?",
        trigger_evidence=TriggerEvidence(transcript="John?", confidence=0.5),
        meeting_answer=_meeting_answer(),
        created_at="2026-05-20T10:00:00+00:00",
    )

    loaded = answer_draft_from_json(answer_draft_to_json(draft))
    rendered = render_answer_draft(loaded)

    assert loaded.draft_id == draft.draft_id
    assert "citations:" in rendered
    assert "daily-1#1@0.0-8.0s" in rendered


def test_source_evidence_error_redacts_token_like_values():
    evidence = source_evidence_error("jira", "API_TOKEN=secret-value failed")

    assert evidence.status == "error"
    assert "secret-value" not in evidence.diagnostic
    assert "<redacted>" in evidence.diagnostic


def test_cockpit_state_renders_pending_actions(tmp_path):
    draft = build_answer_draft(
        profile="daily",
        session_id="daily-1",
        question="What is the release status?",
        trigger_evidence=TriggerEvidence(transcript="John?", confidence=0.5),
        meeting_answer=_meeting_answer(),
        created_at="2026-05-20T10:00:00+00:00",
    )
    state = build_cockpit_state(draft, updated_at="2026-05-20T10:00:01+00:00")
    path = write_cockpit_state(tmp_path, state)
    loaded = load_cockpit_state(path)
    rendered = render_cockpit_state(loaded)

    assert loaded.state == "pending"
    assert "available actions: speak, edit, skip, takeover" in rendered
    assert "daily-1#1@0.0-8.0s" in rendered


def test_apply_cockpit_speak_records_approval_without_playback():
    draft = build_answer_draft(
        profile="daily",
        session_id="daily-1",
        question="What is the release status?",
        trigger_evidence=TriggerEvidence(transcript="John?", confidence=0.5),
        meeting_answer=_meeting_answer(),
        created_at="2026-05-20T10:00:00+00:00",
    )
    state = build_cockpit_state(draft)

    updated, event = apply_cockpit_action(
        state,
        action="speak",
        at="2026-05-20T10:00:02+00:00",
    )

    assert updated.state == "approved_to_speak"
    assert updated.draft.action_state == "approved_to_speak"
    assert event.action == "speak"
    assert event.metadata["playback_started"] is False


def test_apply_cockpit_edit_requires_text_and_saves_approved_text():
    draft = build_answer_draft(
        profile="daily",
        session_id="daily-1",
        question="What is the release status?",
        trigger_evidence=TriggerEvidence(transcript="John?", confidence=0.5),
        meeting_answer=_meeting_answer(),
        created_at="2026-05-20T10:00:00+00:00",
    )
    state = build_cockpit_state(draft)

    updated, event = apply_cockpit_action(
        state,
        action="edit",
        edited_text="I will verify the release after this call.",
        at="2026-05-20T10:00:03+00:00",
    )

    assert updated.state == "edited"
    assert updated.approved_text == "I will verify the release after this call."
    assert event.metadata["state"] == "edited"


def test_audit_events_round_trip_and_sanitized_report(tmp_path):
    draft = build_answer_draft(
        profile="daily",
        session_id="daily-1",
        question="What is the release status?",
        trigger_evidence=TriggerEvidence(transcript="John?", confidence=0.5),
        meeting_answer=_meeting_answer(),
        created_at="2026-05-20T10:00:00+00:00",
    )
    event = draft_created_event(draft, at="2026-05-20T10:00:04+00:00")
    path = append_audit_event(tmp_path, event)

    events = load_audit_events(path)
    rendered = render_audit_events(events)
    report = render_sanitized_audit_report(events)

    assert events[0].event_type == "draft_shown"
    assert "type=draft_shown" in rendered
    assert "raw audio: omitted" in report

"""Local ledgers for trigger-capture training sessions."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SESSION_LEDGER_DIR = "_sessions"


@dataclass(frozen=True)
class TriggerSessionSummary:
    """Aggregate counts for one trigger-capture session."""

    total_windows: int = 0
    saved_samples: int = 0
    skipped_silence: int = 0
    categories: dict[str, int] = field(default_factory=dict)
    speakers: dict[str, int] = field(default_factory=dict)
    answer_decisions: dict[str, int] = field(default_factory=dict)
    first_sample_at: str = ""
    last_sample_at: str = ""
    readiness: str = "empty"


@dataclass(frozen=True)
class TriggerSession:
    """Persistent metadata for one capture run."""

    profile: str
    session_id: str
    session_name: str
    started_at: str
    status: str = "running"
    ended_at: str = ""
    skipped_silence: int = 0
    summary: TriggerSessionSummary = field(default_factory=TriggerSessionSummary)
    path: Path | None = None


def start_trigger_session(
    *,
    base_dir: Path,
    profile: str,
    session_name: str | None,
    started_at: str,
) -> TriggerSession:
    """Create a running session ledger and return its metadata."""
    resolved_name = " ".join((session_name or profile or "capture").split())
    base_session_id = make_session_id(resolved_name, started_at)
    session_id = base_session_id
    path = session_ledger_path(base_dir, profile, session_id)
    suffix = 2
    while path.exists():
        session_id = f"{base_session_id}-{suffix}"
        path = session_ledger_path(base_dir, profile, session_id)
        suffix += 1
    session = TriggerSession(
        profile=profile,
        session_id=session_id,
        session_name=resolved_name,
        started_at=started_at,
        path=path,
    )
    write_session_ledger(session)
    return session


def finish_trigger_session(
    *,
    base_dir: Path,
    session: TriggerSession,
    ended_at: str,
    status: str,
    skipped_silence: int = 0,
) -> TriggerSession:
    """Persist a final session summary."""
    summary = summarize_trigger_session(
        base_dir=base_dir,
        profile=session.profile,
        session_id=session.session_id,
        skipped_silence=skipped_silence,
    )
    finished = TriggerSession(
        profile=session.profile,
        session_id=session.session_id,
        session_name=session.session_name,
        started_at=session.started_at,
        status=status,
        ended_at=ended_at,
        skipped_silence=skipped_silence,
        summary=summary,
        path=session.path
        or session_ledger_path(base_dir, session.profile, session.session_id),
    )
    write_session_ledger(finished)
    return finished


def write_session_ledger(session: TriggerSession) -> Path:
    """Write a session ledger JSON file."""
    if session.path is None:
        raise ValueError("session.path is required")
    session.path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "profile": session.profile,
        "session_id": session.session_id,
        "session_name": session.session_name,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "status": session.status,
        "skipped_silence": session.skipped_silence,
        "summary": asdict(session.summary),
    }
    session.path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return session.path


def load_trigger_session(path: Path, *, base_dir: Path | None = None) -> TriggerSession:
    """Load one session ledger and refresh summary counts from sample JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    profile = str(data.get("profile") or _profile_from_ledger_path(path))
    session_id = str(data.get("session_id") or Path(path).stem)
    skipped_silence = int(data.get("skipped_silence") or 0)
    root = Path(base_dir).expanduser() if base_dir else _base_from_ledger_path(path)
    summary = summarize_trigger_session(
        base_dir=root,
        profile=profile,
        session_id=session_id,
        skipped_silence=skipped_silence,
    )
    return TriggerSession(
        profile=profile,
        session_id=session_id,
        session_name=str(data.get("session_name") or session_id),
        started_at=str(data.get("started_at") or ""),
        ended_at=str(data.get("ended_at") or ""),
        status=str(data.get("status") or "unknown"),
        skipped_silence=skipped_silence,
        summary=summary,
        path=Path(path),
    )


def list_trigger_sessions(
    base_dir: Path,
    profile: str | None = None,
) -> list[TriggerSession]:
    """Return prior trigger-capture sessions, newest first."""
    root = Path(base_dir).expanduser()
    if profile:
        paths = sorted((root / profile / SESSION_LEDGER_DIR).glob("*.json"))
    else:
        paths = sorted(root.glob(f"*/{SESSION_LEDGER_DIR}/*.json"))
    sessions: list[TriggerSession] = []
    for path in paths:
        try:
            sessions.append(load_trigger_session(path, base_dir=root))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return sorted(sessions, key=lambda s: (s.started_at, s.session_id), reverse=True)


def summarize_trigger_session(
    *,
    base_dir: Path,
    profile: str,
    session_id: str,
    skipped_silence: int = 0,
) -> TriggerSessionSummary:
    """Summarize saved samples that belong to one session."""
    categories: Counter[str] = Counter()
    speakers: Counter[str] = Counter()
    decisions: Counter[str] = Counter()
    created: list[str] = []

    for data in iter_session_sample_metadata(base_dir, profile, session_id):
        category = str(data.get("category") or "unknown")
        categories[category] += 1
        speakers[_normalize_speaker(data.get("speaker"))] += 1
        decisions[_normalize_answer_decision(data.get("answer_decision"))] += 1
        created_at = str(data.get("created_at") or "")
        if created_at:
            created.append(created_at)

    saved = sum(categories.values())
    readiness = basic_training_readiness(
        saved_samples=saved,
        answer_decisions=dict(decisions),
    )
    return TriggerSessionSummary(
        total_windows=saved + skipped_silence,
        saved_samples=saved,
        skipped_silence=skipped_silence,
        categories=dict(sorted(categories.items())),
        speakers=dict(sorted(speakers.items())),
        answer_decisions=dict(sorted(decisions.items())),
        first_sample_at=min(created) if created else "",
        last_sample_at=max(created) if created else "",
        readiness=readiness,
    )


def iter_session_sample_metadata(
    base_dir: Path,
    profile: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Load sample JSON files for a session, ignoring ledger files."""
    root = Path(base_dir).expanduser() / profile
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/*.json")):
        if path.parent.name == SESSION_LEDGER_DIR:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("session_id") != session_id:
            continue
        records.append(data)
    return records


def basic_training_readiness(
    *,
    saved_samples: int,
    answer_decisions: dict[str, int],
    min_samples: int = 4,
) -> str:
    """Small Phase 8 readiness hint; full gates are Phase 10 scope."""
    if saved_samples <= 0:
        return "empty"
    if saved_samples < min_samples:
        return "needs_samples"
    accepted = answer_decisions.get("accepted", 0)
    rejected = answer_decisions.get("rejected", 0)
    if not accepted or not rejected:
        return "needs_labels"
    return "ready"


def session_ledger_path(base_dir: Path, profile: str, session_id: str) -> Path:
    """Return the local ledger path for a session id."""
    return (
        Path(base_dir).expanduser()
        / profile
        / SESSION_LEDGER_DIR
        / f"{session_id}.json"
    )


def make_session_id(session_name: str, started_at: str) -> str:
    """Build a readable, filesystem-safe session id."""
    slug = re.sub(r"[^\w.-]+", "-", session_name.strip().lower(), flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-._") or "capture"
    digits = re.sub(r"\D", "", started_at)
    if len(digits) >= 14:
        stamp = f"{digits[:8]}-{digits[8:14]}"
    else:
        stamp = digits or "session"
    return f"{slug}-{stamp}"


def _normalize_speaker(value: object) -> str:
    label = str(value or "").strip().lower()
    return label if label in {"me", "other", "unknown"} else "unknown"


def _normalize_answer_decision(value: object) -> str:
    label = str(value or "").strip().lower()
    return label if label in {"accepted", "rejected", "unlabeled"} else "unlabeled"


def _base_from_ledger_path(path: Path) -> Path:
    try:
        return Path(path).parents[2]
    except IndexError:
        return Path(path).parent


def _profile_from_ledger_path(path: Path) -> str:
    try:
        return Path(path).parents[1].name
    except IndexError:
        return ""

"""Tier-A response cache for CPU-only real-time Q&A.

Pre-synthesises a small library of answers to common stand-up follow-up
questions in the user's fine-tuned voice, then plays them from cache when
the trigger fires with a matching intent. Latency is playback-only (~100 ms)
— no synthesis on the hot path, which means real-time Q&A works on a
machine without Apple Silicon GPU / MLX.

The default library lives in ``DEFAULT_RESPONSE_LIBRARY`` below. Users
extend or override entries via ``config.responses.library.<key>`` — the
same pattern as the ``DEFAULT_*_PROMPT_*`` constants in
``saymo/speech/ollama_composer.py``. Source stays project-agnostic; all
personal or team-specific wording belongs in the user's ``config.yaml``.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

logger = logging.getLogger("saymo.analysis.response_cache")

DEFAULT_CACHE_DIR = Path.home() / ".saymo" / "audio_cache" / "responses"


@dataclass
class ResponseEntry:
    """One intent the cache can answer.

    Attributes:
        key: Stable short ID used as filename and lookup key (snake_case).
        triggers: Lower-case keyword phrases. A transcript window matches
            this entry when it contains all tokens of at least one trigger
            phrase. Shorter triggers match more aggressively — prefer 2–4
            meaningful words per phrase.
        variants: Candidate answer texts. Build-time synthesises each;
            lookup picks one at random so repeated hits do not sound
            identical on the same call.
        description: Human-readable context for debugging / config docs.
    """

    key: str
    triggers: list[str]
    variants: list[str]
    description: str = ""


@dataclass
class CachedResponse:
    """One playable cached response, returned by ``ResponseCache.lookup``."""

    key: str
    audio_path: Path
    text: str
    confidence: float


DEFAULT_RESPONSE_LIBRARY: dict[str, ResponseEntry] = {
    "status_generic": ResponseEntry(
        key="status_generic",
        triggers=["как дела", "что по задаче", "что по статусу", "какой статус", "что со статусом"],
        variants=[
            "В работе, движется по плану, деталями поделюсь после митинга.",
            "Сейчас в процессе, всё идёт в графике.",
        ],
        description="Generic status on a task in progress",
    ),
    "status_progressing": ResponseEntry(
        key="status_progressing",
        triggers=["движется", "идёт работа", "как продвигается"],
        variants=[
            "Движется, основную часть уже сделал, осталось довести до ума.",
            "Прогресс есть, финализирую на этой неделе.",
        ],
        description="Task is progressing normally",
    ),
    "status_done": ResponseEntry(
        key="status_done",
        triggers=["закончил", "доделал", "готово", "завершил"],
        variants=[
            "Да, закончил, отправил на ревью.",
            "Готово, жду проверки.",
        ],
        description="Task is done",
    ),
    "status_testing": ResponseEntry(
        key="status_testing",
        triggers=["тестирую", "на тестах", "проверяю"],
        variants=[
            "Сейчас в тестировании, проверяю основные сценарии.",
            "Прогоняю тесты, если всё зелёное — отправлю в ревью.",
        ],
        description="Task is in testing phase",
    ),
    "status_review": ResponseEntry(
        key="status_review",
        triggers=["на ревью", "в ревью", "ждёт ревью"],
        variants=[
            "Висит на ревью, жду комментариев.",
            "Отправил в ревью, как только апрувнут — замержу.",
        ],
        description="Task is waiting for code review",
    ),
    "blockers_none": ResponseEntry(
        key="blockers_none",
        triggers=["есть блокеры", "блокеры", "что блокирует", "что мешает"],
        variants=[
            "Блокеров нет, всё движется.",
            "Сейчас всё идёт без блокеров.",
        ],
        description="No blockers",
    ),
    "blockers_dependency": ResponseEntry(
        key="blockers_dependency",
        triggers=["жду от команды", "жду коллег", "нужна помощь от"],
        variants=[
            "Жду ответа от смежной команды, как только получу — двигаемся дальше.",
            "Есть зависимость от коллег, напомню сегодня.",
        ],
        description="Blocked on a dependency from another team/person",
    ),
    "blockers_api": ResponseEntry(
        key="blockers_api",
        triggers=["внешний апи", "внешний сервис", "стороннее апи", "апи не работает"],
        variants=[
            "Упёрся во внешний сервис, пишу в поддержку параллельно.",
            "Внешнее API ведёт себя нестабильно, разбираюсь, есть ли обходной путь.",
        ],
        description="Blocked on external API",
    ),
    "eta_today": ResponseEntry(
        key="eta_today",
        triggers=["когда будет", "к какому сроку", "сегодня успеешь"],
        variants=[
            "Планирую закрыть сегодня до конца дня.",
            "Сегодня должно быть готово.",
        ],
        description="ETA: today",
    ),
    "eta_tomorrow": ResponseEntry(
        key="eta_tomorrow",
        triggers=["завтра", "на завтра"],
        variants=[
            "Ожидаю, что к завтра будет готово.",
            "Завтра докручу оставшееся и покажу.",
        ],
        description="ETA: tomorrow",
    ),
    "eta_eow": ResponseEntry(
        key="eta_eow",
        triggers=["к концу недели", "на этой неделе", "пятница"],
        variants=[
            "К концу недели должно быть готово.",
            "Цель — закрыть задачу на этой неделе.",
        ],
        description="ETA: end of week",
    ),
    "eta_unclear": ResponseEntry(
        key="eta_unclear",
        triggers=["пока не понятно", "сложно сказать", "затрудняюсь"],
        variants=[
            "Пока не могу точно сказать, дам оценку после митинга.",
            "Нужно копнуть глубже, чтобы дать корректный срок.",
        ],
        description="ETA unclear, will clarify later",
    ),
    "help_needed": ResponseEntry(
        key="help_needed",
        triggers=["нужна помощь", "помощь нужна", "можешь помочь"],
        variants=[
            "Да, помощь пригодится, напишу в чат детали.",
            "Было бы здорово обсудить, накину контекст после митинга.",
        ],
        description="Help is needed",
    ),
    "help_not_needed": ResponseEntry(
        key="help_not_needed",
        triggers=["справишься", "справляешься", "сам разберёшься"],
        variants=[
            "Пока справляюсь, если что — позову.",
            "Сейчас разберусь сам, если упрусь — напишу в чат.",
        ],
        description="Help not needed",
    ),
    "defer_offline": ResponseEntry(
        key="defer_offline",
        triggers=["обсудим", "давай отдельно", "оффлайн"],
        variants=[
            "Давай обсудим после митинга, там есть нюансы.",
            "Отдельно созвонимся, скину приглашение.",
        ],
        description="Defer to a separate 1:1 after the meeting",
    ),
    "clarify_question": ResponseEntry(
        key="clarify_question",
        triggers=["не совсем понял", "уточни", "что именно"],
        variants=[
            "Можешь уточнить вопрос, чтобы я ответил точнее?",
            "Не совсем понял, ты про какую именно часть спрашиваешь?",
        ],
        description="Ask the asker to clarify",
    ),
    "progress_demo": ResponseEntry(
        key="progress_demo",
        triggers=["покажи", "демо", "можно посмотреть"],
        variants=[
            "Могу показать после митинга, открою экран.",
            "Готов продемонстрировать, давай после колла.",
        ],
        description="Offer to demo after the call",
    ),
    "confirm": ResponseEntry(
        key="confirm",
        triggers=["всё верно", "правильно понял", "так и есть"],
        variants=[
            "Да, всё так.",
            "Верно, именно так.",
        ],
        description="Confirm the asker's understanding",
    ),
    "deny": ResponseEntry(
        key="deny",
        triggers=["не так", "неверно", "не совсем"],
        variants=[
            "Не совсем, уточню после митинга.",
            "Есть нюанс, распишу подробнее отдельно.",
        ],
        description="Polite correction without going into detail",
    ),
    "update_later": ResponseEntry(
        key="update_later",
        triggers=["напиши потом", "апдейт", "пришлёшь апдейт"],
        variants=[
            "Скину апдейт в чат после митинга.",
            "Напишу подробности отдельно, чтобы не задерживать.",
        ],
        description="Promise to send a written update later",
    ),
    "refactor": ResponseEntry(
        key="refactor",
        triggers=["рефакторинг", "переписываю", "рефактор"],
        variants=[
            "Сейчас рефакторю часть кода, чтобы дальше было проще.",
            "В процессе рефакторинга, затем продолжу основную задачу.",
        ],
        description="Currently refactoring code",
    ),
    "research": ResponseEntry(
        key="research",
        triggers=["исследую", "смотрю варианты", "ресёрчу"],
        variants=[
            "Сейчас сравниваю варианты, выберу оптимальный и вернусь с решением.",
            "В ресёрче, как будут выводы — поделюсь.",
        ],
        description="Currently doing research / evaluation",
    ),
    "estimation_pending": ResponseEntry(
        key="estimation_pending",
        triggers=["оценка", "estimate", "сколько займёт"],
        variants=[
            "Уточняю оценку, дам цифры до конца дня.",
            "Сейчас разбиваю задачу, после этого дам точный срок.",
        ],
        description="Estimation still in progress",
    ),
    "acknowledge": ResponseEntry(
        key="acknowledge",
        triggers=["принял", "услышал", "понял тебя"],
        variants=[
            "Принял, учту.",
            "Понял, возьму в работу.",
        ],
        description="Generic acknowledgement",
    ),
}


def _entry_from_dict(key: str, data: dict) -> ResponseEntry:
    """Build a ``ResponseEntry`` from a config override dict."""
    return ResponseEntry(
        key=key,
        triggers=list(data.get("triggers", [])),
        variants=list(data.get("variants", [])),
        description=data.get("description", ""),
    )


def build_library(overrides: dict | None) -> dict[str, ResponseEntry]:
    """Merge ``DEFAULT_RESPONSE_LIBRARY`` with user overrides.

    Keys present in both are replaced by the user version. Keys only in the
    overrides are appended. Entries are validated — an override with no
    triggers or no variants is skipped with a warning, so a malformed user
    config does not crash startup.
    """
    library = {k: v for k, v in DEFAULT_RESPONSE_LIBRARY.items()}
    if not overrides:
        return library
    for key, data in overrides.items():
        if not isinstance(data, dict):
            logger.warning(f"response override '{key}' is not a mapping; skipping")
            continue
        entry = _entry_from_dict(key, data)
        if not entry.triggers or not entry.variants:
            logger.warning(
                f"response override '{key}' is missing triggers or variants; skipping"
            )
            continue
        library[key] = entry
    return library


def _tokenize(text: str) -> list[str]:
    """Lower-case tokens used for trigger matching."""
    return re.findall(r"\w+", text.lower())


@dataclass
class _IndexedEntry:
    entry: ResponseEntry
    trigger_tokens: list[list[str]] = field(default_factory=list)

    def match_score(self, window_tokens: list[str]) -> tuple[float, int]:
        """Score how well this entry matches the transcript window.

        Returns (confidence, best_trigger_index). Confidence is the ratio
        of trigger tokens that appear **in order** within the window — a
        phrase trigger ``["нужна", "помощь"]`` matches the window
        ``["мне", "сейчас", "нужна", "любая", "помощь"]`` even though
        other words appear between.
        """
        best = 0.0
        best_idx = -1
        window_set = set(window_tokens)
        for i, tokens in enumerate(self.trigger_tokens):
            if not tokens:
                continue
            hits = sum(1 for t in tokens if t in window_set)
            score = hits / len(tokens)
            if score > best:
                best = score
                best_idx = i
        return best, best_idx


class ResponseCache:
    """Pre-synthesised library of short stand-up answers.

    Build once per ``saymo prepare`` cycle via :meth:`build`, then query
    at runtime via :meth:`lookup`. The cache is engine-agnostic — the
    TTS engine is injected as a ``synth_fn`` callback so this module
    stays testable on CPU-only machines with no real TTS installed.
    """

    def __init__(
        self,
        library: dict[str, ResponseEntry] | None = None,
        cache_dir: Path | None = None,
        confidence_threshold: float = 0.6,
    ):
        self.library = library if library is not None else dict(DEFAULT_RESPONSE_LIBRARY)
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.confidence_threshold = confidence_threshold

        self._indexed: list[_IndexedEntry] = [
            _IndexedEntry(
                entry=e,
                trigger_tokens=[_tokenize(t) for t in e.triggers],
            )
            for e in self.library.values()
        ]

    # ------------------------------------------------------------------
    # Build (offline, called by ``saymo prepare-responses``)
    # ------------------------------------------------------------------

    async def build(
        self,
        synth_fn: Callable[[str], Awaitable[bytes]],
        progress: Callable[[str, int, int], None] | None = None,
        force: bool = False,
    ) -> list[Path]:
        """Synthesise every variant of every entry and write WAV files.

        Args:
            synth_fn: Async callable ``(text) -> wav_bytes``. The caller
                selects which TTS engine it wraps; this module does not
                import any TTS engine directly.
            progress: Optional callback ``(key, idx, total)`` for a UI
                progress bar.
            force: If ``False`` (default), entries whose files already
                exist on disk are skipped. Pass ``True`` after retraining
                the voice model to regenerate from scratch.

        Returns:
            List of paths actually written (skipped ones are not in the
            list).
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        total = sum(len(e.variants) for e in self.library.values())
        seen = 0
        for entry in self.library.values():
            for variant_idx, text in enumerate(entry.variants):
                seen += 1
                path = self._variant_path(entry.key, variant_idx, text)
                if progress:
                    progress(entry.key, seen, total)
                if path.exists() and not force:
                    logger.debug(f"cache hit: {path.name}")
                    continue
                try:
                    audio = await synth_fn(text)
                except Exception as e:
                    logger.warning(f"synth failed for '{entry.key}' variant {variant_idx}: {e}")
                    continue
                if not audio:
                    logger.warning(f"empty audio for '{entry.key}' variant {variant_idx}")
                    continue
                path.write_bytes(audio)
                written.append(path)
                logger.info(f"cached: {path.name} ({len(audio) // 1024} KB)")

        return written

    def _variant_path(self, key: str, variant_idx: int, text: str) -> Path:
        """Deterministic filename per variant. Text hash means edits
        invalidate the old file automatically."""
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        return self.cache_dir / f"{key}_{variant_idx}_{digest}.wav"

    # ------------------------------------------------------------------
    # Lookup (runtime, called from _auto())
    # ------------------------------------------------------------------

    def lookup(self, transcript_window: str) -> CachedResponse | None:
        """Find the best matching cached response for a transcript window.

        Returns ``None`` when no entry clears ``confidence_threshold`` or
        when the matched entry has no cached file on disk (caller should
        fall back to generic cached standup playback).
        """
        if not transcript_window.strip():
            return None

        tokens = _tokenize(transcript_window)
        best_score = 0.0
        best_entry: ResponseEntry | None = None
        for ix in self._indexed:
            score, _ = ix.match_score(tokens)
            if score > best_score:
                best_score = score
                best_entry = ix.entry

        if best_entry is None or best_score < self.confidence_threshold:
            logger.debug(
                f"no match (best={best_score:.2f} < {self.confidence_threshold})"
            )
            return None

        # Pick a random variant that actually has a cached file.
        candidates: list[tuple[int, str, Path]] = []
        for idx, text in enumerate(best_entry.variants):
            path = self._variant_path(best_entry.key, idx, text)
            if path.exists():
                candidates.append((idx, text, path))
        if not candidates:
            logger.info(
                f"matched '{best_entry.key}' but no cached audio; run 'saymo prepare-responses'"
            )
            return None

        idx, text, path = random.choice(candidates)
        logger.info(
            f"cache hit: '{best_entry.key}' variant {idx} "
            f"(confidence={best_score:.2f})"
        )
        return CachedResponse(
            key=best_entry.key,
            audio_path=path,
            text=text,
            confidence=best_score,
        )

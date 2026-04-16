# ADR-001: Fully Local Architecture (No Cloud APIs)

**Status:** Accepted
**Date:** 2026-04-16
**Author:** Mikhail Shchegolev

## Context

Saymo — AI-ассистент для стендап-митингов в RingCentral Video (Glip). Изначально рассматривались облачные API (Anthropic Claude, OpenAI TTS, Deepgram STT). Однако:

- Отсутствуют API ключи (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- Подписка Claude Max не даёт API доступ
- Нежелание зависеть от внешних сервисов для ежедневного инструмента
- Требование к приватности: аудио звонков не должно уходить в облако

## Decision

Весь стек работает **локально на macOS (M1 Pro, 16GB RAM)**:

| Компонент | Облако (отклонено) | Локальное (принято) |
|-----------|-------------------|---------------------|
| LLM (текст) | Claude API, OpenAI | **Ollama** (qwen2.5-coder:7b) |
| TTS (голос) | OpenAI TTS, ElevenLabs | **Coqui TTS XTTS v2** (voice clone) |
| STT (распознавание) | Deepgram, Google | **faster-whisper** (small model) |
| Task source | — | **JIRA** (корпоративная сеть) |

Единственное сетевое подключение — JIRA REST API по корпоративной сети.

## Consequences

**Positive:**
- Zero cost — нет платных API
- Приватность — аудио не покидает машину
- Автономность — работает без интернета (кроме JIRA)
- Нет rate limits и downtime внешних сервисов

**Negative:**
- Генерация аудио ~30-90с (vs ~2с в облаке) → решено через **pre-generation** в `prepare`
- Качество голоса XTTS v2 ниже ElevenLabs → компенсируется 5-минутным voice sample
- Whisper small менее точен чем Deepgram Nova-3 → компенсируется fuzzy matching + overlap chunks
- Disk usage: ~5GB (PyTorch + XTTS model + Whisper model)

## Alternatives Considered

- **Hybrid** (облачный LLM + локальный TTS): отклонено из-за отсутствия API ключей
- **macOS say** (встроенный TTS): используется как fallback, но не клонирует голос
- **Piper TTS**: используется как быстрая альтернатива (no voice clone)

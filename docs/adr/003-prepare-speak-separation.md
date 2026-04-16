# ADR-003: Separation of Prepare and Speak Phases

**Status:** Accepted
**Date:** 2026-04-16
**Author:** Mikhail Shchegolev

## Context

Генерация стендап-отчёта включает цепочку:
1. JIRA fetch (~3с)
2. Ollama LLM composition (~15с)
3. Text normalization (<1с)
4. XTTS v2 voice synthesis (~30-90с)

Суммарно **~50-110 секунд** — неприемлемо для real-time использования во время звонка.

## Decision

Разделить на два этапа с кешированием:

### `saymo prepare` (до дейли, ~60с)
1. Fetch JIRA tasks → Ollama text → save to Obsidian daily note
2. Normalize text → XTTS v2 synthesis → save WAV to `~/.saymo/audio_cache/YYYY-MM-DD.wav`

### `saymo speak` (во время дейли, ~2с)
1. Check audio cache → **instant playback** (no generation)
2. Fallback: check Obsidian text cache → generate audio on the fly
3. Fallback: full pipeline

### Трёхуровневый кеш:
```
Audio cache (~/.saymo/audio_cache/YYYY-MM-DD.wav)  → instant (~2с)
    ↓ miss
Text cache (Obsidian daily note ## Standup Summary) → needs TTS (~30с)
    ↓ miss
Full pipeline (JIRA → Ollama → TTS)                → full generation (~60с)
```

### `saymo review` (опционально)
Прослушать sentence-by-sentence, перегенерировать плохие фрагменты, собрать финальный WAV.

## Consequences

**Positive:**
- `speak --glip` срабатывает за **2 секунды** — мгновенно для контекста звонка
- Можно проверить и отредактировать аудио заранее (`review`)
- `auto` mode использует тот же кеш — без дополнительной генерации

**Negative:**
- Если забыл `prepare` — будет полная генерация (fallback работает, но медленно)
- Audio cache привязан к дате — нужно `prepare` каждый день
- Если задачи изменились после `prepare` — нужно перезапустить

## Alternatives Considered

- **Streaming TTS**: генерировать по предложениям и играть по мере готовности — сложнее, всё равно ~30с суммарно
- **Облачный TTS (OpenAI)**: ~2с генерация, но требует API key и интернет
- **Pre-record**: записать речь голосом заранее — теряется автоматизация

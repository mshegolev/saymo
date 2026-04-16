# ADR-005: Auto Mode — Parallel Capture/Transcription Pipeline

**Status:** Accepted
**Date:** 2026-04-16
**Author:** Mikhail Shchegolev

## Context

Saymo `auto` mode должен непрерывно слушать звонок и реагировать на имя пользователя. Проблемы наивной последовательной реализации:

1. **Пропуск имени**: пока Whisper обрабатывает чанк (~1-2с), аудио с именем может прийти и остаться необработанным
2. **Разрезание слов**: имя попадает на границу двух чанков и не распознаётся ни в одном
3. **Ложные пропуски**: VAD фильтр Whisper отбрасывает короткие фразы с именем

## Decision

### Параллельная архитектура (asyncio.gather)

```
sounddevice callback thread:  непрерывный захват → queue (никогда не блокируется)
                                         ↓
_transcribe_loop (async):     queue → whisper → detector → triggered.set()
                                         ↓ (Event)
_trigger_loop (async):        await triggered → drain queue → speak → resume
```

### Overlapping Sliding Window (AudioCapture)

```
|-------- chunk 1 (4s) --------|
            |-------- chunk 2 (4s) --------|
                        |-------- chunk 3 (4s) --------|
←── 2s ──→←── 2s ──→←── 2s ──→
```

- Chunk size: **4 секунды**
- Overlap: **2 секунды** (50%)
- Новый чанк каждые **2 секунды**
- Имя на границе чанков гарантированно попадает в один из двух

### Fuzzy Name Detection (TurnDetector)

Whisper может транскрибировать "Михаил" как:
- "Михоил", "Михаел", "Микаил" (акцент/шум)
- "Миш", "Мишка", "Мишань" (разговорные формы)
- "Mikhail", "Mihail" (code-switching)

Детектор содержит **расширенные паттерны** для каждого варианта имени + ищет совпадение в текущем чанке **и** объединении с предыдущим.

### Whisper Configuration
- `vad_filter=False` — отключен, чтобы не глотать короткие фразы с именем
- `beam_size=5, best_of=3` — выше точность за счёт скорости
- `condition_on_previous_text=False` — каждый чанк независим

### Anti-Echo Protection
- Флаг `speaking` — во время воспроизведения TTS транскрипция приостанавливается
- После триггера — drain audio queue (очистка устаревших чанков)
- Cooldown 45 секунд между триггерами

## Consequences

**Positive:**
- Имя **не теряется** даже если Whisper занят обработкой
- Overlap гарантирует что слово на границе попадёт хотя бы в один чанк
- Fuzzy matching компенсирует неточности Whisper
- Нет feedback loop — пауза транскрипции во время speak

**Negative:**
- Двойная обработка overlapping участков (CPU overhead ~50%)
- Whisper small на CPU: ~1-2с на 4с чанк → эффективная задержка ~3-4с от момента произнесения имени до триггера
- Если говорят быстро после имени — 2с задержка перед speak может быть заметна

## Alternatives Considered

- **Dedicated keyword spotter** (Porcupine, OpenWakeWord): быстрее, но не поддерживает русские имена out-of-the-box
- **Deepgram streaming**: <300ms задержка, но требует API key и интернет
- **VAD + имя detector**: быстрее, но пропускает имя в потоке речи
- **Полный отказ от STT**: только hotkey trigger — проще, но не автоматически

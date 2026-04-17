# ADR-007: Task Sources and Standup Text Generation

**Status:** Accepted
**Date:** 2026-04-16
**Author:** Mikhail Shchegolev

## Context

Saymo должен получать информацию о задачах и генерировать текст стендапа. Доступно несколько источников данных и подходов к генерации.

## Decision

### Три источника задач (speech.source в config.yaml):

**1. `confluence` (default)** — используется тот же JQL что и `update_confluence.py`:
```sql
-- Today: активные + закрытые за последний день
project = "{project_key}"
AND (status in ("In Progress", "Blocked", "Review")
     OR status changed from "In Progress" to Closed during (now(), -1d))
AND assignee in (currentUser(), {another_assignee})

-- Yesterday: обновлённые в предыдущий рабочий день
project = "{project_key}"
AND assignee = currentUser()
AND updated >= "YYYY-MM-DD" AND updated < "YYYY-MM-DD+1"
```

**2. `obsidian`** — читает daily note из Obsidian vault (`YYYY-MM-DD.md`)

**3. `jira`** — простой JQL `assignee = currentUser() AND updated >= -1d`

### Генерация текста (speech.composer):

**Ollama** (qwen2.5-coder:7b) с промптом оптимизированным для TTS:

Ключевые правила промпта (`config.prompts.standup_ru`):
- **Один абзац**, 2-4 предложения (не списки/пункты)
- Группировать похожие задачи (не перечислять каждую)
- Без номеров тикетов трекера
- Без длинных чисел и версий билдов
- IT-термины на русском с английским звучанием: смоук-тесты, стейдж, деплой, хотфикс
- Названия продуктов — как есть (пользователь сам перечисляет свой стек в `config.user.tech_stack`)

### Text Normalizer (post-processing перед TTS):
- Дефолтный набор аббревиатур → фонетика (generic IT/DevOps)
- Проект-специфичные термины добавляются через `config.vocabulary.abbreviations`
- Удаление build stamps (длинные цифровые стемпы)
- Удаление tracker ID (регексп `FOO-123:`)
- Числа → русские слова (только до 4 цифр)
- IT-термины → русская транскрипция (smoke → смоук)

## Consequences

**Positive:**
- `confluence` source повторяет логику существующего `update_confluence.py` — консистентность
- Промпт оптимизирован для устной речи — результат звучит естественно
- Text normalizer гарантирует корректное произношение аббревиатур

**Negative:**
- Ollama генерирует ~15с (vs ~2с у Claude API)
- `confluence` source зависит от JIRA connectivity
- Промпт иногда генерирует лишние фразы ("Надеюсь, это поможет") — нужна итерация

## Alternatives Considered

- **Claude API** (speech.composer=anthropic): лучше качество текста, но нет API ключа
- **Template-based** (без LLM): `"Вчера я работал над {task1}, {task2}"` — нет естественности
- **Confluence page parsing**: парсить HTML со страницы daily scrum — хрупко, зависит от формата

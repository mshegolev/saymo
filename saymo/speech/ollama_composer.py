"""Compose standup text using local Ollama LLM."""

import logging

import httpx

logger = logging.getLogger("saymo.speech.ollama")

STANDUP_PROMPT_RU = """\
Ты — помощник для стендап-митингов. Составь краткий устный отчёт на русском языке.

Вот мои заметки за вчера ({yesterday_date}):
---
{yesterday_notes}
---

Вот мои заметки на сегодня ({today_date}):
---
{today_notes}
---

ВАЖНЫЕ ПРАВИЛА:
- Напиши ОДИН сплошной абзац из 2-4 предложений. БЕЗ списков, БЕЗ нумерации, БЕЗ пунктов.
- Говори от первого лица: "Вчера я занимался...", "Сегодня планирую..."
- Объединяй похожие задачи в группы, не перечисляй каждую отдельно.
- НЕ используй номера тикетов (DATA-XXXXX) — только суть задачи.
- НЕ произноси длинные числа, версии билдов, таймстемпы.
- IT-термины пиши как произносятся по-русски с английским звучанием: смоук-тесты, стейдж, релиз, хотфикс, деплой, пайплайн, парсинг, ревью, фреймворк, автотесты.
- Названия продуктов и технологий оставляй как есть: NetSuite, OpenMetadata, FedRamp, Spark, Hive.
- Будь кратким — максимум 30 секунд при чтении вслух.
- Говори естественно, как будто рассказываешь коллеге.
- Если есть блокеры — упомяни одним предложением в конце.
- Не выдумывай то, чего нет в заметках.

Пример хорошего отчёта:
"Вчера я в основном занимался верификацией хотфиксов на стейдже и ревью автотестов. Сегодня продолжу работу над смоук-тестами для NetSuite и начну пи-оу-си по валидации данных в OpenMetadata. Пока есть проблема с доступностью NetSuite sandbox, это немного тормозит тестирование."
"""

STANDUP_PROMPT_EN = """\
You are a standup meeting assistant. Compose a brief verbal standup update in English.

Yesterday's notes ({yesterday_date}):
---
{yesterday_notes}
---

Today's notes ({today_date}):
---
{today_notes}
---

RULES:
- Write ONE short paragraph, 2-4 sentences. NO bullet points, NO numbered lists.
- First person: "Yesterday I worked on...", "Today I'm planning to..."
- Group similar tasks together, don't list each one separately.
- Do NOT mention ticket numbers (DATA-XXXXX).
- Do NOT read out long build numbers or timestamps.
- Keep it under 30 seconds when spoken aloud.
- Sound natural and conversational.
- Mention blockers briefly at the end if any.
- Don't invent things not in the notes.
"""


TEAM_SCRUM_PROMPT_RU = """\
Ты — помощник для скрам-митингов. Составь краткий отчёт по команде QA на русском языке.

Задачи команды за вчера ({yesterday_date}):
---
{yesterday_notes}
---

Задачи команды на сегодня ({today_date}):
---
{today_notes}
---

ВАЖНЫЕ ПРАВИЛА:
- ОБЯЗАТЕЛЬНО: про задачи Михаила говори от ПЕРВОГО лица: "Я работал...", "Я занимался...", "Я продолжу..."
- НИКОГДА не пиши "Михаил работал" — только "Я работал"
- Про Олега говори от третьего лица: "Олег работал над...", "Олег занимался..."
- По каждому человеку кратко: 1-2 предложения. Группируй задачи.
- НЕ используй номера тикетов и версии билдов.
- IT-термины на русском: смоук-тесты, стейдж, деплой, хотфикс, пайплайн, автотесты.
- Названия продуктов как есть: NetSuite, OpenMetadata, FedRamp.
- Если есть блокеры — упомяни в конце.
- Общая длительность — не больше 45 секунд при чтении вслух.
- БЕЗ списков и нумерации — сплошной текст.

Пример хорошего отчёта:
"По нашей команде: вчера я занимался верификацией хотфиксов на стейдже и ревью автотестов для FedRamp. Олег работал над смоук-тестами NS2 и тестированием нового пайплайна. Сегодня я продолжу работу над валидацией данных в OpenMetadata, а Олег займётся автоматизацией тестов для Customer 360. Из блокеров — периодическая недоступность NetSuite sandbox."
"""


async def compose_standup_ollama(
    notes: dict,
    model: str = "qwen2.5-coder:7b",
    ollama_url: str = "http://localhost:11434",
    language: str = "ru",
    prompt_override: str | None = None,
) -> str:
    """Compose standup text using local Ollama.

    Args:
        notes: Dict with 'today', 'yesterday', 'today_date', 'yesterday_date' keys.
        model: Ollama model name.
        ollama_url: Ollama API endpoint.
        language: 'ru' or 'en'.
    """
    yesterday_notes = notes.get("yesterday") or "(нет заметок)"
    today_notes = notes.get("today") or "(нет заметок)"
    yesterday_date = notes.get("yesterday_date", "вчера")
    today_date = notes.get("today_date", "сегодня")

    if prompt_override:
        template = prompt_override
    elif language == "ru":
        template = STANDUP_PROMPT_RU
    else:
        template = STANDUP_PROMPT_EN
    prompt = template.format(
        yesterday_notes=yesterday_notes,
        today_notes=today_notes,
        yesterday_date=yesterday_date,
        today_date=today_date,
    )

    logger.info(f"Composing standup with Ollama ({model})")

    async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 400,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    text = data.get("response", "").strip()
    logger.info(f"Composed standup: {len(text)} chars")
    return text


EXPAND_PROMPT_RU = """\
Тебе дали заметки. Перепиши их в естественную устную речь на русском языке.

Заметки:
---
{brief}
---

СТРОГИЕ ПРАВИЛА:
- Выведи ТОЛЬКО готовый текст речи. Никаких пояснений, заголовков, форматирования, маркдауна, списков, тире, нумерации.
- Говори от первого лица: "Я сегодня расскажу...", "Мы сделали..."
- IT-термины пиши как произносятся: деплой, пайплайн, ревью, автотесты, мерж-реквест.
- Числа пиши словами: "сто двадцать", "семьдесят пять процентов".
- Стиль — живой, разговорный, как будто выступаешь перед коллегами.
- Целевая длительность при чтении вслух: {duration} секунд.
- НЕ выдумывай то, чего нет в заметках. Только переформулируй и оформляй.
- Начинай сразу с текста речи, без вступлений вроде "Вот текст:" или "---".
"""


async def expand_brief(
    brief: str,
    duration: int = 30,
    model: str = "qwen2.5-coder:7b",
    ollama_url: str = "http://localhost:11434",
) -> str:
    """Expand a brief user summary into a full standup text.

    Args:
        brief: Short user notes (a few words/sentences).
        duration: Target speech duration in seconds.
        model: Ollama model name.
        ollama_url: Ollama API endpoint.

    Returns:
        Expanded standup text.
    """
    prompt = EXPAND_PROMPT_RU.format(brief=brief, duration=duration)
    logger.info(f"Expanding brief ({len(brief)} chars) to ~{duration}s with {model}")

    num_predict = max(200, duration * 8)  # ~8 tokens per second of speech

    async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": num_predict,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    text = data.get("response", "").strip()
    logger.info(f"Expanded brief: {len(text)} chars")
    return text


async def check_ollama_health(ollama_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0, proxy=None) as client:
            resp = await client.get(ollama_url)
            return resp.status_code == 200
    except Exception:
        return False

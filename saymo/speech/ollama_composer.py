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

Составь отчёт в формате:
1. Что было сделано вчера (кратко)
2. Что планируется на сегодня
3. Есть ли блокеры

Требования:
- Говори от первого лица ("Я сделал...", "Я работал над...")
- Будь кратким — максимум 45 секунд при чтении вслух
- Говори естественно, как на реальном стендапе
- Не выдумывай то, чего нет в заметках
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

Format:
1. What was done yesterday (brief)
2. What's planned for today
3. Any blockers

Requirements:
- First person ("I worked on...", "I completed...")
- Keep it under 45 seconds when spoken aloud
- Sound natural, like a real standup
- Don't invent things not in the notes
"""


async def compose_standup_ollama(
    notes: dict,
    model: str = "qwen2.5-coder:7b",
    ollama_url: str = "http://localhost:11434",
    language: str = "ru",
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

    template = STANDUP_PROMPT_RU if language == "ru" else STANDUP_PROMPT_EN
    prompt = template.format(
        yesterday_notes=yesterday_notes,
        today_notes=today_notes,
        yesterday_date=yesterday_date,
        today_date=today_date,
    )

    logger.info(f"Composing standup with Ollama ({model})")

    async with httpx.AsyncClient(timeout=120.0) as client:
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


async def check_ollama_health(ollama_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(ollama_url)
            return resp.status_code == 200
    except Exception:
        return False

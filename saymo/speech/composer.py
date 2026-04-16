"""Compose natural standup update text from JIRA data using Claude."""

import logging
import os

import anthropic

from saymo.config import SaymoConfig
from saymo.jira_source.tasks import StandupData

logger = logging.getLogger("saymo.speech.composer")

STANDUP_PROMPT_RU = """\
Ты — помощник для стендап-митингов. Составь краткий устный отчёт на русском языке.

Вот задачи из JIRA, над которыми я работал за последние 1-2 дня:

{tasks}

Составь отчёт в формате:
1. Что было сделано вчера/сегодня (кратко по каждой задаче)
2. Что планируется сделать сегодня
3. Есть ли блокеры (если из статусов задач видно проблемы)

Требования:
- Говори от первого лица ("Я сделал...", "Я работал над...")
- Будь кратким — максимум 45 секунд при чтении вслух
- Не упоминай номера задач (DATA-XXXX) — только суть
- Говори естественно, как на реальном стендапе
- Если задач мало, не выдумывай дополнительных
"""

STANDUP_PROMPT_EN = """\
You are a standup meeting assistant. Compose a brief verbal standup update in English.

Here are JIRA tasks I worked on in the last 1-2 days:

{tasks}

Format:
1. What was done yesterday/today (brief per task)
2. What's planned for today
3. Any blockers

Requirements:
- First person ("I worked on...", "I completed...")
- Keep it under 45 seconds when spoken aloud
- Don't mention ticket numbers — just the substance
- Sound natural, like a real standup
- Don't invent extra tasks
"""


async def compose_standup(
    standup_data: StandupData,
    config: SaymoConfig,
) -> str:
    """Use Claude to compose a natural standup update from JIRA tasks."""
    if not standup_data.tasks:
        return "У меня нет обновлений по задачам за вчера." if config.speech.language == "ru" else "No task updates from yesterday."

    tasks_text = "\n".join(standup_data.task_summary_lines)

    if config.speech.language == "ru":
        prompt = STANDUP_PROMPT_RU.format(tasks=tasks_text)
    else:
        prompt = STANDUP_PROMPT_EN.format(tasks=tasks_text)

    api_key = config.analysis.anthropic.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model = config.analysis.anthropic.model

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Set it in config.yaml or as environment variable."
        )

    client = anthropic.Anthropic(api_key=api_key)

    logger.info(f"Composing standup with {model} for {len(standup_data.tasks)} tasks")

    message = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    logger.info(f"Composed standup: {len(text)} chars")
    return text

"""Restore punctuation in raw dictation text using a local Ollama LLM.

The prompt templates are user-configurable via ``config.yaml`` under
``prompts.punctuate_ru`` / ``prompts.punctuate_en``, mirroring the other
composers. The constants here are generic defaults.
"""

import logging

import httpx

logger = logging.getLogger("saymo.speech.punctuator")


DEFAULT_PUNCTUATE_PROMPT_RU = """\
Ты исправляешь пунктуацию в распознанной речи (speech-to-text). Текст ниже
пришёл без знаков препинания, с маленьких букв и без регистра.

Правила:
- Верни ТОЛЬКО исправленный текст. Без вступлений, пояснений и кавычек.
- Расставь точки, запятые, вопросительные и восклицательные знаки по смыслу.
- Начни предложения с заглавной буквы; имена собственные с заглавной.
- Не меняй слова, не перефразируй, не переводи. Если слово не распознано,
  оставь его как есть.
- Не добавляй ничего от себя — только пунктуация и регистр.
- Если текст пустой, верни пустую строку.

Текст:
{text}
"""


DEFAULT_PUNCTUATE_PROMPT_EN = """\
You fix the punctuation in raw speech-to-text. The text below has no
punctuation and inconsistent capitalization.

Rules:
- Return ONLY the corrected text. No preamble, no commentary, no quotes.
- Add periods, commas, question and exclamation marks where the meaning
  requires them.
- Capitalize sentence starts and proper nouns.
- Do not change words, rephrase, or translate. Leave unrecognized words as-is.
- Add nothing on your own — punctuation and case only.
- If the text is empty, return an empty string.

Text:
{text}
"""


def _resolve_prompt(config, key: str, default: str) -> str:
    prompts = getattr(config, "prompts", None)
    if prompts is None and isinstance(config, dict):
        prompts = config.get("prompts")
    if isinstance(prompts, dict):
        override = prompts.get(key)
        if override:
            return override
    return default


async def punctuate_text(
    text: str,
    language: str = "auto",
    model: str = "qwen2.5-coder:7b",
    ollama_url: str = "http://localhost:11434",
    config=None,
) -> str:
    """Restore punctuation in a raw dictation fragment.

    Args:
        text: Raw speech-to-text output, likely punctuation-free.
        language: 'auto', 'ru', or 'en'. Auto picks the template from the
            script by character spread.
        model: Ollama model name.
        ollama_url: Ollama API endpoint.
        config: Optional config — loads ``config.prompts.punctuate_ru`` /
            ``punctuate_en`` before falling back to the built-in defaults.
    """
    import re

    text = text.strip()
    if not text:
        return ""

    lang = language
    if lang == "auto":
        letters = [c for c in text if c.isalpha()]
        if letters:
            cyrillic = sum(1 for c in letters if "\u0400" <= c <= "\u04ff")
            lang = "ru" if cyrillic / len(letters) > 0.3 else "en"
        else:
            lang = "en"

    if lang == "ru":
        template = _resolve_prompt(config, "punctuate_ru", DEFAULT_PUNCTUATE_PROMPT_RU)
    else:
        template = _resolve_prompt(config, "punctuate_en", DEFAULT_PUNCTUATE_PROMPT_EN)
    prompt = template.format(text=text)

    logger.info("Punctuating %d chars via Ollama (%s, %s)", len(text), model, lang)

    async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 400},
            },
        )
        response.raise_for_status()
        data = response.json()

    result = data.get("response", "").strip()
    logger.info("Punctuated: %d chars", len(result))
    return result
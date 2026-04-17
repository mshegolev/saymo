"""Text normalizer for TTS — expand abbreviations, numbers, and mixed-lang terms.

Default abbreviation map below covers generic IT/DevOps vocabulary. Project
or company-specific terms (internal pipelines, product codenames, etc.)
should be added via ``config.vocabulary.abbreviations`` rather than edited
here, so the source remains project-agnostic.
"""

import re

# Default abbreviation → pronunciation mapping (Russian phonetic).
# Covers generic IT / DevOps / QA vocabulary. For project-specific terms use
# ``config.vocabulary.abbreviations`` which is merged on top of this map.
ABBREV_MAP = {
    # Environments
    "UAT": "ю-эй-ти",
    "QA": "кью-эй",
    "CI": "си-ай",
    "CD": "си-ди",
    "CICD": "си-ай-си-ди",
    "CI/CD": "си-ай си-ди",
    # Tech terms
    "API": "эй-пи-ай",
    "SDK": "эс-ди-кей",
    "SQL": "эс-кью-эл",
    "ETL": "и-ти-эл",
    "DB": "ди-би",
    "HDFS": "эйч-ди-эф-эс",
    "JDBC": "джей-ди-би-си",
    "TTS": "ти-ти-эс",
    "STT": "эс-ти-ти",
    "LLM": "эл-эл-эм",
    "AI": "эй-ай",
    "ML": "эм-эл",
    "PR": "пи-ар",
    "MR": "эм-ар",
    "POC": "пи-оу-си",
    "PoC": "пи-оу-си",
    # Infrastructure
    "AWS": "эй-дабл-ю-эс",
    "GCP": "джи-си-пи",
    "VM": "ви-эм",
    "SSH": "эс-эс-эйч",
    "VPN": "ви-пи-эн",
    "DNS": "ди-эн-эс",
    "HTTP": "эйч-ти-ти-пи",
    "HTTPS": "эйч-ти-ти-пи-эс",
    "REST": "рест",
    "JSON": "джейсон",
    "YAML": "ямл",
    "XML": "икс-эм-эл",
    # Tools
    "JIRA": "джира",
    "GIT": "гит",
    "NPM": "эн-пи-эм",
    "Kafka": "кафка",
    "Spark": "спарк",
    "Hive": "хайв",
    "Parquet": "паркет",
    "Jenkins": "дженкинс",
    "Docker": "докер",
    "Kubernetes": "кубернетис",
    # IT/QA terms — Russian pronunciation with English flavor
    "smoke": "смоук",
    "stage": "стейдж",
    "deploy": "деплой",
    "release": "релиз",
    "hotfix": "хотфикс",
    "pipeline": "пайплайн",
    "review": "ревью",
    "framework": "фреймворк",
    "sandbox": "сэндбокс",
    "blocker": "блокер",
    "sprint": "спринт",
    "backlog": "бэклог",
    "merge": "мёрж",
    "branch": "бранч",
    "commit": "коммит",
    "rollback": "роллбэк",
    "debug": "дебаг",
    "refactoring": "рефакторинг",
    "autotests": "автотесты",
    "autotest": "автотест",
}

# Russian number words
ONES = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
         "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
TENS = ["", "десять", "двадцать", "тридцать", "сорок", "пятьдесят",
        "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот",
            "шестьсот", "семьсот", "восемьсот", "девятьсот"]


def _num_to_words_ru(n: int) -> str:
    """Convert integer to Russian words (0-9999)."""
    if n == 0:
        return "ноль"
    if n < 0:
        return "минус " + _num_to_words_ru(-n)

    parts = []
    if n >= 1000:
        thousands = n // 1000
        if thousands == 1:
            parts.append("тысяча")
        elif thousands in (2, 3, 4):
            parts.append(ONES[thousands])
            parts.append("тысячи")
        else:
            parts.append(ONES[thousands] if thousands < 10 else str(thousands))
            parts.append("тысяч")
        n %= 1000

    if n >= 100:
        parts.append(HUNDREDS[n // 100])
        n %= 100

    if 10 <= n <= 19:
        parts.append(TEENS[n - 10])
    else:
        if n >= 20:
            parts.append(TENS[n // 10])
            n %= 10
        if n > 0:
            parts.append(ONES[n])

    return " ".join(p for p in parts if p)


def _expand_version(match: re.Match) -> str:
    """Expand version numbers like 1.0.0 or 2.5.3."""
    parts = match.group(0).split(".")
    return " точка ".join(_num_to_words_ru(int(p)) for p in parts)


def _expand_number(match: re.Match) -> str:
    """Expand standalone numbers to Russian words."""
    num = int(match.group(0))
    if num > 9999:
        # For large numbers, read digits individually
        return " ".join(ONES[int(d)] if int(d) > 0 else "ноль" for d in match.group(0))
    return _num_to_words_ru(num)


def normalize_for_tts(text: str, extra_abbrevs: dict[str, str] | None = None) -> str:
    """Normalize text for TTS: expand abbreviations, numbers, versions.

    Args:
        text: Input text with abbreviations and numbers.
        extra_abbrevs: Additional abbreviation mappings to merge.

    Returns:
        Normalized text ready for TTS.
    """
    abbrevs = {**ABBREV_MAP}
    if extra_abbrevs:
        abbrevs.update(extra_abbrevs)

    # Sort by length (longest first) to avoid partial replacements
    sorted_keys = sorted(abbrevs.keys(), key=len, reverse=True)

    # Replace abbreviations (case-sensitive, whole word)
    for key in sorted_keys:
        # Word boundary matching
        pattern = re.compile(r'\b' + re.escape(key) + r'\b')
        text = pattern.sub(abbrevs[key], text)

    # Remove ETL build version stamps (e.g., v.2604101636, v2603261416)
    # These are Jenkins build IDs, not meaningful to pronounce
    text = re.sub(r'\bv\.?\d{8,}\b', '', text)

    # Remove standalone long numbers (8+ digits) — build IDs, timestamps
    text = re.sub(r'\b\d{8,}\b', '', text)

    # Remove tracker ticket numbers like `FOO-12345:` that are noise in speech
    text = re.sub(r'\b[A-Z][A-Z0-9]{1,9}-\d+\s*:?\s*', '', text)

    # Expand version numbers (e.g., 1.0.0, 2.5.3)
    text = re.sub(r'\b\d+\.\d+\.\d+\b', _expand_version, text)
    text = re.sub(r'\bv\.?\d+\.\d+\b', lambda m: _expand_version(m), text)

    # Expand standalone numbers (only short ones — up to 4 digits)
    text = re.sub(r'\b\d{1,4}\b', _expand_number, text)

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove markdown artifacts that TTS shouldn't read
    text = text.replace("---", "")
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)

    return text

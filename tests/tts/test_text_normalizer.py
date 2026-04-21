"""Tests for saymo.tts.text_normalizer."""

import pytest

from saymo.tts.text_normalizer import ABBREV_MAP, normalize_for_tts


# ---------------------------------------------------------------------------
# ABBREV_MAP content
# ---------------------------------------------------------------------------

def test_abbrev_map_is_non_empty():
    assert len(ABBREV_MAP) > 0


def test_abbrev_map_api():
    assert ABBREV_MAP["API"] == "эй-пи-ай"


def test_abbrev_map_etl():
    assert ABBREV_MAP["ETL"] == "и-ти-эл"


def test_abbrev_map_sql():
    assert ABBREV_MAP["SQL"] == "эс-кью-эл"


# ---------------------------------------------------------------------------
# Abbreviation replacement
# ---------------------------------------------------------------------------

def test_replaces_api_abbreviation():
    result = normalize_for_tts("Нужен API ключ")
    assert "эй-пи-ай" in result
    assert "API" not in result


def test_replaces_etl_abbreviation():
    result = normalize_for_tts("Запускаем ETL пайплайн")
    assert "и-ти-эл" in result
    assert "ETL" not in result


def test_replaces_cicd_before_ci():
    """Longer keys (CICD) must not be broken by shorter prefix (CI)."""
    result = normalize_for_tts("В CICD pipeline")
    assert "си-ай-си-ди" in result
    assert "CICD" not in result


def test_replaces_multiple_abbreviations():
    result = normalize_for_tts("API и SQL")
    assert "эй-пи-ай" in result
    assert "эс-кью-эл" in result


# ---------------------------------------------------------------------------
# Version stripping (long build IDs)
# ---------------------------------------------------------------------------

def test_strips_versioned_build_id_with_dot():
    """v.2604101636 is a Jenkins build stamp — should be removed."""
    result = normalize_for_tts("Деплой v.2604101636 прошёл")
    assert "2604101636" not in result


def test_strips_versioned_build_id_without_dot():
    result = normalize_for_tts("Билд v2603261416 завершён")
    assert "2603261416" not in result


def test_strips_bare_long_number():
    """Standalone 8+ digit numbers (timestamps, build IDs) are removed."""
    result = normalize_for_tts("ID задачи 20240415 сохранён")
    assert "20240415" not in result


# ---------------------------------------------------------------------------
# Version expansion (semantic versions)
# ---------------------------------------------------------------------------

def test_expands_three_part_version():
    result = normalize_for_tts("Версия 1.0.0")
    assert "один точка ноль точка ноль" in result


def test_expands_three_part_version_nonzero():
    result = normalize_for_tts("Вышла версия 2.5.3")
    assert "два точка пять точка три" in result


# ---------------------------------------------------------------------------
# Number expansion
# ---------------------------------------------------------------------------

def test_expands_single_digit():
    result = normalize_for_tts("Осталось 5 задач")
    assert "пять" in result
    assert "5" not in result


def test_expands_year():
    result = normalize_for_tts("Год 2024")
    # _num_to_words_ru uses ONES for thousands digit: 2 → "два"
    assert "тысячи двадцать четыре" in result
    assert "2024" not in result


def test_expands_two_digit_number():
    result = normalize_for_tts("Всего 42 коммита")
    assert "сорок два" in result


# ---------------------------------------------------------------------------
# Ticket stripping
# ---------------------------------------------------------------------------

def test_strips_ticket_with_colon():
    result = normalize_for_tts("DATA-12345: исправление бага")
    assert "DATA-12345" not in result
    assert "исправление бага" in result


def test_strips_ticket_without_colon():
    result = normalize_for_tts("Смотри TASK-999 в джире")
    assert "TASK-999" not in result


def test_strips_ticket_prefix_only():
    """Only the ticket token is removed; surrounding text survives."""
    result = normalize_for_tts("JIRA-1 готово")
    assert "готово" in result


# ---------------------------------------------------------------------------
# extra_abbrevs merging
# ---------------------------------------------------------------------------

def test_extra_abbrevs_are_applied():
    result = normalize_for_tts("Запуск NS2 пайплайна", extra_abbrevs={"NS2": "эн-эс-два"})
    assert "эн-эс-два" in result
    assert "NS2" not in result


def test_extra_abbrevs_override_default():
    """A key in extra_abbrevs shadows the same key in ABBREV_MAP."""
    custom = {"API": "эй-пи-ай-кастом"}
    result = normalize_for_tts("Вызов API", extra_abbrevs=custom)
    assert "эй-пи-ай-кастом" in result


def test_extra_abbrevs_none_does_not_crash():
    result = normalize_for_tts("Просто текст", extra_abbrevs=None)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Whitespace cleanup
# ---------------------------------------------------------------------------

def test_collapses_multiple_spaces():
    result = normalize_for_tts("слово   пробел")
    assert "  " not in result


def test_strips_leading_trailing_spaces():
    result = normalize_for_tts("  текст  ")
    assert result == result.strip()


# ---------------------------------------------------------------------------
# Markdown artifact removal
# ---------------------------------------------------------------------------

def test_removes_triple_dash():
    result = normalize_for_tts("Раздел --- конец")
    assert "---" not in result


def test_removes_double_asterisk():
    result = normalize_for_tts("**жирный** текст")
    assert "**" not in result


def test_removes_single_asterisk():
    result = normalize_for_tts("*курсив* текст")
    assert "*" not in result


def test_removes_heading_hash():
    result = normalize_for_tts("## Заголовок раздела")
    assert "#" not in result
    assert "Заголовок раздела" in result


def test_removes_list_dash_prefix():
    result = normalize_for_tts("- первый пункт")
    assert result.startswith("первый пункт")

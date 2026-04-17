# Voice Training — пошаговая инструкция

Обучение голосовой модели чтобы ответы на стендапе звучали максимально как ты сам.

## Что получим

| До (zero-shot) | После (fine-tuned) |
|---|---|
| MOS 3.5-3.8 | MOS 4.0-4.3 |
| Cosine similarity ~0.78 | Cosine similarity ~0.92 |
| Голос "похож" | Голос "это я" |

## Требования

- MacBook M1 Pro / M2 / M3, 16GB RAM
- ~30 минут на запись голоса
- ~2-3 часа на тренировку (можно оставить на ночь)
- Тихое помещение, гарнитура Plantronics или встроенный микрофон

---

## Step 1: Проверь окружение

```bash
# Проверь что Saymo работает
saymo test-devices

# Проверь текущий статус
saymo train-status
```

Убедись что микрофон виден (Plantronics или MacBook Pro Microphone).

Если `recording_device` не настроен в `config.yaml`, добавь:

```yaml
audio:
  recording_device: "Plantronics Blackwire 3220 Series"  # или "MacBook Pro Microphone"
```

## Step 2: Запись голоса (~30 минут)

```bash
saymo train-prepare
```

Что произойдёт:
1. На экране появится текст промпта (всего 100 штук)
2. Нажми **Enter** чтобы начать запись
3. **Прочитай текст вслух** естественным голосом — как обычно говоришь на стендапе
4. Запись остановится автоматически (макс 20 сек на промпт)
5. Нажми **s** чтобы пропустить промпт, **q** чтобы выйти

**Советы для лучшего качества:**
- Говори в своём обычном темпе, не ускоряй и не замедляй
- Не нужно идеально — естественность важнее
- Если сбился — нажми s и перейди к следующему
- Можно прервать по Ctrl+C и продолжить позже: `saymo train-prepare --resume`
- Для начала можно записать только стендап-промпты: `saymo train-prepare --category standup`

По окончании записи Saymo автоматически:
- Разобьёт записи на сегменты по 5-15 секунд
- Транскрибирует каждый сегмент через Whisper
- Проверит качество (SNR, клиппинг)
- Создаст `metadata.csv` для тренировки

Проверь результат:

```bash
saymo train-status
```

Нужно **минимум 50 сегментов** и **10+ минут** аудио. Если мало — дозапиши:

```bash
saymo train-prepare --resume --category qa
```

## Step 3: Тренировка модели (~2-3 часа)

```bash
saymo train-voice
```

Или с кастомными параметрами:

```bash
saymo train-voice --epochs 5 --batch-size 2
```

Что произойдёт:
- Загрузится базовая модель XTTS v2 (~2GB)
- Fine-tune только GPT decoder (~50M параметров из 467M)
- Audio encoder остаётся замороженным
- Авто-определение MPS (Apple Silicon GPU), fallback на CPU
- Прогресс-бар с loss по эпохам

**Можно оставить на ночь** — тренировка полностью автономная.

Если прервалось — продолжи:

```bash
saymo train-voice --resume
```

Если OOM (не хватает памяти):

```bash
saymo train-voice --batch-size 1
```

## Step 4: Оценка качества (~10 минут)

```bash
saymo train-eval
```

Что произойдёт:
1. Генерация 10 тестовых фраз **обеими** моделями (base и fine-tuned)
2. Воспроизведение пар [A] / [B] в **случайном порядке** (blind test)
3. Ты выбираешь: **a**, **b**, или **s** (same)
4. **r** — переиграть пару
5. Итоговый отчёт: % предпочтений + similarity score

Ожидаемый результат: fine-tuned preferred **> 70%** случаев.

## Step 5: Использование

**Ничего менять не нужно!** Saymo автоматически загружает fine-tuned модель:

```bash
# Всё работает как раньше, но голос теперь твой:
saymo prepare -p standup
saymo speak --glip
saymo auto -p standup
```

Чтобы временно вернуться на базовую модель (для сравнения):

```yaml
# config.yaml
tts:
  voice_training:
    use_finetuned: false
```

## Данные и файлы

```
~/.saymo/
├── training_dataset/
│   ├── raw/              # Исходные записи (100 файлов)
│   ├── wavs/             # Сегментированные клипы (5-15 сек)
│   ├── metadata.csv      # filename|транскрипция
│   └── eval/             # 10% holdout для валидации
└── models/
    └── xtts_finetuned/
        ├── best_model.pth    # Лучший чекпоинт (~500MB)
        ├── model.pth         # Финальный чекпоинт
        ├── config.json       # Конфигурация модели
        └── training_log.json # Loss curve, параметры
```

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| "No input devices found" | Подключи гарнитуру, проверь `saymo test-devices` |
| "Insufficient training data" | Дозапиши: `saymo train-prepare --resume` |
| OOM при тренировке | `saymo train-voice --batch-size 1` |
| Тренировка прервалась | `saymo train-voice --resume` |
| Голос не улучшился | Запиши больше данных (60+ мин), увеличь epochs до 10 |
| Хочу перетренировать | Удали `~/.saymo/models/xtts_finetuned/` и начни с Step 3 |

## Быстрый старт (TL;DR)

```bash
saymo train-prepare          # 30 мин — читаешь промпты вслух
saymo train-voice            # 2-3 часа — оставь на ночь
saymo train-eval             # 10 мин — слушаешь A/B
saymo prepare -p standup     # profit — голос теперь твой
```

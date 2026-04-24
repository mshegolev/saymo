# F5-TTS Voice Cloning — альтернатива XTTS+RVC

Одностадийный путь голосового клонирования: текст → твой голос за один проход модели, без второй ступени конверсии. Используется русский fine-tune `Misha24-10/F5-TTS_RUSSIAN` (~5K часов русского аудио, 100% разметка ударений).

## Когда выбирать F5-TTS вместо XTTS+RVC

| Если у тебя… | Лучше |
|---|---|
| Уже работает XTTS-only «похоже» и хочешь дотянуть | XTTS + RVC ([RVC-VOICE-CLONING.md](RVC-VOICE-CLONING.md)) |
| RVC даёт металлические артефакты или трещит | **F5-TTS (этот документ)** |
| Хочешь меньше движущихся частей в pipeline | **F5-TTS** |
| Нужно хорошее ударение в сложных русских словах | **F5-TTS** (особенно с `+о` ручной разметкой) |
| 16 GB RAM и хочешь что-то ещё легче | **F5-TTS** (1.6 GB модель vs RVC 53 MB + XTTS 2 GB) |

## Что получим

| Тип | MOS (по сообществу) | Latency / фразу | Setup |
|---|---|---|---|
| F5-TTS_RUSSIAN v1_Base_v2 | ~4.5 | 5-10 с на CPU | ~10 мин |
| XTTS+RVC (для сравнения) | ~4.3 после dotrain | 3-5 с | ~3-4 ч |

## Требования

- Apple Silicon (M1/M2/M3), 16 GB RAM
- Python 3.10+ (Saymo требует 3.12, F5-TTS работает с 3.10+)
- ~3 GB свободного места (модель ~1.6 GB + deps ~1 GB)
- Reference WAV в `~/.saymo/voice_samples/voice_sample.wav` (10-15 сек, чёткая речь)

## Step 1: Установка (~10 мин)

```bash
./scripts/install_f5tts.sh
```

Скрипт:
- Создаёт `~/F5TTS/.venv` (отдельный от Saymo, чтобы torch 2.11 / transformers 5.x не конфликтовали с Coqui TTS / mlx-audio)
- Устанавливает `f5-tts` через pip
- Скачивает `Misha24-10/F5TTS_v1_Base_v2` чекпоинт + vocab.txt в `~/F5TTS/models/ru/`
- Записывает пути в `~/.saymo/f5tts_model.txt` для удобной копи-паста

Идемпотентен — повторный запуск не перетянет уже скачанное.

Опции через env:
- `VARIANT=F5TTS_v1_Base_v4_winter` — другая ревизия модели
- `HF_REPO=user/repo` — свой fork

## Step 2: Подключить в Saymo

Возьми пути из `~/.saymo/f5tts_model.txt` и впиши в `~/.saymo/config.yaml`:

```yaml
tts:
  engine: f5tts_clone
  f5tts:
    ckpt_file: ~/F5TTS/models/ru/F5TTS_v1_Base_v2/<имя_файла>.pt
    vocab_file: ~/F5TTS/models/ru/F5TTS_v1_Base/vocab.txt
    nfe_step: 32          # 16 быстро, 32 баланс, 64 высокое качество
    speed: 1.0            # 0.8-1.2 для естественной речи
    device: cpu           # mps имеет регрессии в macOS 26 — стартуй с CPU
```

## Step 3: Записать референс

F5-TTS работает по reference audio, как и XTTS:

```bash
saymo record-voice -d 12     # 12 сек чистой речи в твой обычный микрофон
```

(Старый `voice_sample.wav` от XTTS подойдёт.)

**Опционально для лучшего качества:** создай sidecar `voice_sample.txt` с точной транскрипцией референса. F5-TTS использует его для выравнивания. Без файла используется generic фраза.

```bash
echo "Доброе утро коллеги, вчера занимался верификацией релиза CUSTOMER 360." \
  > ~/.saymo/voice_samples/voice_sample.txt
```

## Step 4: Тест

```bash
saymo test-tts "Любая фраза которую хочешь услышать."
```

Ожидаемый результат: голос звучит максимально похоже на твой собственный, без металлических артефактов RVC.

## Step 5: Боевое использование

```bash
saymo prepare -p standup
saymo speak --glip
```

В точности как с любым другим engine — Saymo сам подхватит F5-TTS из `tts.engine: f5tts_clone`.

## Тонкая настройка качества

| Параметр | Эффект | Рекомендация |
|---|---|---|
| `nfe_step` | Шагов денойзинга | 16 для real-time / Q&A; 32 дефолт; 64 для prepare-режима |
| `speed` | Темп речи | 0.95-1.05 для естественной интонации |
| `device` | Бэкенд | `cpu` всегда работает; `mps` быстрее но может крэшнуть на macOS 26 |
| Ручные ударения в gen_text | `молок+о`, `позвон+ит` — F5-TTS_RUSSIAN распознаёт `+` как маркер ударения |

Если темп речи отличается от твоего обычного — поменяй `speed`. F5-TTS не учит твой темп из reference (только тембр и общий характер интонаций).

## Troubleshooting

| Проблема | Решение |
|---|---|
| `f5-tts venv not found` | Запусти `./scripts/install_f5tts.sh` |
| `f5tts.ckpt_file is empty` | Заполни `tts.f5tts.ckpt_file` в config.yaml (путь из `~/.saymo/f5tts_model.txt`) |
| `MPS regression` / crashes | Поставь `device: cpu` в config |
| Голос звучит «не моим» | Проверь что reference `voice_sample.wav` чистый, peak >0.5; transcript в `voice_sample.txt` соответствует речи |
| Гнусавость / искажения | Уменьши `speed` до 0.95; увеличь `nfe_step` до 64 |
| Долгий syntheise (>10 c) | Уменьши `nfe_step` до 16; CPU всё равно медленный |

## Ссылки

- F5-TTS official: https://github.com/SWivid/F5-TTS
- Russian fine-tune: https://huggingface.co/Misha24-10/F5-TTS_RUSSIAN
- Демо/сравнения: https://misha24-10.github.io/

## Лицензия

F5-TTS базовая модель — CC-BY-NC 4.0 (некоммерческое использование). Для личного voice assistant'а — OK. Для коммерческого использования сверь условия с автором русского форка.

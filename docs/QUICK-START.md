# Quick Start — от нуля до твоего голоса в звонке

Один документ, чтобы поднять Saymo на чистом Mac за ~30 минут.

## Один шаг — мастер-сетап

```bash
cd /path/to/saymo
./setup.sh
```

Скрипт сам спросит на каждом шаге что делать:

1. **Saymo core** — uv venv, Ollama, Whisper, BlackHole (~5-15 мин)
2. **F5-TTS** — рекомендованный движок голосового клонирования (~10 мин)
3. **RVC** *(опционально)* — альтернативный двухстадийный pipeline (~30 мин)
4. **Wizard** — твоё имя, голос, аудио устройства

Если уже что-то стоит — пропустит. Можешь перезапускать без вреда.

## После сетапа: первый тест

```bash
saymo test-tts "Доброе утро коллеги, проверка голоса."
```

Должен сыграть в твои наушники (`monitor_device` из конфига). Если звук похож на тебя — всё работает.

## Перед стендапом

```bash
# 1. Сгенерировать текст ответа на основе профиля
saymo prepare -p standup

# 2. Слушать что получилось (опционально)
saymo review

# 3. В нужный момент звонка — отправить голосом в микрофон
saymo speak --glip      # для Glip / RingCentral Video
saymo speak --zoom      # для Zoom
saymo speak --meet      # для Google Meet
saymo speak --teams     # для MS Teams
```

## Слушать звонок и отвечать на «Михаил, что думаешь?»

```bash
saymo auto -p standup
```

Saymo слушает аудио из звонка, ловит твоё имя, генерирует ответ в реальном времени и отправляет голосом.

## Что у меня сломалось — куда смотреть

| Симптом | Доку |
|---|---|
| Голос не похож, звучит как другой человек | [VOICE-TRAINING.md](VOICE-TRAINING.md) — секция "Если voice не похож" |
| F5-TTS не работает / падает | [F5TTS-VOICE-CLONING.md](F5TTS-VOICE-CLONING.md) — Troubleshooting |
| RVC дает металлические артефакты | [RVC-VOICE-CLONING.md](RVC-VOICE-CLONING.md) — Тонкая настройка |
| BlackHole не виден / нет звука в звонке | [PRD.md](PRD.md) — раздел Audio routing |
| Wizard не запускается | `saymo --version`; если ошибка — `./install.sh` ещё раз |

## Структура проекта в 30 секунд

- `setup.sh` — мастер-сетап (этот файл всё устанавливает)
- `install.sh` — base Saymo install (внутри setup)
- `scripts/install_f5tts.sh` — F5-TTS отдельным venv (внутри setup)
- `scripts/install_rvc.sh` — Applio + RVC (внутри setup, опционально)
- `~/.saymo/config.yaml` — твой личный конфиг (создаётся wizard'ом)
- `~/.saymo/voice_samples/voice_sample.wav` — референс голоса для всех движков
- `~/F5TTS/`, `~/Applio/` — отдельные venv'ы для тяжёлых TTS моделей

## Сменить движок голоса

В `~/.saymo/config.yaml`:

```yaml
tts:
  engine: f5tts_clone        # дефолт — F5-TTS Russian
  # engine: xtts_rvc_clone   # альтернатива — XTTS+RVC
  # engine: coqui_clone      # XTTS-only без RVC
  # engine: macos_say        # системный голос (не клонирует)
```

Или через wizard:
```bash
saymo wizard
```

## Что дальше

- Прочитай [OVERVIEW.md](OVERVIEW.md) — общая архитектура
- Прочитай [VOICE-TRAINING.md](VOICE-TRAINING.md) — как сделать дотюн XTTS на своих 10 мин записи
- Если нужен максимум похожести — [F5TTS-VOICE-CLONING.md](F5TTS-VOICE-CLONING.md) с правильным reference
- Подключить новый источник задач (JIRA / Notion / Obsidian) — [PLUGINS.md](PLUGINS.md)

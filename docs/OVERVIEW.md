# Saymo Overview — что это и как устроено

Saymo — **локальный AI голосовой ассистент для macOS**. Говорит твоим голосом в любой звонок (Zoom / Meet / Glip / Teams), отвечает на вопросы из контекста, помогает на стендапах. Всё крутится на твоей машине — никаких облачных API.

## Зачем это

- **Стендапы** — сгенерировать текст из вчерашних задач (JIRA / Notion / Obsidian) и отдать голосом
- **«Михаил, что ты думаешь?»** — Saymo слышит твоё имя в звонке и отвечает за тебя из подготовленного контекста
- **Privacy** — переговоры не покидают машину, никаких ElevenLabs / OpenAI

## High-level pipeline

```
┌──────────────┐  ┌──────────────┐  ┌────────────────┐  ┌──────────────┐
│ Источник     │→→│ LLM композер │→→│ Text normalizer│→→│  TTS engine  │
│ (Jira/Notion)│  │   (Ollama)   │  │  (abbrevs,     │  │  (F5-TTS /   │
│              │  │              │  │   numbers)     │  │   XTTS+RVC)  │
└──────────────┘  └──────────────┘  └────────────────┘  └──────┬───────┘
                                                                │
┌──────────────┐  ┌──────────────┐  ┌────────────────┐         │
│Call provider │←←│ Auto trigger │←←│  STT (Whisper) │     audio bytes
│(mute/unmute) │  │(name detect) │  │ (capture call) │         │
└──────┬───────┘  └──────────────┘  └────────────────┘         │
       │                                                        │
       ▼                                                        ▼
  BlackHole 2ch ─────────────────────────────── Audio output + monitor
  (виртуальный мик)
```

## Стек целиком локальный

| Слой | Тула | Где живёт |
|---|---|---|
| LLM (генерация ответов) | Ollama | системный сервис, `localhost:11434` |
| STT (распознавание звонка) | faster-whisper | внутри saymo venv |
| TTS (синтез голоса) | F5-TTS Russian / Coqui XTTS / RVC | отдельные venv'ы (`~/F5TTS`, `~/Applio`) |
| Source plugins | JIRA / Notion / Obsidian / files | `saymo/plugins/` |
| Call automation | Chrome JS injection | `saymo/providers/<app>.py` |
| Audio routing | BlackHole virtual mic | системный аудио-драйвер |

## Голос — три уровня качества

См. подробнее в [QUICK-START.md](QUICK-START.md).

| Tier | Setup | Качество |
|---|---|---|
| Zero-shot XTTS | 5 мин | ~5/10 — узнаваемый, но «не я» |
| Fine-tuned XTTS | +2-3 ч | ~7-8/10 — близко |
| **F5-TTS Russian** *(default)* | 10 мин | **9-10/10** — практически не отличить |
| XTTS + RVC v2 | +30 мин | 9-10/10 — другая дорога к тому же результату |

## Как Saymo попадает в звонок

Через виртуальный микрофон **BlackHole**:

1. Звонок-аппа (Glip/Zoom/Meet/...) выбирает `BlackHole 2ch` как mic
2. Saymo TTS пишет аудио в `BlackHole 2ch`
3. Участники звонка слышат это как твой голос

Параллельно:
- `Multi-Output Device` (твои наушники + BlackHole 16ch) играет тот же поток
- Ты слышишь что говорит Saymo + других участников
- `BlackHole 16ch` отдаёт аудио звонка в Whisper для распознавания

## Триггеры — когда Saymo сам говорит

`saymo auto -p standup` — listen mode. Алгоритм:

1. faster-whisper транскрибирует аудио из звонка непрерывно
2. `TurnDetector` ищет совпадения с `config.user.name_variants` + fuzzy expansions
3. При совпадении — берёт следующее предложение как вопрос, отдаёт LLM на ответ
4. TTS синтезирует, BlackHole 2ch отправляет в звонок

Имена и варианты — в `~/.saymo/config.yaml`. Никакого хардкода в исходниках.

## Поддерживаемые звонок-аппы

Все через Chrome JS injection — мьют/анмьют, проверка mic device:

- Glip / RingCentral Video
- Zoom (browser)
- Google Meet
- MS Teams
- Telegram (web)
- Yandex Telemost
- VK Teams
- MTS Link

Для каждого свой провайдер в `saymo/providers/<app>.py`. Добавить новый — наследуйся от `MultiProviderBase`, реализуй `mute()`/`unmute()`/`switch_mic()`.

## Источники текста (plugins)

`saymo prepare -p <profile>` берёт текст из:

- **JIRA** — что назначено на тебя сегодня (`saymo/plugins/jira.py`)
- **Notion** — твоя дневник-страница (`saymo/plugins/notion.py`)
- **Obsidian vault** — markdown daily notes
- **Plain text file** — для тестов
- **No source** — пустой профиль, генерация чисто из промпта

Промпты живут в `saymo/speech/ollama_composer.py` как `DEFAULT_*_PROMPT_*` и переопределяются через `config.prompts.<key>`.

## Файлы и директории

```
saymo (репа)
├── saymo/                  ← Python пакет (CLI, audio, providers, plugins, tts/...)
├── scripts/install_*.sh    ← установщики каждого внешнего движка
├── docs/                   ← вся документация (этот файл, QUICK-START, etc.)
├── tests/                  ← pytest
├── install.sh              ← base Saymo install (uv + Ollama + BlackHole)
└── setup.sh                ← мастер-сетап, вызывает install.sh + установщики

~/.saymo/                   ← пользовательские данные (gitignore)
├── config.yaml             ← твой конфиг (имя, голос, источники, движок)
├── voice_samples/          ← reference WAV для cloning
├── training_dataset/       ← если делал fine-tune XTTS
├── models/                 ← fine-tuned XTTS, RVC модели
├── f5tts_model.txt         ← пути к F5-TTS модели (auto-generated)
└── logs/                   ← логи последних запусков

~/F5TTS/                    ← отдельный venv для F5-TTS
~/Applio/                   ← отдельный venv для RVC training/inference (если ставил)
```

Раздельные venv'ы потому что torch/transformers версии конфликтуют между Coqui TTS, mlx-audio, F5-TTS и RVC. Saymo вызывает их через subprocess.

## Безопасность и privacy

- Всё локально по умолчанию — ничего не уходит наружу без явной настройки
- Облачные провайдеры (Anthropic, Deepgram) — опциональные, в `config.example.yaml` отключены
- Голосовые сэмплы и `~/.saymo/config.yaml` в `.gitignore`
- Секреты через `${ENV_VAR}` интерполяцию — не попадают в git

См. [SECURITY.md](../SECURITY.md) для деталей и threat model.

## Куда дальше

- [QUICK-START.md](QUICK-START.md) — поднять с нуля
- [F5TTS-VOICE-CLONING.md](F5TTS-VOICE-CLONING.md) — детали F5-TTS
- [VOICE-TRAINING.md](VOICE-TRAINING.md) — fine-tune XTTS на своих записях
- [adr/](adr/) — почему такие архитектурные решения (8 ADR)
- [PRD.md](PRD.md) — продуктовые требования и roadmap

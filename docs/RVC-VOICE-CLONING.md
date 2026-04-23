# RVC Voice Cloning — поверх XTTS для финального уровня

Phase 2 голосового клонирования: XTTS делает «правильную интонацию + слова», RVC поверх превращает тембр в твой буквально. Это даёт перцептивный прирост ~30%, переводит «похоже» в «не отличить».

## Зачем RVC

XTTS-fine-tune обучает только GPT-decoder (прозодию и стиль). Speaker embedding замораживается и берётся из `voice_sample.wav` через encoder, который натренирован на тысячах английских голосов — для русского зрелого мужского тембра он попадает «приблизительно».

RVC v2 — это voice conversion поверх готового аудио: берёт любую речь (выход XTTS) и переподписывает тембр под твою модель, обученную исключительно на твоих 10 минутах. Тембр получается твой, прозодия и слова сохраняются от XTTS.

## Что получим

| Стадия | Subjective similarity | Latency / фразу |
|---|---|---|
| XTTS base (zero-shot) | ~5/10 | 2-3 с |
| XTTS fine-tuned + хороший voice_sample | ~7/10 | 2-3 с |
| **XTTS fine-tuned + RVC** | **9-10/10** | 3-5 с |

## Требования

- Apple Silicon, 16GB RAM
- Saymo установлен и работает (`saymo test-tts` синтезирует)
- Записанный датасет ≥10 мин в `~/.saymo/training_dataset/wavs/`
- ~5 GB свободного места (Applio + pretrained модели)
- ~1-2 ч свободного времени (установка + тренировка)

---

## Step 1: Установка (~30 мин)

```bash
./scripts/install_rvc.sh
```

Скрипт:
- Клонирует Applio в `~/Applio`
- Запускает Applio installer (создаёт свой venv, качает pretrained ~3-5 GB)
- Ставит `rvc-python` в Saymo venv через `uv add`
- Создаёт `~/.saymo/models/rvc/` для моделей

Идемпотентен — можно перезапускать, шаги пропускаются если уже выполнены.

## Step 2: Тренировка — два варианта

### Вариант A — Headless (рекомендуется)

Один скрипт, прогоняет preprocess → extract → train → index → копирует артефакты в `~/.saymo/models/rvc/`. Никакого UI.

```bash
./scripts/train_rvc.sh
# или с параметрами:
./scripts/train_rvc.sh --model-name myname --epochs 500 --batch-size 2
```

Дополнительные флаги: `--dataset PATH`, `--gpu ID` (`""` = CPU), `--sample-rate {32000|40000|48000}`. Полный список: `--help`. Можно переопределять и через env-переменные (`MODEL_NAME=...`, `EPOCHS=...`).

После `saymo train-voice` Saymo сам предложит запустить headless-тренировку RVC если Applio установлен и сессия интерактивная.

### Вариант B — Applio Web UI

Если хочешь видеть прогресс в браузере:

```bash
~/.saymo/run_applio.sh
```

Открой в браузере: `http://127.0.0.1:6969`

#### Шаги в UI (~30-60 мин)

#### 3.1 Preprocess Dataset (Tab "Train")
- **Dataset path**: `/Users/<you>/.saymo/training_dataset/wavs`
- **Model Name**: `myname_voice` (любое латиницей)
- **Sample rate**: `40000`
- Кнопка **Preprocess Dataset** → ~1-2 мин

#### 3.2 Extract Features
- **Pitch extractor**: `rmvpe` (best quality)
- **Hop length**: `128`
- **Embedder**: `contentvec`
- Кнопка **Extract Features** → ~3-5 мин на CPU/MPS

#### 3.3 Training
- **Total epochs**: `300` (хороший баланс для 10 мин датасета)
- **Batch size**: `4` (безопасно на 16 GB)
- **Save every epoch**: `25`
- **Pretrained**: оставь включённым
- **GPU**: `mps` если доступно, иначе `cpu`
- Кнопка **Start Training** → ~30-60 мин

#### 3.4 Где взять артефакты (только для UI-варианта)
После завершения в `~/Applio/logs/myname_voice/`:
- `myname_voice.pth` — модель (~50 MB)
- `added_*.index` или `myname_voice.index` — feature index (~10 MB)

Скопируй оба файла в `~/.saymo/models/rvc/`:
```bash
cp ~/Applio/logs/myname_voice/myname_voice.pth   ~/.saymo/models/rvc/
cp ~/Applio/logs/myname_voice/*.index            ~/.saymo/models/rvc/
```

(При headless-варианте `train_rvc.sh` копирует артефакты автоматически.)

## Step 4: Подключение в Saymo

Обнови `~/.saymo/config.yaml`:

```yaml
tts:
  engine: xtts_rvc_clone   # было coqui_clone
  rvc:
    model_path: ~/.saymo/models/rvc/myname_voice.pth
    index_path: ~/.saymo/models/rvc/myname_voice.index
    pitch_shift: 0          # 0 для своего голоса; +/-12 для перевода октав
    index_rate: 0.75        # 0.0-1.0, выше = больше похожесть, меньше артефактов
```

Проверь:
```bash
saymo test-tts "Доброе утро коллеги, вчера занимался верификацией релиза."
```

Ожидаемый результат: голос звучит максимально похоже на твой собственный.

## Step 5: Боевая проверка

```bash
saymo prepare -p standup
saymo speak --glip
```

Спроси у 1-2 коллег постфактум: «заметил странность в моём голосе?». Если нет — достигли 10/10.

## Тонкая настройка качества

| Параметр | Эффект | Рекомендация |
|---|---|---|
| `index_rate` | Похожесть тембра vs артефакты | 0.7-0.85 для чистой записи; 0.4-0.6 если в датасете шум |
| `pitch_shift` | Транспозиция в полутонах | 0 для своего голоса; -12 если RVC выдаёт высокий писк |
| Applio epochs | Качество модели | 300 хорошо; 500-600 если есть терпение и нет overfitting |

Если качество не дотягивает:
1. Проверь длительность датасета (`saymo train-status`) — RVC любит ≥15 мин
2. Перетренируй RVC с большим числом эпох (500)
3. Понизь `index_rate` до 0.6 если слышны артефакты

## Troubleshooting

| Проблема | Решение |
|---|---|
| Applio installer падает на fairseq | `pip install pip<24.1` перед запуском installer |
| `pyworld` build fails | `brew install cmake` |
| `mps` не появляется в списке GPU в Applio | Обнови PyTorch: внутри Applio venv `pip install -U torch torchaudio` |
| Latency >5 с на фразу | Уменьши `index_rate` до 0.5; либо отключи Index (`index_rate: 0`) |
| Голос «гнусавит» / металлический | Перетренируй с `pitch_extractor: rmvpe`; не используй `crepe` |

## Ссылки

- Applio: https://github.com/IAHispano/Applio
- rvc-python: https://pypi.org/project/rvc-python/
- RVC theory: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

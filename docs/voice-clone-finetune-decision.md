# Voice Clone Fine-Tune Decision

## Trigger

Start this track only if F5, Qwen3 Base, and CosyVoice fail the similarity gate.

## Preserved Assets

- `~/.saymo/training_dataset/`
- `~/.saymo/training_dataset_backup_20260422/`
- `~/.saymo/training_dataset_backup_bigdata_20260422/`
- `~/.saymo/voice_samples/`

## Candidate

GPT-SoVITS is the first fine-tune candidate. XTTS/RVC/Applio is not restored unless GPT-SoVITS is blocked.

## Gate

Fine-tune work starts only after a clean reference/dataset audit confirms the existing recordings are good enough.

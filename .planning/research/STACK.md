# v1.3 Research: Stack

## Scope

Milestone v1.3 adds optional local diarization for completed trigger-capture
sessions. Existing Saymo installs must keep working without diarization
packages, model downloads, or cloud services.

## Findings

- `pyannote.audio` is the primary candidate for a first backend because it is a
  Python speaker-diarization toolkit with pretrained pipelines and a common
  local inference path.
- WhisperX is useful as a reference architecture because it combines
  faster-whisper, alignment, and diarization, but Saymo should not replace its
  existing STT path just to get diarization.
- NVIDIA NeMo has diarization tooling, but it is a heavier candidate and better
  treated as a future advanced backend rather than the first adapter.
- Backend packages should be optional imports. `saymo` should expose
  availability diagnostics instead of failing at import time.
- Any backend that requires a token or model-license acceptance must read it
  from env/config and never from committed files.

## Recommended Stack Shape

- Add a backend-neutral `saymo.analysis.diarization` contract.
- Start with a disabled-by-default `pyannote` backend adapter.
- Store results as local JSON sidecars next to session ledgers rather than
  embedding backend-specific payloads into every sample.
- Keep `speaker` labels as `me`, `other`, `unknown`; store diarization speaker
  ids separately as suggestions.

## References

- https://github.com/pyannote/pyannote-audio
- https://github.com/m-bain/whisperX
- https://github.com/NVIDIA/NeMo

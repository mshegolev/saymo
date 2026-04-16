# ADR-002: Audio Routing via BlackHole Virtual Audio Devices

**Status:** Accepted
**Date:** 2026-04-16
**Author:** Mikhail Shchegolev

## Context

Saymo должен:
1. **Говорить в Glip** — другие участники слышат TTS-аудио как голос из микрофона
2. **Слушать Glip** — захватывать аудио других участников для распознавания имени
3. **Мониторить** — пользователь слышит что Saymo говорит

RingCentral Video работает в Chrome и использует стандартные аудио-устройства macOS.

## Decision

Используются два виртуальных аудио-устройства **BlackHole** (open-source):

```
BlackHole 2ch  → виртуальный микрофон (Saymo TTS → Glip)
BlackHole 16ch → захват аудио участников (Glip → Saymo STT)
```

### Полная схема маршрутизации:

```
Saymo TTS output → BlackHole 2ch ──→ RingCentral mic input (участники слышат)
                 → Plantronics ────→ Наушники (пользователь слышит себя)

RingCentral speaker output → Multi-Output Device → Plantronics (пользователь слышит участников)
                                                 → BlackHole 16ch (Saymo слушает для триггера)
```

### Конфигурация macOS:
- **Multi-Output Device** (Audio MIDI Setup): Plantronics (master) + BlackHole 16ch (drift correction)
- **RingCentral Audio Settings**: Microphone = BlackHole 2ch, Speakers = Multi-Output Device
- **Saymo config.yaml**: playback = BlackHole 2ch, monitor = Plantronics, capture = BlackHole 16ch

### Автоматическое переключение:
Saymo переключает микрофон в RingCentral через **JavaScript injection** в Chrome (AppleScript → Chrome → execute JS → click DOM elements).

## Consequences

**Positive:**
- Два отдельных BlackHole устройства исключают **feedback loop** (Saymo не слышит сам себя)
- Multi-Output Device обеспечивает одновременный мониторинг и захват
- Автоматическое переключение микрофона — пользователю не нужно кликать вручную

**Negative:**
- Требует ручной настройки Multi-Output Device в Audio MIDI Setup (один раз)
- JavaScript injection зависит от DOM-структуры RingCentral Video (может сломаться при обновлении UI)
- Требует `View → Developer → Allow JavaScript from Apple Events` в Chrome

## Alternatives Considered

- **Одно устройство BlackHole**: feedback loop — Saymo слышит свой TTS и повторно тригерится
- **ScreenCaptureKit**: захват аудио приложения напрямую — сложная настройка, только macOS 13+
- **Loopback (Rogue Amoeba)**: коммерческий ($99), но более удобный UI для маршрутизации

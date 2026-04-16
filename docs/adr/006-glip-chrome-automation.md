# ADR-006: RingCentral Video Automation via Chrome AppleScript

**Status:** Accepted
**Date:** 2026-04-16
**Author:** Mikhail Shchegolev

## Context

RingCentral Video работает в Chrome на `v.ringcentral.com/conf/...`. Для автоматического выступления Saymo должен:
1. Переключить микрофон на BlackHole 2ch
2. Нажать Space (unmute)
3. Дождаться окончания воспроизведения
4. Нажать Space (mute)
5. Вернуться в предыдущее приложение

## Decision

### Трёхуровневая автоматизация:

**1. Tab Detection (AppleScript → Chrome)**
```applescript
tell application "Google Chrome"
    -- iterate windows/tabs, find URL containing "v.ringcentral.com/conf"
end tell
```

**2. Mic Switch (AppleScript → Chrome → JavaScript Injection)**
```javascript
// Click "Audio menu" button (aria-label="Audio menu")
// Find li[role="radio"] containing "BlackHole 2ch" in first half of list (Microphone section)
// Click it
```

DOM-структура RingCentral Video:
- `button[aria-label="Audio menu"]` — dropdown кнопка
- `li[role="radio"]` — список устройств, первая половина = Microphone, вторая = Speakers
- CSS class `media-buttons__opt--selected` — текущий выбор

**3. Mute Toggle (AppleScript → System Events)**
```applescript
tell application "System Events"
    keystroke " "  -- Space key
end tell
```

### Полный flow `unmute_speak_mute()`:
1. Запомнить текущее приложение (`get_previous_app()`)
2. Активировать Chrome + Glip вкладку
3. Переключить mic на BlackHole 2ch (JS injection)
4. Нажать Space (unmute)
5. Воспроизвести аудио (BlackHole 2ch + Plantronics monitor)
6. Нажать Space (mute)
7. Вернуться в предыдущее приложение

### Требования к Chrome:
- `View → Developer → Allow JavaScript from Apple Events` — включается через AppleScript автоматически

## Consequences

**Positive:**
- Полностью автоматический flow — одна команда или trigger
- Пользователь не трогает мышку/клавиатуру во время speak
- Возврат в исходное приложение (iTerm2 / VS Code)

**Negative:**
- Зависимость от DOM-структуры RingCentral Video — может сломаться при обновлении
- JavaScript injection требует разового разрешения в Chrome
- AppleScript keystroke Space работает только когда Chrome в фокусе
- Задержка ~2-3с на переключение приложений + клики

## Alternatives Considered

- **Keyboard shortcut**: ⌘+Shift+S как глобальный hotkey → проще, но не переключает mic
- **RingCentral API**: программный mute/unmute → требует OAuth, сложная настройка
- **Virtual keyboard driver**: эмуляция клавиш без фокуса → требует kernel extension

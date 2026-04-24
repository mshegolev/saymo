"""Tests for saymo.tts.factory — engine dispatch and realtime override."""

import pytest

from saymo.config import SaymoConfig
from saymo.tts.factory import (
    UnsupportedTTSEngine,
    get_tts_engine,
    is_known_engine,
)


# ---------------------------------------------------------------------------
# is_known_engine
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "coqui_clone", "qwen3_clone", "piper", "macos_say",
])
def test_known_engines(name):
    assert is_known_engine(name) is True


@pytest.mark.parametrize("name", ["", "unknown", "xtts", "gtts", "openai", "elevenlabs"])
def test_unknown_engines(name):
    assert is_known_engine(name) is False


# ---------------------------------------------------------------------------
# get_tts_engine — dispatch
# ---------------------------------------------------------------------------

def test_macos_say_engine_instantiates():
    config = SaymoConfig()
    config.tts.engine = "macos_say"
    from saymo.tts.macos_say import MacOSSay
    engine = get_tts_engine(config)
    assert isinstance(engine, MacOSSay)


def test_unknown_engine_raises():
    config = SaymoConfig()
    config.tts.engine = "imaginary"
    with pytest.raises(UnsupportedTTSEngine, match="Unknown TTS engine"):
        get_tts_engine(config)


def test_elevenlabs_now_unknown():
    """elevenlabs was removed — no longer a known engine, raises Unknown."""
    config = SaymoConfig()
    config.tts.engine = "elevenlabs"
    with pytest.raises(UnsupportedTTSEngine, match="Unknown TTS engine"):
        get_tts_engine(config)


def test_openai_now_unknown():
    """openai was removed — no longer a known engine, raises Unknown."""
    config = SaymoConfig()
    config.tts.engine = "openai"
    with pytest.raises(UnsupportedTTSEngine, match="Unknown TTS engine"):
        get_tts_engine(config)


# ---------------------------------------------------------------------------
# realtime override
# ---------------------------------------------------------------------------

def test_realtime_override_kicks_in_when_set():
    config = SaymoConfig()
    config.tts.engine = "piper"          # slow, high-quality (prepare-time)
    config.tts.realtime_engine = "macos_say"  # fast fallback (auto-mode)

    from saymo.tts.macos_say import MacOSSay
    engine = get_tts_engine(config, realtime=True)
    assert isinstance(engine, MacOSSay)


def test_realtime_override_ignored_when_flag_false():
    """Without realtime=True, realtime_engine is ignored."""
    config = SaymoConfig()
    config.tts.engine = "macos_say"
    config.tts.realtime_engine = "piper"  # would fail (no piper model)

    # engine path — should pick macos_say and not even look at realtime_engine
    from saymo.tts.macos_say import MacOSSay
    engine = get_tts_engine(config)  # realtime=False default
    assert isinstance(engine, MacOSSay)


def test_realtime_override_empty_falls_back_to_engine():
    config = SaymoConfig()
    config.tts.engine = "macos_say"
    config.tts.realtime_engine = ""  # empty — fall back

    from saymo.tts.macos_say import MacOSSay
    engine = get_tts_engine(config, realtime=True)
    assert isinstance(engine, MacOSSay)

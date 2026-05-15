import textwrap

from saymo.config import load_config, resolve_live_tuning


def test_live_tuning_loads_defaults_and_profile_overrides(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            live:
              chunk_seconds: 3.5
              overlap_seconds: 1.5
              trigger_cooldown_seconds: 20
              silence_rms_threshold: 0.002
            meetings:
              daily:
                provider: glip
                trigger_phrases: ["John"]
                live:
                  chunk_seconds: 2.0
                  pre_speak_delay_seconds: 0.5
            """
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))
    global_tuning = resolve_live_tuning(config)
    daily_tuning = resolve_live_tuning(config, config.get_meeting("daily"))

    assert global_tuning.chunk_seconds == 3.5
    assert global_tuning.overlap_seconds == 1.5
    assert global_tuning.trigger_cooldown_seconds == 20.0
    assert global_tuning.silence_rms_threshold == 0.002

    assert daily_tuning.chunk_seconds == 2.0
    assert daily_tuning.overlap_seconds == 1.5
    assert daily_tuning.trigger_cooldown_seconds == 20.0
    assert daily_tuning.pre_speak_delay_seconds == 0.5

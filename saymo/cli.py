"""Compatibility shim. Real implementation lives in saymo.commands."""

from saymo.commands import (
    console,
    main,
    run_async,
    _get_cached_audio_path,
    _load_cached_summary,
    _looks_like_question,
    _play_cached_audio,
    _resolve_auto_response,
    _rotate_audio_cache,
)

__all__ = [
    "main",
    "_looks_like_question",
    "_resolve_auto_response",
]


if __name__ == "__main__":
    main()

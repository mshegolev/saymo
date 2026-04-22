#!/usr/bin/env python3
"""End-to-end smoke test for the auto-mode Q&A pipeline without a live call.

Feeds a transcript string (or set of strings) through the full Q&A
resolution pipeline and reports which branch fired — cache hit,
classifier hit, live fallback, or standup fallback. Useful for:

- Verifying ``saymo prepare-responses`` populated the cache correctly
- Debugging why a specific question isn't matching (keyword vs intent)
- Regression-testing the resolver after editing the response library

Usage
-----

Single transcript:

    scripts/test_qa_pipeline.py "какой у тебя статус по задаче?"

Batch (one transcript per line):

    scripts/test_qa_pipeline.py --file scripts/qa_samples.txt

With intent classifier enabled:

    scripts/test_qa_pipeline.py --classifier "когда сдашь?"

With live Ollama fallback:

    scripts/test_qa_pipeline.py --live "расскажи что нового"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saymo.commands import _resolve_auto_response  # noqa: E402
from saymo.config import load_config  # noqa: E402


SAMPLE_TRANSCRIPTS = [
    # Questions the default response library should match via keywords
    "какой у тебя статус?",
    "как дела по задаче?",
    "есть блокеры?",
    "когда будет готово?",
    "ты это закончил?",
    # Rephrasings — classifier should help here
    "когда же ты это сдашь",
    "движется ли работа",
    # Non-questions — should fall through to standup audio
    "Миша, выйди на связь",
    "привет всем",
]


async def run_one(config, transcript, response_cache, standup_summary, fallback):
    """Run one transcript through _resolve_auto_response and report the branch."""
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Transcript: {transcript}")
    result = await _resolve_auto_response(
        config, transcript, response_cache, standup_summary, fallback
    )
    if result == fallback:
        print(f"  → standup fallback ({fallback.name})")
    else:
        print(f"  → cached response: {result.name}")
        if result.exists() and result.stat().st_size > 0:
            kb = result.stat().st_size // 1024
            print(f"    ({kb} KB)")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcripts", nargs="*",
                        help="Transcripts to test (omit to use the built-in samples)")
    parser.add_argument("--file", help="Read one transcript per line from a file")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--classifier", action="store_true",
                        help="Force responses.intent_classifier=True for this run")
    parser.add_argument("--live", action="store_true",
                        help="Force responses.live_fallback=True for this run")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.classifier:
        config.responses.intent_classifier = True
    if args.live:
        config.responses.live_fallback = True

    # Collect transcripts
    transcripts = list(args.transcripts)
    if args.file:
        transcripts.extend([
            line.strip()
            for line in Path(args.file).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ])
    if not transcripts:
        transcripts = SAMPLE_TRANSCRIPTS

    # Init response cache (may be empty if prepare-responses wasn't run)
    response_cache = None
    if config.responses.enabled:
        from saymo.analysis.response_cache import ResponseCache, build_library
        cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None
        response_cache = ResponseCache(
            library=build_library(config.responses.library),
            cache_dir=cache_dir,
            confidence_threshold=config.responses.confidence_threshold,
        )

        # Warn about empty cache dir
        cache_path = response_cache.cache_dir
        wavs = list(cache_path.glob("*.wav")) if cache_path.exists() else []
        if not wavs:
            print(f"⚠  No cached WAVs in {cache_path}")
            print(f"   Run 'saymo prepare-responses' first for meaningful results.")

    # Dummy fallback path — must exist for the resolver to "return" it
    fallback = Path("/tmp/saymo-test-standup.wav")
    fallback.write_bytes(b"")

    standup_summary = "Вчера закрыл ticket-1234, сегодня работаю над ticket-5678."

    print(f"Config:")
    print(f"  tts.engine             = {config.tts.engine}")
    print(f"  tts.realtime_engine    = {config.tts.realtime_engine or '(falls back to engine)'}")
    print(f"  responses.enabled      = {config.responses.enabled}")
    print(f"  responses.live_fallback = {config.responses.live_fallback}")
    print(f"  responses.intent_classifier = {config.responses.intent_classifier}")
    if response_cache:
        print(f"  library                = {len(response_cache.library)} intents")

    for t in transcripts:
        await run_one(config, t, response_cache, standup_summary, fallback)

    fallback.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())

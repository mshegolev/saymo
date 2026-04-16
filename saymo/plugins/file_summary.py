"""File summary source — read a plain text/markdown file and speak it.

Use when you already have a prepared summary text.
Set speech.source to "file" and speech.summary_file to the path.
"""

from pathlib import Path


class FileSummarySource:
    name = "file"
    description = "Read pre-written summary from a text file"

    async def fetch(self, config) -> dict | None:
        # Check for summary_file in speech config or default location
        summary_path = getattr(config.speech, "summary_file", "")
        if not summary_path:
            # Default: ~/.saymo/summary.md
            summary_path = str(Path.home() / ".saymo" / "summary.md")

        path = Path(summary_path)
        if not path.exists():
            return None

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return None

        return {
            "yesterday": text,
            "today": None,
            "yesterday_date": "",
            "today_date": "",
        }

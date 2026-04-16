"""Plugin system — auto-discovers source plugins from this directory.

To create a plugin, add a .py file here with a class inheriting SourcePlugin:

    # saymo/plugins/my_source.py
    from saymo.plugins.base import SourcePlugin

    class MySource(SourcePlugin):
        name = "my_source"
        description = "Fetch tasks from My System"

        async def fetch(self, config) -> dict:
            return {
                "yesterday": "task list...",
                "today": "planned tasks...",
                "yesterday_date": "2026-04-17",
                "today_date": "2026-04-18",
            }
"""

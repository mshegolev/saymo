"""Structured logging setup with rich console output."""

import logging

from rich.console import Console
from rich.logging import RichHandler

console = Console()

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure logging with rich handler."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
        force=True,
    )
    logger = logging.getLogger("saymo")
    logger.setLevel(level)
    return logger


def get_logger(name: str = "saymo") -> logging.Logger:
    return logging.getLogger(name)

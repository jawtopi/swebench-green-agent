"""Utility functions."""

import time
from pathlib import Path

from .logger import logger


def save_log(content: str, log_path: Path) -> None:
    """
    Save content to a log file.

    Args:
        content: Log content
        log_path: Path to save log file
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(content)
        logger.info(f"Log saved to: {log_path}")
    except Exception as e:
        logger.error(f"Failed to save log: {str(e)}")


def get_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)

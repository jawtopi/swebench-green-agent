"""Sandbox management for isolated test execution."""

import shutil
from pathlib import Path
from typing import Optional

from src.core.config import RUNS_DIR, LOGS_DIR
from src.core.logger import logger


class Sandbox:
    """Manages isolated execution environments for test runs."""

    def __init__(self, task_id: str, run_id: Optional[str] = None):
        """
        Initialize a sandbox for a task.

        Args:
            task_id: Task identifier
            run_id: Optional run identifier (defaults to task_id)
        """
        self.task_id = task_id
        self.run_id = run_id or task_id
        self.sandbox_dir = RUNS_DIR / self.run_id

    def create(self) -> Path:
        """
        Create a fresh sandbox directory.

        Returns:
            Path to the sandbox directory
        """
        # Clean existing sandbox if present
        if self.sandbox_dir.exists():
            logger.info(f"Cleaning existing sandbox: {self.sandbox_dir}")
            shutil.rmtree(self.sandbox_dir)

        # Create new sandbox
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created sandbox: {self.sandbox_dir}")

        return self.sandbox_dir

    def cleanup(self) -> None:
        """Remove the sandbox directory."""
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
            logger.info(f"Cleaned up sandbox: {self.sandbox_dir}")

    def get_working_dir(self) -> Path:
        """
        Get the working directory path within the sandbox.

        Returns:
            Path to working directory
        """
        return self.sandbox_dir

    @staticmethod
    def reset_all() -> list[str]:
        """
        Reset all sandboxes and logs.

        Returns:
            List of directories that were cleaned
        """
        cleaned = []

        # Clean runs directory
        if RUNS_DIR.exists():
            for item in RUNS_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    cleaned.append(str(item))
            logger.info(f"Cleaned runs directory: {RUNS_DIR}")

        # Clean logs directory
        if LOGS_DIR.exists():
            for item in LOGS_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                    cleaned.append(str(item))
            logger.info(f"Cleaned logs directory: {LOGS_DIR}")

        return cleaned

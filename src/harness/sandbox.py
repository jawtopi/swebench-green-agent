"""
Sandbox management for isolated test execution.

Provides environment isolation for SWE-bench evaluations:
- Local sandboxes: File system isolation for demo mode
- Docker sandboxes: Container-based isolation for real SWE-bench (via swebench harness)

The green agent should run tests in an isolated environment to:
1. Prevent interference between evaluations
2. Ensure reproducibility
3. Protect the host system
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from src.core.config import RUNS_DIR, LOGS_DIR, SWEBENCH_DOCKER_NAMESPACE
from src.core.logger import logger


@dataclass
class EnvironmentStatus:
    """Status of the execution environment."""

    docker_available: bool
    docker_version: Optional[str]
    swebench_images_available: bool
    sandbox_dir: Path
    ready: bool
    message: str


class Sandbox:
    """
    Manages isolated execution environments for test runs.

    For demo mode: Uses local file system isolation
    For SWE-bench mode: Uses Docker containers via the swebench harness
    """

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
        self._docker_checked = False
        self._docker_available = False

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

        # Create new sandbox with proper structure
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        (self.sandbox_dir / "logs").mkdir(exist_ok=True)
        (self.sandbox_dir / "testbed").mkdir(exist_ok=True)
        (self.sandbox_dir / "patches").mkdir(exist_ok=True)

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

    def get_testbed_dir(self) -> Path:
        """
        Get the testbed directory for repository checkout.

        Returns:
            Path to testbed directory
        """
        return self.sandbox_dir / "testbed"

    def get_logs_dir(self) -> Path:
        """
        Get the logs directory within the sandbox.

        Returns:
            Path to logs directory
        """
        return self.sandbox_dir / "logs"

    def check_environment(self) -> EnvironmentStatus:
        """
        Check if the execution environment is ready.

        Verifies:
        - Docker availability (for SWE-bench mode)
        - SWE-bench Docker images
        - Sandbox directory access

        Returns:
            EnvironmentStatus with details about the environment
        """
        docker_available, docker_version = self._check_docker()
        swebench_images = self._check_swebench_images() if docker_available else False

        ready = True
        messages = []

        if not self.sandbox_dir.parent.exists():
            ready = False
            messages.append(f"Runs directory does not exist: {RUNS_DIR}")

        if not docker_available:
            messages.append("Docker is not available - SWE-bench mode will not work")
        elif not swebench_images:
            messages.append(f"SWE-bench images not found in namespace: {SWEBENCH_DOCKER_NAMESPACE}")

        return EnvironmentStatus(
            docker_available=docker_available,
            docker_version=docker_version,
            swebench_images_available=swebench_images,
            sandbox_dir=self.sandbox_dir,
            ready=ready,
            message="; ".join(messages) if messages else "Environment ready",
        )

    def _check_docker(self) -> Tuple[bool, Optional[str]]:
        """Check if Docker is available and running."""
        if self._docker_checked:
            return self._docker_available, None

        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self._docker_available = True
                self._docker_checked = True
                logger.debug(f"Docker available: {version}")
                return True, version

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        self._docker_available = False
        self._docker_checked = True
        return False, None

    def _check_swebench_images(self) -> bool:
        """Check if SWE-bench Docker images are available."""
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                images = result.stdout.strip().split("\n")
                # Check for any swebench images
                swebench_images = [img for img in images if SWEBENCH_DOCKER_NAMESPACE in img]
                return len(swebench_images) > 0

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False

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

    @staticmethod
    def check_docker_available() -> Tuple[bool, str]:
        """
        Static method to check Docker availability.

        Returns:
            Tuple of (available: bool, message: str)
        """
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "Docker is available and running"
            else:
                return False, f"Docker error: {result.stderr.strip()}"

        except FileNotFoundError:
            return False, "Docker is not installed"
        except subprocess.TimeoutExpired:
            return False, "Docker check timed out - daemon may not be running"
        except Exception as e:
            return False, f"Error checking Docker: {e}"

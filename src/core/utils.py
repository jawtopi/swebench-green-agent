"""Utility functions for git operations and file handling."""

import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional

from .logger import logger


def apply_patch(patch_path: Path, working_dir: Path) -> Tuple[bool, str]:
    """
    Apply a git patch to a repository.

    Args:
        patch_path: Path to the patch file
        working_dir: Working directory (git repo root)

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        # Check if patch file exists
        if not patch_path.exists():
            return False, f"Patch file not found: {patch_path}"

        # Run git apply
        result = subprocess.run(
            ["git", "apply", "--verbose", str(patch_path)],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        if result.returncode == 0:
            logger.info(f"Patch applied successfully: {patch_path}")
            return True, output
        else:
            logger.error(f"Failed to apply patch: {output}")
            return False, output

    except subprocess.TimeoutExpired:
        error_msg = "Patch application timed out"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error applying patch: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def run_command(
    cmd: list[str],
    working_dir: Path,
    timeout: int = 300,
) -> Tuple[int, str, str]:
    """
    Run a shell command and capture output.

    Args:
        cmd: Command and arguments as list
        working_dir: Working directory
        timeout: Timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        return -1, "", str(e)


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


def format_log_content(
    task_id: str,
    patch_choice: str,
    apply_success: bool,
    apply_output: str,
    test_output: str,
    verdict: str,
    tests_passed: int,
    total_tests: int,
) -> str:
    """
    Format execution log content.

    Args:
        task_id: Task identifier
        patch_choice: Patch choice (good/bad)
        apply_success: Whether patch applied successfully
        apply_output: Output from patch application
        test_output: Output from test execution
        verdict: Final verdict
        tests_passed: Number of tests passed
        total_tests: Total number of tests

    Returns:
        Formatted log content
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    log_parts = [
        "=" * 80,
        f"SWE-Bench Green Agent Evaluation Log",
        "=" * 80,
        f"Task ID: {task_id}",
        f"Patch: {patch_choice}",
        f"Timestamp: {timestamp}",
        "",
        "-" * 80,
        "PATCH APPLICATION",
        "-" * 80,
        f"Status: {'SUCCESS' if apply_success else 'FAILED'}",
        "",
        apply_output,
        "",
        "-" * 80,
        "TEST EXECUTION",
        "-" * 80,
        test_output,
        "",
        "-" * 80,
        "RESULTS",
        "-" * 80,
        f"Verdict: {verdict}",
        f"Tests Passed: {tests_passed}/{total_tests}",
        "=" * 80,
    ]

    return "\n".join(log_parts)


def get_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)

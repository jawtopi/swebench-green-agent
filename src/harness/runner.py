"""Test harness runner for SWE-Bench evaluation."""

import time
from pathlib import Path
from typing import Tuple, Dict, Any

from src.core.config import DEMO_TASKS, TASKS_DIR, LOGS_DIR
from src.core.logger import logger
from src.core.utils import apply_patch, save_log, format_log_content, get_timestamp_ms
from .sandbox import Sandbox


class TestRunner:
    """Runs SWE-Bench tests in an isolated sandbox."""

    def __init__(self, task_id: str, patch_choice: str):
        """
        Initialize test runner.

        Args:
            task_id: Task identifier (e.g., 'numpy-1234')
            patch_choice: Which patch to use ('good' or 'bad')
        """
        self.task_id = task_id
        self.patch_choice = patch_choice
        self.sandbox = Sandbox(task_id, f"{task_id}-{patch_choice}")

        # Validate task exists
        if task_id not in DEMO_TASKS:
            raise ValueError(f"Unknown task: {task_id}. Available: {list(DEMO_TASKS.keys())}")

        self.task_config = DEMO_TASKS[task_id]

    def run(self) -> Dict[str, Any]:
        """
        Execute the test harness for this task.

        Returns:
            Dictionary with test results
        """
        start_time = get_timestamp_ms()
        logger.info(f"Starting evaluation for {self.task_id} with {self.patch_choice} patch")

        try:
            # Create sandbox
            sandbox_dir = self.sandbox.create()

            # Get patch path
            patch_path = TASKS_DIR / self.task_id / f"{self.patch_choice}.patch"

            # Apply patch
            apply_success, apply_output = self._apply_patch(patch_path, sandbox_dir)

            if not apply_success:
                # Patch failed to apply
                result = self._create_result(
                    verdict="FAIL",
                    tests_passed=0,
                    total_tests=self.task_config["total_tests"],
                    failure_type="apply_error",
                    runtime_ms=get_timestamp_ms() - start_time,
                )

                # Save log
                log_content = format_log_content(
                    task_id=self.task_id,
                    patch_choice=self.patch_choice,
                    apply_success=False,
                    apply_output=apply_output,
                    test_output="Tests not run (patch failed to apply)",
                    verdict="FAIL",
                    tests_passed=0,
                    total_tests=self.task_config["total_tests"],
                )
                self._save_log(log_content, result["logs_uri"])

                return result

            # Run tests (stubbed for demo)
            test_output, tests_passed, total_tests = self._run_tests()

            # Determine verdict
            verdict = "PASS" if tests_passed == total_tests else "FAIL"
            failure_type = "test_failure" if verdict == "FAIL" else None

            runtime_ms = get_timestamp_ms() - start_time

            result = self._create_result(
                verdict=verdict,
                tests_passed=tests_passed,
                total_tests=total_tests,
                failure_type=failure_type,
                runtime_ms=runtime_ms,
            )

            # Save log
            log_content = format_log_content(
                task_id=self.task_id,
                patch_choice=self.patch_choice,
                apply_success=True,
                apply_output=apply_output,
                test_output=test_output,
                verdict=verdict,
                tests_passed=tests_passed,
                total_tests=total_tests,
            )
            self._save_log(log_content, result["logs_uri"])

            logger.info(f"Evaluation complete: {verdict} ({tests_passed}/{total_tests} tests passed)")

            return result

        except Exception as e:
            logger.error(f"Error during test execution: {str(e)}")
            runtime_ms = get_timestamp_ms() - start_time

            return self._create_result(
                verdict="FAIL",
                tests_passed=0,
                total_tests=self.task_config["total_tests"],
                failure_type="test_failure",
                runtime_ms=runtime_ms,
            )

    def _apply_patch(self, patch_path: Path, working_dir: Path) -> Tuple[bool, str]:
        """
        Apply the patch to the sandbox.

        Args:
            patch_path: Path to patch file
            working_dir: Sandbox working directory

        Returns:
            Tuple of (success, output)
        """
        # For demo purposes, simulate patch application
        # In a real implementation, this would use git apply
        if not patch_path.exists():
            return False, f"Patch file not found: {patch_path}"

        # Read patch content to verify it exists
        try:
            patch_content = patch_path.read_text()
            logger.info(f"Patch file loaded: {len(patch_content)} bytes")

            # Simulate git apply output
            if self.patch_choice == "bad" and self.task_id == "django-5678":
                # Simulate apply failure for bad django patch
                return False, "error: patch failed: models.py:42\nerror: models.py: patch does not apply"

            return True, f"Applied patch successfully to {working_dir}"

        except Exception as e:
            return False, f"Error reading patch: {str(e)}"

    def _run_tests(self) -> Tuple[str, int, int]:
        """
        Run test suite (stubbed for demo).

        Returns:
            Tuple of (output, tests_passed, total_tests)
        """
        total_tests = self.task_config["total_tests"]

        # Simulate test execution based on task config
        if self.patch_choice == "good":
            tests_passed = self.task_config["good_pass"]
        else:
            tests_passed = self.task_config["bad_pass"]

        # Simulate test output
        time.sleep(0.1)  # Simulate test execution time

        test_output_lines = [
            f"Running test suite for {self.task_id}...",
            f"Repository: {self.task_config['repo']}",
            "",
        ]

        # Generate mock test results
        for i in range(1, total_tests + 1):
            if i <= tests_passed:
                test_output_lines.append(f"test_{i:02d} ... PASSED")
            else:
                test_output_lines.append(f"test_{i:02d} ... FAILED")

        test_output_lines.extend([
            "",
            f"Results: {tests_passed} passed, {total_tests - tests_passed} failed, {total_tests} total",
        ])

        test_output = "\n".join(test_output_lines)

        return test_output, tests_passed, total_tests

    def _create_result(
        self,
        verdict: str,
        tests_passed: int,
        total_tests: int,
        failure_type: str | None,
        runtime_ms: int,
    ) -> Dict[str, Any]:
        """
        Create result dictionary.

        Args:
            verdict: Test verdict
            tests_passed: Number of tests passed
            total_tests: Total number of tests
            failure_type: Type of failure (if any)
            runtime_ms: Runtime in milliseconds

        Returns:
            Result dictionary
        """
        log_name = f"{self.task_id}-{self.patch_choice}.txt"

        return {
            "task_id": self.task_id,
            "tests_passed": tests_passed,
            "total_tests": total_tests,
            "verdict": verdict,
            "runtime_ms": runtime_ms,
            "failure_type": failure_type,
            "logs_uri": f"/logs/{log_name}",
        }

    def _save_log(self, content: str, logs_uri: str) -> None:
        """
        Save log content to file.

        Args:
            content: Log content
            logs_uri: Log URI (e.g., '/logs/task-id.txt')
        """
        # Extract filename from URI
        filename = logs_uri.split("/")[-1]
        log_path = LOGS_DIR / filename
        save_log(content, log_path)

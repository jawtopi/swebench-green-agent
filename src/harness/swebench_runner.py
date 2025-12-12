"""
Real SWE-bench evaluation harness runner.

This module provides the integration with the official SWE-bench harness
to evaluate code patches against real test suites.

Supports two execution modes:
1. Direct API: Uses swebench.harness.run_evaluation functions directly
2. Subprocess: Falls back to `python -m swebench.harness.run_evaluation`
"""

import json
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from src.core.config import (
    RUNS_DIR,
    LOGS_DIR,
    SWEBENCH_TIMEOUT_SECONDS,
    SWEBENCH_DATASET_SPLIT,
    SWEBENCH_DOCKER_NAMESPACE,
    SWEBENCH_CACHE_DIR,
)
from src.core.logger import logger
from src.core.utils import get_timestamp_ms

# Try to import swebench directly
try:
    from swebench.harness.run_evaluation import (
        run_instances,
        get_dataset_from_preds,
        make_test_spec,
    )
    SWEBENCH_AVAILABLE = True
except ImportError:
    SWEBENCH_AVAILABLE = False
    logger.warning("swebench not installed - will use subprocess fallback")


@dataclass
class SwebenchResult:
    """
    Result from a SWE-bench evaluation run.

    SWE-bench evaluates patches by running tests before and after applying the patch:
    - FAIL_TO_PASS: Tests that were failing and now pass (the fix worked)
    - PASS_TO_PASS: Tests that were passing and still pass (no regressions)
    - FAIL_TO_FAIL: Tests that were failing and still fail (fix incomplete)
    - PASS_TO_FAIL: Tests that were passing and now fail (regression!)

    A patch is considered successful (PASS) if:
    - All FAIL_TO_PASS tests now pass (the bug is fixed)
    - All PASS_TO_PASS tests still pass (no regressions introduced)

    Attributes:
        task_id: The SWE-bench task identifier (e.g., 'django__django-11099')
        verdict: Overall result - 'PASS' if resolved, 'FAIL' otherwise
        tests_passed: Number of tests that passed after patch
        total_tests: Total number of tests run
        failure_type: Type of failure if verdict is FAIL
        runtime_ms: Execution time in milliseconds
        logs_text: Raw logs from the evaluation (stdout + stderr)
        fail_to_pass: Tests that should go from failing to passing (count that succeeded)
        pass_to_pass: Tests that should remain passing (count that succeeded)
        resolved: Whether the instance was fully resolved
    """

    task_id: str
    verdict: Literal["PASS", "FAIL"]
    tests_passed: int
    total_tests: int
    failure_type: Optional[Literal["apply_error", "build_error", "test_failure", "unknown"]]
    runtime_ms: int
    logs_text: str
    # Before/after test tracking
    fail_to_pass: int = 0  # Tests that went from FAIL -> PASS (the fix)
    fail_to_pass_total: int = 0  # Total expected FAIL -> PASS tests
    pass_to_pass: int = 0  # Tests that stayed PASS -> PASS (no regression)
    pass_to_pass_total: int = 0  # Total expected PASS -> PASS tests
    resolved: bool = False  # True if all FAIL_TO_PASS and PASS_TO_PASS succeeded


def run_swebench_task(task_id: str, patch_diff: str, dataset_split: Optional[str] = None) -> SwebenchResult:
    """
    Run SWE-bench evaluation for a single task with a given patch.

    This function:
    1. Creates a temporary working directory
    2. Writes the patch to a predictions file
    3. Invokes the SWE-bench harness (API or subprocess)
    4. Parses the results and returns a SwebenchResult

    Args:
        task_id: The SWE-bench instance ID (e.g., 'django__django-11099')
        patch_diff: The unified diff patch content to apply
        dataset_split: Optional override for dataset split (defaults to config)

    Returns:
        SwebenchResult with evaluation results

    Raises:
        Exception: If the harness cannot be invoked (not installed, etc.)
    """
    start_time = get_timestamp_ms()
    split = dataset_split or SWEBENCH_DATASET_SPLIT

    # Create unique run directory
    run_id = f"{task_id}-{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting SWE-bench evaluation for {task_id} in {run_dir}")

    logs_parts = [
        "=" * 80,
        f"SWE-bench Evaluation: {task_id}",
        f"Dataset split: {split}",
        f"Run ID: {run_id}",
        f"SWE-bench API available: {SWEBENCH_AVAILABLE}",
        "=" * 80,
        "",
    ]

    try:
        # Step 1: Create predictions dict for SWE-bench harness
        # swebench v4.1.0 expects predictions as a dict keyed by instance_id
        predictions = {
            task_id: {
                "instance_id": task_id,
                "model_patch": patch_diff,
                "model_name_or_path": "green-agent",
            }
        }
        # Also save as a list for the subprocess fallback (traditional format)
        predictions_list = [predictions[task_id]]
        predictions_file = run_dir / "predictions.json"
        predictions_file.write_text(json.dumps(predictions_list, indent=2))
        logs_parts.append(f"Created predictions file: {predictions_file}")
        logs_parts.append(f"Patch length: {len(patch_diff)} bytes")
        logs_parts.append("")

        # Step 2: Invoke the SWE-bench harness
        if SWEBENCH_AVAILABLE:
            logs_parts.append("Using SWE-bench Python API...")
            result = _invoke_swebench_api(
                predictions=predictions,
                run_dir=run_dir,
                task_id=task_id,
                run_id=run_id,
                split=split,
                logs_parts=logs_parts,
            )
        else:
            logs_parts.append("Using subprocess fallback...")
            result = _invoke_swebench_subprocess(
                predictions_file=predictions_file,
                run_dir=run_dir,
                task_id=task_id,
                split=split,
                logs_parts=logs_parts,
            )

        runtime_ms = get_timestamp_ms() - start_time
        result.runtime_ms = runtime_ms

        logs_parts.append("")
        logs_parts.append("-" * 80)
        logs_parts.append("FINAL RESULT")
        logs_parts.append("-" * 80)
        logs_parts.append(f"Verdict: {result.verdict}")
        logs_parts.append(f"Tests: {result.tests_passed}/{result.total_tests}")
        logs_parts.append(f"Runtime: {runtime_ms}ms")
        if result.failure_type:
            logs_parts.append(f"Failure type: {result.failure_type}")
        logs_parts.append("=" * 80)

        result.logs_text = "\n".join(logs_parts)
        return result

    except FileNotFoundError as e:
        # SWE-bench not installed
        runtime_ms = get_timestamp_ms() - start_time
        error_msg = f"SWE-bench harness not found: {e}"
        logger.error(error_msg)
        logs_parts.append(f"ERROR: {error_msg}")
        logs_parts.append("")
        logs_parts.append("Please install SWE-bench:")
        logs_parts.append("  pip install swebench")
        logs_parts.append("  # or")
        logs_parts.append("  git clone https://github.com/princeton-nlp/SWE-bench.git")
        logs_parts.append("  pip install -e SWE-bench")

        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=0,
            total_tests=0,
            failure_type="unknown",
            runtime_ms=runtime_ms,
            logs_text="\n".join(logs_parts),
        )

    except Exception as e:
        runtime_ms = get_timestamp_ms() - start_time
        error_msg = f"Unexpected error during evaluation: {e}"
        logger.error(error_msg)
        logs_parts.append(f"ERROR: {error_msg}")

        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=0,
            total_tests=0,
            failure_type="unknown",
            runtime_ms=runtime_ms,
            logs_text="\n".join(logs_parts),
        )


def _invoke_swebench_api(
    predictions: dict,
    run_dir: Path,
    task_id: str,
    run_id: str,
    split: str,
    logs_parts: list[str],
) -> SwebenchResult:
    """
    Invoke SWE-bench harness using the Python API directly.

    This is more reliable than subprocess as it runs in-process.

    Args:
        predictions: Dict of predictions keyed by instance_id
        run_dir: Working directory for this run
        task_id: The task instance ID
        run_id: Unique run identifier
        split: Dataset split to use
        logs_parts: List to append log lines to

    Returns:
        SwebenchResult with parsed results
    """
    logs_parts.append("-" * 80)
    logs_parts.append("INVOKING SWE-BENCH API")
    logs_parts.append("-" * 80)

    try:
        # Build dataset name and determine actual split
        # SWE-bench datasets only have 'dev' and 'test' splits
        # The config name (lite/verified/full) is part of the dataset name, not the split
        actual_split = "test"  # Default to test split

        if split.lower() == "lite":
            dataset_name = "princeton-nlp/SWE-bench_Lite"
        elif split.lower() == "verified":
            dataset_name = "princeton-nlp/SWE-bench_Verified"
        elif split.lower() in ("full", "test"):
            dataset_name = "princeton-nlp/SWE-bench"
        elif split.lower() == "dev":
            dataset_name = "princeton-nlp/SWE-bench_Lite"
            actual_split = "dev"
        else:
            dataset_name = "princeton-nlp/SWE-bench_Lite"

        logs_parts.append(f"Dataset: {dataset_name}")
        logs_parts.append(f"Split: {actual_split}")
        logs_parts.append(f"Run ID: {run_id}")

        # Get the dataset entries that match our predictions
        # swebench v4.1.0 API signature:
        # get_dataset_from_preds(dataset_name, split, instance_ids, predictions, run_id, rewrite_reports, exclude_completed)
        dataset = get_dataset_from_preds(
            dataset_name=dataset_name,
            split=actual_split,
            instance_ids=[task_id],
            predictions=predictions,
            run_id=run_id,
            rewrite_reports=False,
            exclude_completed=False,  # Run even if already evaluated
        )
        logs_parts.append(f"Found {len(dataset)} matching instances")

        if not dataset:
            logs_parts.append(f"ERROR: Task {task_id} not found in {dataset_name}")
            return SwebenchResult(
                task_id=task_id,
                verdict="FAIL",
                tests_passed=0,
                total_tests=0,
                failure_type="unknown",
                runtime_ms=0,
                logs_text="",
            )

        logs_parts.append(f"Running evaluation with timeout={SWEBENCH_TIMEOUT_SECONDS}s...")
        logs_parts.append(f"Docker namespace: {SWEBENCH_DOCKER_NAMESPACE}")

        # run_instances API (swebench v4.1.0):
        # run_instances(predictions, instances, cache_level, clean, force_rebuild,
        #               max_workers, run_id, timeout, namespace, ...)
        results = run_instances(
            predictions=predictions,
            instances=dataset,
            cache_level="instance",
            clean=False,
            force_rebuild=False,
            max_workers=1,
            run_id=run_id,
            timeout=SWEBENCH_TIMEOUT_SECONDS,
            namespace=SWEBENCH_DOCKER_NAMESPACE if SWEBENCH_DOCKER_NAMESPACE else None,
        )

        logs_parts.append(f"Evaluation complete. Results: {results}")

        # Parse the results for our task
        return _parse_api_results(task_id, results, run_dir, run_id, logs_parts)

    except Exception as e:
        import traceback
        logs_parts.append(f"API Error: {str(e)}")
        logs_parts.append(f"Traceback: {traceback.format_exc()}")
        # Fall back to unknown failure
        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=0,
            total_tests=0,
            failure_type="unknown",
            runtime_ms=0,
            logs_text="",
        )


def _parse_api_results(
    task_id: str,
    results: dict,
    run_dir: Path,
    run_id: str,
    logs_parts: list[str],
) -> SwebenchResult:
    """
    Parse results from the SWE-bench API.

    Extracts before/after test information:
    - FAIL_TO_PASS: Tests that were failing before patch and pass after
    - PASS_TO_PASS: Tests that were passing before and still pass after
    """
    logs_parts.append("-" * 80)
    logs_parts.append("PARSING API RESULTS")
    logs_parts.append("-" * 80)

    # Default values
    resolved = False
    fail_to_pass = 0
    fail_to_pass_total = 0
    pass_to_pass = 0
    pass_to_pass_total = 0

    # Check if our task is in results from run_instances
    # run_instances returns: {instance_id: {"completed": bool, "resolved": bool}} or None
    if results is None:
        logs_parts.append("run_instances returned None - checking for report files")
        results = {}

    if task_id in results:
        result = results[task_id]
        resolved = result.get("resolved", False)
        completed = result.get("completed", False)
        logs_parts.append(f"Task {task_id} completed: {completed}, resolved: {resolved}")

    # SWE-bench stores detailed reports at:
    # logs/run_evaluation/{run_id}/{model_name_or_path}/{instance_id}/report.json
    # Try multiple possible report locations
    report_paths = [
        # Standard swebench location
        Path("logs/run_evaluation") / run_id / "green-agent" / task_id / "report.json",
        # Fallback locations
        run_dir / "logs" / "report.json",
        run_dir / "logs" / task_id / "report.json",
    ]

    for report_file in report_paths:
        if report_file.exists():
            logs_parts.append(f"Found report file: {report_file}")
            try:
                report = json.loads(report_file.read_text())
                logs_parts.append(f"Report content keys: {list(report.keys())}")

                # Handle both formats: report might have task_id as key, or contain the data directly
                entry = report.get(task_id, report)
                resolved = entry.get("resolved", resolved)

                # Extract test counts from report
                # Try both 'tests' and 'tests_status' keys (different swebench versions use different keys)
                tests_data = entry.get("tests_status", entry.get("tests", {}))
                fail_to_pass_data = tests_data.get("FAIL_TO_PASS", {})
                pass_to_pass_data = tests_data.get("PASS_TO_PASS", {})

                if isinstance(fail_to_pass_data, dict):
                    fail_to_pass = len(fail_to_pass_data.get("success", []))
                    fail_to_pass_total = fail_to_pass + len(fail_to_pass_data.get("failure", []))
                if isinstance(pass_to_pass_data, dict):
                    pass_to_pass = len(pass_to_pass_data.get("success", []))
                    pass_to_pass_total = pass_to_pass + len(pass_to_pass_data.get("failure", []))

                logs_parts.append(f"From report: resolved={resolved}")
                logs_parts.append(f"  FAIL_TO_PASS: {fail_to_pass}/{fail_to_pass_total}")
                logs_parts.append(f"  PASS_TO_PASS: {pass_to_pass}/{pass_to_pass_total}")

                total_tests = fail_to_pass_total + pass_to_pass_total
                tests_passed = fail_to_pass + pass_to_pass

                return SwebenchResult(
                    task_id=task_id,
                    verdict="PASS" if resolved else "FAIL",
                    tests_passed=tests_passed,
                    total_tests=total_tests,
                    failure_type=None if resolved else "test_failure",
                    runtime_ms=0,
                    logs_text="",
                    fail_to_pass=fail_to_pass,
                    fail_to_pass_total=fail_to_pass_total,
                    pass_to_pass=pass_to_pass,
                    pass_to_pass_total=pass_to_pass_total,
                    resolved=resolved,
                )
            except Exception as e:
                logs_parts.append(f"Error reading report {report_file}: {e}")

    # If we have a result from run_instances but no detailed report
    if task_id in results:
        logs_parts.append("Using basic result from run_instances (no detailed report found)")
        return SwebenchResult(
            task_id=task_id,
            verdict="PASS" if resolved else "FAIL",
            tests_passed=1 if resolved else 0,
            total_tests=1,
            failure_type=None if resolved else "test_failure",
            runtime_ms=0,
            logs_text="",
            resolved=resolved,
        )

    logs_parts.append("Could not determine result from API response")
    return SwebenchResult(
        task_id=task_id,
        verdict="FAIL",
        tests_passed=0,
        total_tests=0,
        failure_type="unknown",
        runtime_ms=0,
        logs_text="",
    )


def _invoke_swebench_subprocess(
    predictions_file: Path,
    run_dir: Path,
    task_id: str,
    split: str,
    logs_parts: list[str],
) -> SwebenchResult:
    """
    Invoke the SWE-bench harness via subprocess (fallback).

    Uses `python -m swebench.harness.run_evaluation` to run evaluation.

    Args:
        predictions_file: Path to predictions JSON file
        run_dir: Working directory for this run
        task_id: The task instance ID
        split: Dataset split to use
        logs_parts: List to append log lines to

    Returns:
        SwebenchResult with parsed results
    """
    # Build the command
    cmd = [
        "python", "-m", "swebench.harness.run_evaluation",
        "--predictions_path", str(predictions_file),
        "--swe_bench_tasks", f"princeton-nlp/SWE-bench_{split.capitalize()}",
        "--log_dir", str(run_dir / "logs"),
        "--testbed", str(run_dir / "testbed"),
        "--skip_existing",
        "--timeout", str(SWEBENCH_TIMEOUT_SECONDS),
        "--verbose",
    ]

    # Add instance filter to only run our single task
    cmd.extend(["--instance_ids", task_id])

    logs_parts.append("-" * 80)
    logs_parts.append("INVOKING SWE-BENCH HARNESS")
    logs_parts.append("-" * 80)
    logs_parts.append(f"Command: {' '.join(cmd)}")
    logs_parts.append("")

    logger.info(f"Running SWE-bench harness: {' '.join(cmd[:6])}...")

    try:
        # Run the harness
        result = subprocess.run(
            cmd,
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=SWEBENCH_TIMEOUT_SECONDS + 60,  # Extra buffer
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )

        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode

        logs_parts.append("STDOUT:")
        logs_parts.append(stdout if stdout else "(empty)")
        logs_parts.append("")
        logs_parts.append("STDERR:")
        logs_parts.append(stderr if stderr else "(empty)")
        logs_parts.append("")
        logs_parts.append(f"Return code: {returncode}")

        # Parse the results
        return _parse_harness_output(
            task_id=task_id,
            run_dir=run_dir,
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            logs_parts=logs_parts,
        )

    except subprocess.TimeoutExpired:
        logs_parts.append(f"TIMEOUT: Process exceeded {SWEBENCH_TIMEOUT_SECONDS + 60}s")
        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=0,
            total_tests=0,
            failure_type="unknown",
            runtime_ms=0,
            logs_text="",
        )


def _parse_harness_output(
    task_id: str,
    run_dir: Path,
    stdout: str,
    stderr: str,
    returncode: int,
    logs_parts: list[str],
) -> SwebenchResult:
    """
    Parse the output from the SWE-bench harness to extract results.

    The harness writes results to a JSON file and also outputs to stdout.
    We try multiple parsing strategies:
    1. Read the results JSON file
    2. Parse stdout for test results
    3. Fallback to heuristics

    Args:
        task_id: The task instance ID
        run_dir: Working directory with output files
        stdout: Captured stdout from harness
        stderr: Captured stderr from harness
        returncode: Process return code
        logs_parts: List to append log lines to

    Returns:
        SwebenchResult with parsed results
    """
    logs_parts.append("-" * 80)
    logs_parts.append("PARSING RESULTS")
    logs_parts.append("-" * 80)

    # Strategy 1: Look for results JSON
    results_file = run_dir / "logs" / f"{task_id}.json"
    if results_file.exists():
        try:
            results_data = json.loads(results_file.read_text())
            logs_parts.append(f"Found results file: {results_file}")
            return _parse_results_json(task_id, results_data, logs_parts)
        except (json.JSONDecodeError, KeyError) as e:
            logs_parts.append(f"Failed to parse results file: {e}")

    # Strategy 2: Check for report file
    report_file = run_dir / "logs" / "report.json"
    if report_file.exists():
        try:
            report_data = json.loads(report_file.read_text())
            logs_parts.append(f"Found report file: {report_file}")
            if task_id in report_data:
                return _parse_report_entry(task_id, report_data[task_id], logs_parts)
        except (json.JSONDecodeError, KeyError) as e:
            logs_parts.append(f"Failed to parse report file: {e}")

    # Strategy 3: Parse stdout for common patterns
    combined_output = stdout + "\n" + stderr

    # Check for patch apply failure
    if "patch does not apply" in combined_output.lower() or "error: patch failed" in combined_output.lower():
        logs_parts.append("Detected: patch apply failure")
        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=0,
            total_tests=0,
            failure_type="apply_error",
            runtime_ms=0,
            logs_text="",
        )

    # Check for build failure
    if "build failed" in combined_output.lower() or "compilation error" in combined_output.lower():
        logs_parts.append("Detected: build failure")
        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=0,
            total_tests=0,
            failure_type="build_error",
            runtime_ms=0,
            logs_text="",
        )

    # Try to extract test counts from pytest-style output
    tests_passed, total_tests = _extract_test_counts(combined_output)
    logs_parts.append(f"Extracted test counts: {tests_passed}/{total_tests}")

    # Check for explicit pass/fail in output
    if "PASSED" in combined_output and "FAILED" not in combined_output:
        logs_parts.append("Detected: all tests passed")
        return SwebenchResult(
            task_id=task_id,
            verdict="PASS",
            tests_passed=tests_passed if tests_passed > 0 else total_tests,
            total_tests=total_tests,
            failure_type=None,
            runtime_ms=0,
            logs_text="",
        )

    if "FAILED" in combined_output or returncode != 0:
        logs_parts.append(f"Detected: test failure (returncode={returncode})")
        return SwebenchResult(
            task_id=task_id,
            verdict="FAIL",
            tests_passed=tests_passed,
            total_tests=total_tests,
            failure_type="test_failure",
            runtime_ms=0,
            logs_text="",
        )

    # Fallback: assume success if return code is 0
    if returncode == 0:
        logs_parts.append("Fallback: assuming success based on return code 0")
        return SwebenchResult(
            task_id=task_id,
            verdict="PASS",
            tests_passed=total_tests if total_tests > 0 else 1,
            total_tests=total_tests if total_tests > 0 else 1,
            failure_type=None,
            runtime_ms=0,
            logs_text="",
        )

    # Ultimate fallback
    logs_parts.append("Fallback: unknown result, marking as failure")
    return SwebenchResult(
        task_id=task_id,
        verdict="FAIL",
        tests_passed=0,
        total_tests=0,
        failure_type="unknown",
        runtime_ms=0,
        logs_text="",
    )


def _parse_results_json(task_id: str, data: dict, logs_parts: list[str]) -> SwebenchResult:
    """Parse a per-instance results JSON file."""
    # SWE-bench typically stores results with these fields
    resolved = data.get("resolved", False)
    tests_status = data.get("tests_status", {})

    passed = sum(1 for s in tests_status.values() if s == "PASSED")
    total = len(tests_status)

    logs_parts.append(f"Resolved: {resolved}")
    logs_parts.append(f"Tests: {passed}/{total}")

    return SwebenchResult(
        task_id=task_id,
        verdict="PASS" if resolved else "FAIL",
        tests_passed=passed,
        total_tests=total,
        failure_type=None if resolved else "test_failure",
        runtime_ms=0,
        logs_text="",
    )


def _parse_report_entry(task_id: str, entry: dict, logs_parts: list[str]) -> SwebenchResult:
    """Parse a report.json entry for a single instance."""
    status = entry.get("status", "FAILED")
    resolved = status == "RESOLVED" or entry.get("resolved", False)

    # Try to get test counts
    passed = entry.get("tests_passed", 0)
    total = entry.get("total_tests", 0)

    logs_parts.append(f"Status: {status}")
    logs_parts.append(f"Resolved: {resolved}")

    return SwebenchResult(
        task_id=task_id,
        verdict="PASS" if resolved else "FAIL",
        tests_passed=passed,
        total_tests=total,
        failure_type=None if resolved else "test_failure",
        runtime_ms=0,
        logs_text="",
    )


def _extract_test_counts(output: str) -> tuple[int, int]:
    """
    Extract test pass/total counts from pytest-style output.

    Looks for patterns like:
    - "5 passed, 2 failed"
    - "====== 5 passed in 1.23s ======"
    - "PASSED: 5/7"

    Returns:
        Tuple of (passed, total)
    """
    import re

    # Pattern: "X passed, Y failed, Z errors"
    match = re.search(r"(\d+)\s+passed(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+error)?", output)
    if match:
        passed = int(match.group(1))
        failed = int(match.group(2) or 0)
        errors = int(match.group(3) or 0)
        return passed, passed + failed + errors

    # Pattern: "X/Y tests passed"
    match = re.search(r"(\d+)/(\d+)\s+tests?\s+passed", output, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Pattern: "PASSED: X, FAILED: Y"
    passed_match = re.search(r"PASSED:\s*(\d+)", output)
    failed_match = re.search(r"FAILED:\s*(\d+)", output)
    if passed_match or failed_match:
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        return passed, passed + failed

    return 0, 0


def check_swebench_available() -> tuple[bool, str]:
    """
    Check if SWE-bench is available in the environment.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["python", "-c", "import swebench; print(swebench.__version__)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"SWE-bench version {version} is available"
        else:
            return False, f"SWE-bench import failed: {result.stderr}"
    except FileNotFoundError:
        return False, "Python not found"
    except subprocess.TimeoutExpired:
        return False, "Timeout checking SWE-bench"
    except Exception as e:
        return False, f"Error checking SWE-bench: {e}"

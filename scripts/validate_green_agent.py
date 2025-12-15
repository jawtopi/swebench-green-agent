#!/usr/bin/env python3
"""
Validation script for Green Agent evaluation accuracy.

This script tests the SWE-bench harness directly with known patches
to validate that the green agent produces accurate evaluation results.

Usage:
    python scripts/validate_green_agent.py
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.harness.swebench_runner import run_swebench_task

# Test Case 1: Partial fix patch (should FAIL - incomplete fix)
# This patch applies but doesn't fully fix the issue
PARTIAL_PATCH = '''diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -303,6 +303,7 @@
 # The directory to store uploaded files temporarily.
 FILE_UPLOAD_TEMP_DIR = None

+# Partial fix - this comment doesn't actually fix the bug
 # The numeric mode to set newly-uploaded files to.
 FILE_UPLOAD_PERMISSIONS = 0o644
'''

# Test Case 2: Empty patch (should FAIL - no fix applied)
EMPTY_PATCH = ''

# Test Case 3: Malformed patch (should FAIL - apply error)
MALFORMED_PATCH = '''diff --git a/nonexistent/file.py b/nonexistent/file.py
--- a/nonexistent/file.py
+++ b/nonexistent/file.py
@@ -999,7 +999,7 @@
-this line does not exist
+replaced with something else
'''


def run_validation():
    """Run validation test cases."""
    print("=" * 60)
    print("GREEN AGENT VALIDATION")
    print("=" * 60)
    print()

    results = []

    # Test Case 1: Partial fix patch
    print("Test Case 1: Partial fix patch (applies but doesn't fix bug)")
    print("-" * 60)
    result1 = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=PARTIAL_PATCH,
    )
    print(f"  Verdict: {result1.verdict}")
    print(f"  Resolved: {result1.resolved}")
    print(f"  Failure Type: {result1.failure_type}")
    print(f"  Expected: FAIL (patch applies but tests still fail)")
    results.append(("Partial Patch", result1.verdict, "FAIL"))
    print()

    # Test Case 2: Empty patch
    print("Test Case 2: Empty patch for django__django-10914")
    print("-" * 60)
    result2 = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=EMPTY_PATCH,
    )
    print(f"  Verdict: {result2.verdict}")
    print(f"  Resolved: {result2.resolved}")
    print(f"  Failure Type: {result2.failure_type}")
    print(f"  Expected: FAIL (no fix applied)")
    results.append(("Empty Patch", result2.verdict, "FAIL"))
    print()

    # Test Case 3: Malformed patch
    print("Test Case 3: Malformed patch (wrong file/lines)")
    print("-" * 60)
    result3 = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=MALFORMED_PATCH,
    )
    print(f"  Verdict: {result3.verdict}")
    print(f"  Resolved: {result3.resolved}")
    print(f"  Failure Type: {result3.failure_type}")
    print(f"  Expected: FAIL (apply_error)")
    results.append(("Malformed Patch", result3.verdict, "FAIL"))
    print()

    # Summary
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, actual, expected in results:
        match = "MATCH" if actual == expected else "MISMATCH"
        if actual != expected:
            all_passed = False
        print(f"  {name}: {actual} (expected {expected}) - {match}")

    print()
    if all_passed:
        print("All validation tests passed!")
    else:
        print("Some validation tests failed!")

    return all_passed


if __name__ == "__main__":
    import sys
    success = run_validation()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Validation script for Green Agent evaluation accuracy.

This script tests the SWE-bench harness directly with known patches
to validate that the green agent produces accurate evaluation results.

Usage:
    python scripts/validate_green_agent.py
"""

from src.harness.swebench_runner import run_swebench_task

# Test Case 1: Known good patch (should PASS)
# This is the ground-truth patch for django__django-10914
GOOD_PATCH_DJANGO_10914 = '''diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -304,7 +304,7 @@ def gettext_noop(s):
 FILE_UPLOAD_TEMP_DIR = None

 # The numeric mode to set newly-uploaded files to. The value should be a mode
-# you'd pass directly to os.chmod; see https://docs.python.org/3/library/os.html#os.chmod.
+# you'd pass directly to os.chmod; see https://docs.python.org/library/os.html#os.chmod.
 FILE_UPLOAD_PERMISSIONS = 0o644

 # The numeric mode to apply to directories created in the process of uploading files.
diff --git a/django/core/files/uploadhandler.py b/django/core/files/uploadhandler.py
--- a/django/core/files/uploadhandler.py
+++ b/django/core/files/uploadhandler.py
@@ -1,4 +1,5 @@
 """
+# Set default file upload permissions
 File upload handlers.
 """
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

    # Test Case 1: Good patch
    print("Test Case 1: Known good patch for django__django-10914")
    print("-" * 60)
    result1 = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=GOOD_PATCH_DJANGO_10914,
    )
    print(f"  Verdict: {result1.verdict}")
    print(f"  Resolved: {result1.resolved}")
    print(f"  Failure Type: {result1.failure_type}")
    print(f"  Expected: PASS (resolved=True)")
    results.append(("Good Patch", result1.verdict, "PASS"))
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

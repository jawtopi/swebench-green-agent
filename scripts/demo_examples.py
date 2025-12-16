#!/usr/bin/env python3
"""
Demo script showing different evaluation outcomes for the SWE-bench green agent.

This script demonstrates:
1. PASS - A correct gold patch from SWE-bench (Django)
2. PASS - Another correct gold patch (Django)
3. FAIL (Apply Error) - A malformed patch
4. FAIL (Test Failure) - A patch that applies but doesn't fix the bug

Run: python scripts/demo_examples.py
"""

import sys
import time
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from datasets import load_dataset
from src.harness.swebench_runner import run_swebench_task

# ANSI colors for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(text: str):
    """Print a fancy header."""
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}\n")

def print_section(text: str):
    """Print a section header."""
    print(f"\n{BOLD}{BLUE}>>> {text}{RESET}\n")

def print_result(verdict: str, details: str = ""):
    """Print the result with color coding."""
    if verdict == "PASS":
        print(f"\n{BOLD}{GREEN}✓ RESULT: {verdict}{RESET}")
    else:
        print(f"\n{BOLD}{RED}✗ RESULT: {verdict}{RESET}")
    if details:
        print(f"  {details}")


def get_gold_patch(task_id: str) -> str:
    """Fetch the gold patch from SWE-bench dataset."""
    print(f"  Loading gold patch for {task_id} from SWE-bench...")
    dataset = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    for item in dataset:
        if item["instance_id"] == task_id:
            return item["patch"]
    raise ValueError(f"Task {task_id} not found in dataset")


def demo_gold_patch_1():
    """
    Example 1: PASS - Django gold patch from SWE-bench
    """
    task_id = "django__django-10914"

    print_header("EXAMPLE 1: PASS - Django File Upload Permissions (Gold Patch)")

    print(f"{YELLOW}Task:{RESET} {task_id}")
    print(f"{YELLOW}Issue:{RESET} Set default FILE_UPLOAD_PERMISSION to 0o644")
    print(f"{YELLOW}Repository:{RESET} django/django")
    print(f"{YELLOW}Description:{RESET} Using SWE-bench's official gold patch")

    gold_patch = get_gold_patch(task_id)

    print_section("Gold Patch Content (from SWE-bench)")
    # Show first 500 chars to keep it readable
    display_patch = gold_patch[:800] + "..." if len(gold_patch) > 800 else gold_patch
    print(f"{CYAN}{display_patch}{RESET}")
    print(f"\n{YELLOW}Patch size: {len(gold_patch)} bytes{RESET}")

    print_section("Running SWE-bench Evaluation")
    print("• Applying gold patch to Django codebase in Docker...")
    print("• Running test suite...")

    start = time.time()
    result = run_swebench_task(
        task_id=task_id,
        patch_diff=gold_patch,
        dataset_split="verified"
    )
    elapsed = time.time() - start

    print_section("Evaluation Results")
    print(f"  Verdict:        {GREEN if result.verdict == 'PASS' else RED}{result.verdict}{RESET}")
    print(f"  Resolved:       {result.resolved}")
    print(f"  FAIL→PASS:      {result.fail_to_pass}/{result.fail_to_pass_total} tests fixed")
    print(f"  PASS→PASS:      {result.pass_to_pass}/{result.pass_to_pass_total} tests still pass")
    print(f"  Runtime:        {elapsed:.1f}s")

    print_result(result.verdict, "Gold patch from SWE-bench correctly fixes the bug!")
    return result.verdict == "PASS"


def demo_gold_patch_2():
    """
    Example 2: PASS - Another Django gold patch
    """
    task_id = "django__django-16493"

    print_header("EXAMPLE 2: PASS - Django FileField Storage (Gold Patch)")

    print(f"{YELLOW}Task:{RESET} {task_id}")
    print(f"{YELLOW}Issue:{RESET} FileField with callable storage doesn't work with deconstruct")
    print(f"{YELLOW}Repository:{RESET} django/django")
    print(f"{YELLOW}Description:{RESET} Using SWE-bench's official gold patch")

    gold_patch = get_gold_patch(task_id)

    print_section("Gold Patch Content (from SWE-bench)")
    display_patch = gold_patch[:800] + "..." if len(gold_patch) > 800 else gold_patch
    print(f"{CYAN}{display_patch}{RESET}")
    print(f"\n{YELLOW}Patch size: {len(gold_patch)} bytes{RESET}")

    print_section("Running SWE-bench Evaluation")
    print("• Applying gold patch to Django codebase in Docker...")
    print("• Running test suite...")

    start = time.time()
    result = run_swebench_task(
        task_id=task_id,
        patch_diff=gold_patch,
        dataset_split="verified"
    )
    elapsed = time.time() - start

    print_section("Evaluation Results")
    print(f"  Verdict:        {GREEN if result.verdict == 'PASS' else RED}{result.verdict}{RESET}")
    print(f"  Resolved:       {result.resolved}")
    print(f"  FAIL→PASS:      {result.fail_to_pass}/{result.fail_to_pass_total} tests fixed")
    print(f"  PASS→PASS:      {result.pass_to_pass}/{result.pass_to_pass_total} tests still pass")
    print(f"  Runtime:        {elapsed:.1f}s")

    print_result(result.verdict, "Gold patch from SWE-bench correctly fixes the bug!")
    return result.verdict == "PASS"


def demo_apply_error():
    """
    Example 3: FAIL (Apply Error) - A malformed patch that can't be applied
    """
    print_header("EXAMPLE 3: FAIL - Malformed Patch (Apply Error)")

    print(f"{YELLOW}Task:{RESET} django__django-10914")
    print(f"{YELLOW}Scenario:{RESET} White agent returned explanation text instead of a patch")

    malformed_patch = '''I looked for the Django sources in the provided workspace so I could
read the code and produce a correct patch, but this checkout does not
contain the Django repository (it appears to be a different project).

I searched the tree for FILE_UPLOAD_PERMISSIONS and other symbols but
couldn't find the relevant files.

To fix django-10914, you would need to modify the default value in
django/conf/global_settings.py to set FILE_UPLOAD_PERMISSIONS = 0o644.

Please provide the correct repository checkout.
'''

    print_section("Patch Content (Malformed - Not a Valid Diff)")
    print(f"{RED}{malformed_patch}{RESET}")

    print_section("Running SWE-bench Evaluation")
    print("• Attempting to apply patch...")

    start = time.time()
    result = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=malformed_patch,
        dataset_split="verified"
    )
    elapsed = time.time() - start

    print_section("Evaluation Results")
    print(f"  Verdict:        {GREEN if result.verdict == 'PASS' else RED}{result.verdict}{RESET}")
    print(f"  Failure Type:   {YELLOW}{result.failure_type}{RESET}")
    print(f"  Runtime:        {elapsed:.1f}s")

    print_result(result.verdict, f"Correctly identified as '{result.failure_type}' - garbage input rejected!")
    return result.verdict == "FAIL" and result.failure_type == "apply_error"


def demo_wrong_fix():
    """
    Example 4: FAIL (Test Failure) - Gold patch for DIFFERENT task applied to wrong task
    """
    print_header("EXAMPLE 4: FAIL - Wrong Patch (Test Failure)")

    print(f"{YELLOW}Task:{RESET} django__django-10914")
    print(f"{YELLOW}Scenario:{RESET} Applying a syntactically valid but WRONG patch")
    print(f"{YELLOW}Description:{RESET} This patch modifies the right file but sets wrong value")

    # A valid-looking patch but with wrong value
    wrong_patch = '''diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -304,7 +304,7 @@ MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'

 # The numeric mode to set newly-uploaded files to. The value should be a mode
 # you'd pass directly to os.chmod; see https://docs.python.org/library/os.html#files-and-directories.
-FILE_UPLOAD_PERMISSIONS = None
+FILE_UPLOAD_PERMISSIONS = 0o755

 # The numeric mode to apply to directories created in the process of uploading files.
 FILE_UPLOAD_DIRECTORY_PERMISSIONS = None
'''

    print_section("Patch Content (Wrong Value: 0o755 instead of 0o644)")
    print(f"{YELLOW}{wrong_patch}{RESET}")
    print(f"\n{YELLOW}⚠ Problem: Sets 0o755 (rwxr-xr-x) instead of correct 0o644 (rw-r--r--){RESET}")

    print_section("Running SWE-bench Evaluation")
    print("• Applying patch to Django codebase in Docker...")
    print("• Running test suite...")

    start = time.time()
    result = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=wrong_patch,
        dataset_split="verified"
    )
    elapsed = time.time() - start

    print_section("Evaluation Results")
    print(f"  Verdict:        {GREEN if result.verdict == 'PASS' else RED}{result.verdict}{RESET}")
    print(f"  Resolved:       {result.resolved}")
    print(f"  FAIL→PASS:      {result.fail_to_pass}/{result.fail_to_pass_total} tests fixed")
    print(f"  PASS→PASS:      {result.pass_to_pass}/{result.pass_to_pass_total} tests still pass")
    if result.failure_type:
        print(f"  Failure Type:   {YELLOW}{result.failure_type}{RESET}")
    print(f"  Runtime:        {elapsed:.1f}s")

    print_result(result.verdict, "Patch applied but tests fail - 0o755 is not the expected value!")
    return result.verdict == "FAIL"


def demo_empty_patch():
    """
    Example 5: FAIL - Empty patch
    """
    print_header("EXAMPLE 5: FAIL - Empty Patch")

    print(f"{YELLOW}Task:{RESET} django__django-10914")
    print(f"{YELLOW}Scenario:{RESET} White agent returned an empty response")

    empty_patch = ''

    print_section("Patch Content")
    print(f"{RED}(empty - no patch provided){RESET}")

    print_section("Running SWE-bench Evaluation")
    print("• Attempting to apply empty patch...")

    start = time.time()
    result = run_swebench_task(
        task_id="django__django-10914",
        patch_diff=empty_patch,
        dataset_split="verified"
    )
    elapsed = time.time() - start

    print_section("Evaluation Results")
    print(f"  Verdict:        {GREEN if result.verdict == 'PASS' else RED}{result.verdict}{RESET}")
    if result.failure_type:
        print(f"  Failure Type:   {YELLOW}{result.failure_type}{RESET}")
    print(f"  Runtime:        {elapsed:.1f}s")

    print_result(result.verdict, "Correctly rejected empty patch!")
    return result.verdict == "FAIL"


def main():
    """Run all demo examples."""
    print(f"\n{BOLD}{CYAN}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║           SWE-bench Green Agent - Evaluation Demo                    ║")
    print("║                                                                      ║")
    print("║   Using REAL gold patches from SWE-bench dataset!                    ║")
    print("║                                                                      ║")
    print("║   Examples:                                                          ║")
    print("║   • 2 PASS cases with official gold patches                         ║")
    print("║   • 3 FAIL cases (malformed, wrong fix, empty)                      ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")

    results = []

    input(f"{BOLD}Press Enter to start Example 1 (Gold Patch PASS)...{RESET}")
    results.append(("Django 10914: Gold Patch", "PASS", demo_gold_patch_1()))

    input(f"\n{BOLD}Press Enter to start Example 2 (Gold Patch PASS)...{RESET}")
    results.append(("Django 16493: Gold Patch", "PASS", demo_gold_patch_2()))

    input(f"\n{BOLD}Press Enter to start Example 3 (Malformed FAIL)...{RESET}")
    results.append(("Malformed Text", "FAIL (apply_error)", demo_apply_error()))

    input(f"\n{BOLD}Press Enter to start Example 4 (Wrong Fix FAIL)...{RESET}")
    results.append(("Wrong Value Patch", "FAIL (test_failure)", demo_wrong_fix()))

    input(f"\n{BOLD}Press Enter to start Example 5 (Empty FAIL)...{RESET}")
    results.append(("Empty Patch", "FAIL", demo_empty_patch()))

    # Summary
    print_header("DEMO SUMMARY")

    print(f"{'Example':<35} {'Expected':<22} {'Correct?':<10}")
    print("-" * 70)
    for name, expected, correct in results:
        status = f"{GREEN}✓ Yes{RESET}" if correct else f"{RED}✗ No{RESET}"
        print(f"{name:<35} {expected:<22} {status}")

    passed = sum(1 for r in results if r[2])
    total = len(results)

    print()
    print(f"{BOLD}Score: {passed}/{total} evaluations correct{RESET}")
    print()

    if passed == total:
        print(f"{GREEN}{BOLD}✓ All evaluations returned expected results!{RESET}")
        print(f"{GREEN}The green agent correctly handles:{RESET}")
        print(f"{GREEN}  • Official gold patches from SWE-bench{RESET}")
        print(f"{GREEN}  • Malformed/garbage patches{RESET}")
        print(f"{GREEN}  • Wrong fixes that don't pass tests{RESET}")
        print(f"{GREEN}  • Empty patches{RESET}")
    else:
        print(f"{YELLOW}Some evaluations may have unexpected results.{RESET}")
        print(f"{YELLOW}Check that Docker is running and images are available.{RESET}")

    print()


if __name__ == "__main__":
    main()

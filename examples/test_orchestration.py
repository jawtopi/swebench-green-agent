#!/usr/bin/env python3
"""
Test orchestration script for SWE-bench Green Agent.

This script demonstrates the full A2A flow:
1. Starts the mock white agent
2. Starts the green agent
3. Sends a task to the green agent
4. Green agent calls white agent with problem statement
5. White agent returns a patch
6. Green agent evaluates the patch
7. Results are reported

Usage:
    python -m examples.test_orchestration
    python -m examples.test_orchestration --skip-eval  # Skip actual SWE-bench evaluation
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import multiprocessing
import json
import time
import argparse

from src.green_agent import start_green_agent
from src.green_agent.a2a_utils import send_message, wait_agent_ready
from examples.mock_white_agent import start_mock_white_agent


async def run_test_orchestration(skip_eval: bool = False):
    """Run the full orchestration test."""

    GREEN_HOST = "localhost"
    GREEN_PORT = 9001
    WHITE_HOST = "localhost"
    WHITE_PORT = 9002

    green_url = f"http://{GREEN_HOST}:{GREEN_PORT}"
    white_url = f"http://{WHITE_HOST}:{WHITE_PORT}"

    print("=" * 70)
    print("SWE-BENCH GREEN AGENT ORCHESTRATION TEST")
    print("=" * 70)
    print()

    # Step 1: Start mock white agent
    print("[1/6] Starting mock white agent...")
    p_white = multiprocessing.Process(
        target=start_mock_white_agent,
        args=(WHITE_HOST, WHITE_PORT, "mock"),
    )
    p_white.start()

    # Step 2: Start green agent
    print("[2/6] Starting green agent...")
    p_green = multiprocessing.Process(
        target=start_green_agent,
        args=("swebench_green_agent", GREEN_HOST, GREEN_PORT),
    )
    p_green.start()

    try:
        # Wait for both agents to be ready
        print("[3/6] Waiting for agents to be ready...")

        white_ready = await wait_agent_ready(white_url, timeout=30)
        if not white_ready:
            print("ERROR: White agent failed to start")
            return

        green_ready = await wait_agent_ready(green_url, timeout=30)
        if not green_ready:
            print("ERROR: Green agent failed to start")
            return

        print(f"      White agent ready at {white_url}")
        print(f"      Green agent ready at {green_url}")
        print()

        # Step 3: Build task configuration
        print("[4/6] Building task configuration...")

        if skip_eval:
            # Use a simple task for testing without full SWE-bench evaluation
            task_config = {
                "dataset": "lite",
                "task_ids": ["django__django-10914"],
                "timeout": 60,  # Short timeout for testing
            }
            print("      Mode: SKIP EVAL (testing flow only)")
        else:
            task_config = {
                "dataset": "lite",
                "task_ids": ["django__django-10914"],
                "timeout": 600,
            }
            print("      Mode: FULL EVAL (will run SWE-bench in Docker)")

        print(f"      Dataset: {task_config['dataset']}")
        print(f"      Tasks: {task_config['task_ids']}")
        print()

        # Step 4: Send task to green agent
        print("[5/6] Sending task to green agent...")
        print()
        print("-" * 70)
        print("TASK MESSAGE:")
        print("-" * 70)

        task_message = f"""Your task is to run SWE-bench evaluation for the agent located at:
<white_agent_url>
{white_url}
</white_agent_url>
You should use the following task configuration:
<task_config>
{json.dumps(task_config, indent=2)}
</task_config>
"""
        print(task_message)
        print("-" * 70)
        print()

        # Send the task
        print("Sending task to green agent...")
        start_time = time.time()

        response = await send_message(
            url=green_url,
            message=task_message,
            timeout=task_config["timeout"] * 2,
        )

        elapsed = time.time() - start_time
        print()
        print("-" * 70)
        print(f"[6/6] RESULTS (completed in {elapsed:.1f}s)")
        print("-" * 70)
        print()
        print(response)
        print()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print()
        print("=" * 70)
        print("Shutting down agents...")
        p_green.terminate()
        p_white.terminate()
        p_green.join(timeout=5)
        p_white.join(timeout=5)
        print("Done.")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Test SWE-bench orchestration")
    parser.add_argument("--skip-eval", action="store_true",
                       help="Skip actual SWE-bench evaluation (faster, tests flow only)")
    args = parser.parse_args()

    asyncio.run(run_test_orchestration(skip_eval=args.skip_eval))


if __name__ == "__main__":
    main()

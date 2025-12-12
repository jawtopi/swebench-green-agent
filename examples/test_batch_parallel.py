#!/usr/bin/env python3
"""
Test parallel batch evaluation with mock white agent.

Usage:
    cd examples && python test_batch_parallel.py
    # Or from repo root:
    python -m examples.test_batch_parallel
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import multiprocessing
import json
import time

from src.green_agent import start_green_agent
from src.green_agent.a2a_utils import send_message, wait_agent_ready
from examples.mock_white_agent import start_mock_white_agent


async def test_batch_parallel():
    """Test batch parallel evaluation."""

    GREEN_HOST = "localhost"
    GREEN_PORT = 9001
    WHITE_HOST = "localhost"
    WHITE_PORT = 9002

    green_url = f"http://{GREEN_HOST}:{GREEN_PORT}"
    white_url = f"http://{WHITE_HOST}:{WHITE_PORT}"

    print("=" * 60)
    print("BATCH PARALLEL EVALUATION TEST")
    print("=" * 60)
    print()

    # Start agents
    print("[1/4] Starting mock white agent...")
    p_white = multiprocessing.Process(
        target=start_mock_white_agent,
        args=(WHITE_HOST, WHITE_PORT, "mock"),
    )
    p_white.start()

    print("[2/4] Starting green agent...")
    p_green = multiprocessing.Process(
        target=start_green_agent,
        args=("swebench_green_agent", GREEN_HOST, GREEN_PORT),
    )
    p_green.start()

    try:
        # Wait for agents
        print("[3/4] Waiting for agents...")
        await wait_agent_ready(white_url, timeout=15)
        await wait_agent_ready(green_url, timeout=15)
        print("      Both agents ready")
        print()

        # Send batch task with multiple task_ids and max_workers
        print("[4/4] Sending batch task (3 tasks, 2 workers)...")

        task_config = {
            "dataset": "lite",
            "task_ids": [
                "django__django-10914",
                "astropy__astropy-12907",
                "django__django-11099",
            ],
            "timeout": 60,
            "max_workers": 2,  # Test parallel execution
        }

        task_message = f"""Your task is to run SWE-bench evaluation for the agent located at:
<white_agent_url>
{white_url}
</white_agent_url>
You should use the following task configuration:
<task_config>
{json.dumps(task_config, indent=2)}
</task_config>
"""
        print(f"      Config: {json.dumps(task_config)}")
        print()

        start = time.time()
        response = await send_message(green_url, task_message, timeout=300)
        elapsed = time.time() - start

        print("-" * 60)
        print(f"RESULTS (completed in {elapsed:.1f}s)")
        print("-" * 60)
        print(response)
        print()

        print("=" * 60)
        print("BATCH PARALLEL TEST: SUCCESS")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print()
        print("Shutting down agents...")
        p_green.terminate()
        p_white.terminate()
        p_green.join(timeout=5)
        p_white.join(timeout=5)


if __name__ == "__main__":
    asyncio.run(test_batch_parallel())

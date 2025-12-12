#!/usr/bin/env python3
"""
Quick test of A2A communication flow between green and white agents.

This tests ONLY the A2A communication, not the SWE-bench evaluation.

Usage:
    cd examples && python test_a2a_flow.py
    # Or from repo root:
    python -m examples.test_a2a_flow
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import multiprocessing
import time

from src.green_agent.a2a_utils import (
    get_agent_card,
    wait_agent_ready,
    send_message,
    format_swebench_task_message,
    parse_tags,
)
from examples.mock_white_agent import start_mock_white_agent


async def test_a2a_communication():
    """Test A2A communication with mock white agent."""

    WHITE_HOST = "localhost"
    WHITE_PORT = 9002
    white_url = f"http://{WHITE_HOST}:{WHITE_PORT}"

    print("=" * 60)
    print("A2A COMMUNICATION TEST")
    print("=" * 60)
    print()

    # Start mock white agent
    print("[1/5] Starting mock white agent...")
    p_white = multiprocessing.Process(
        target=start_mock_white_agent,
        args=(WHITE_HOST, WHITE_PORT, "mock"),
    )
    p_white.start()

    try:
        # Wait for agent to be ready
        print("[2/5] Waiting for white agent...")
        ready = await wait_agent_ready(white_url, timeout=15)
        if not ready:
            print("ERROR: White agent failed to start")
            return False
        print(f"      White agent ready at {white_url}")
        print()

        # Get agent card
        print("[3/5] Fetching agent card...")
        card = await get_agent_card(white_url)
        print(f"      Name: {card.name}")
        print(f"      Version: {card.version}")
        print(f"      Skills: {len(card.skills)}")
        print()

        # Format a task message
        print("[4/5] Sending task message...")
        task_message = format_swebench_task_message(
            task_id="django__django-10914",
            problem_statement="There is a bug in Django settings...",
            repo="django/django",
            hints_text="Check global_settings.py",
            base_commit="abc123",
        )
        print(f"      Message length: {len(task_message)} bytes")

        # Send message
        start = time.time()
        response = await send_message(white_url, task_message, timeout=30)
        elapsed = time.time() - start
        print(f"      Response received in {elapsed:.2f}s")
        print()

        # Parse response
        print("[5/5] Parsing response...")
        from a2a.types import SendMessageSuccessResponse, Message
        from a2a.utils import get_text_parts

        res_root = response.root
        if isinstance(res_root, SendMessageSuccessResponse):
            res_result = res_root.result
            if isinstance(res_result, Message):
                text_parts = get_text_parts(res_result.parts)
                if text_parts:
                    white_text = text_parts[0]
                    tags = parse_tags(white_text)
                    patch = tags.get("patch")

                    print(f"      Response text length: {len(white_text)} bytes")
                    if patch:
                        print(f"      Patch found: YES ({len(patch)} bytes)")
                        print()
                        print("-" * 60)
                        print("PATCH CONTENT:")
                        print("-" * 60)
                        print(patch[:500])
                        if len(patch) > 500:
                            print(f"... ({len(patch) - 500} more bytes)")
                        print("-" * 60)
                    else:
                        print("      Patch found: NO")

        print()
        print("=" * 60)
        print("A2A COMMUNICATION TEST: SUCCESS")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print()
        print("Shutting down mock white agent...")
        p_white.terminate()
        p_white.join(timeout=5)


if __name__ == "__main__":
    success = asyncio.run(test_a2a_communication())
    exit(0 if success else 1)

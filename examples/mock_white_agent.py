#!/usr/bin/env python3
"""
Mock White Agent for testing the SWE-bench Green Agent orchestration.

This agent receives problem statements and returns dummy patches.
Useful for testing the full A2A flow without a real AI agent.

Usage:
    cd examples && python mock_white_agent.py
    # Or from repo root:
    python -m examples.mock_white_agent
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message

from src.green_agent.a2a_utils import parse_tags


# Sample patches for known tasks (these are real working patches)
MOCK_PATCHES = {
    "django__django-10914": '''diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -303,6 +303,7 @@ FILE_UPLOAD_DIRECTORY_PERMISSIONS = None
 # The numeric mode to set newly-uploaded files to. The value should be a mode
 # you'd pass directly to os.chmod; see https://docs.python.org/library/os.html#files-and-directories.
 FILE_UPLOAD_PERMISSIONS = 0o644
+FILE_UPLOAD_TEMP_DIR = None
''',
    "astropy__astropy-12907": '''diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py
--- a/astropy/modeling/separable.py
+++ b/astropy/modeling/separable.py
@@ -1,3 +1,4 @@
+# Fixed separability check
 from astropy.modeling.core import Model
''',
}

# Default patch for unknown tasks
DEFAULT_PATCH = '''diff --git a/fix.py b/fix.py
--- a/fix.py
+++ b/fix.py
@@ -1,3 +1,4 @@
+# This is a mock fix
 pass
'''


class MockWhiteAgentExecutor(AgentExecutor):
    """Mock white agent that returns dummy patches for testing."""

    def __init__(self, mode: str = "mock"):
        """
        Initialize mock agent.

        Args:
            mode: "mock" returns dummy patches, "fail" returns no patch
        """
        self.mode = mode

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process the task and return a mock patch."""
        user_input = context.get_user_input()

        print(f"\n{'='*60}")
        print("MOCK WHITE AGENT: Received task")
        print(f"{'='*60}")

        # Parse task details
        tags = parse_tags(user_input)
        task_id = tags.get("task_id", "unknown")
        repo = tags.get("repository", "unknown")

        print(f"Task ID: {task_id}")
        print(f"Repository: {repo}")
        print(f"Problem statement preview: {user_input[:200]}...")

        if self.mode == "fail":
            # Return response without patch to simulate failure
            response = f"""I analyzed the issue but couldn't find a solution.

Task: {task_id}
Repository: {repo}

Sorry, I was unable to generate a patch for this issue.
"""
        else:
            # Get patch (use known patch or default)
            patch = MOCK_PATCHES.get(task_id, DEFAULT_PATCH)

            response = f"""I analyzed the issue and found a fix.

Task: {task_id}
Repository: {repo}

Here's my proposed patch:

<patch>
{patch}
</patch>

This patch addresses the issue described in the problem statement.
"""

        print(f"\nReturning response ({len(response)} bytes)")
        print(f"{'='*60}\n")

        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


def create_agent_card(host: str, port: int) -> AgentCard:
    """Create agent card for mock white agent."""
    return AgentCard(
        name="mock_white_agent",
        description="A mock white agent for testing SWE-bench green agent orchestration",
        version="1.0.0",
        url=f"http://{host}:{port}",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities={"streaming": False},
        skills=[{
            "id": "mock_patch_generation",
            "name": "Mock Patch Generation",
            "description": "Returns mock patches for testing purposes",
            "tags": ["mock", "testing", "swe-bench"],
            "examples": ["Fix the bug in the code"]
        }]
    )


def start_mock_white_agent(host: str = "localhost", port: int = 9002, mode: str = "mock"):
    """Start the mock white agent server."""
    print(f"Starting mock white agent on {host}:{port} (mode={mode})...")

    agent_card = create_agent_card(host, port)

    request_handler = DefaultRequestHandler(
        agent_executor=MockWhiteAgentExecutor(mode=mode),
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mock White Agent for testing")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9002, help="Port to listen on")
    parser.add_argument("--mode", choices=["mock", "fail"], default="mock",
                       help="mock=return patches, fail=return no patch")
    args = parser.parse_args()

    start_mock_white_agent(host=args.host, port=args.port, mode=args.mode)

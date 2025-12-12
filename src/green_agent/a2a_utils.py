"""A2A Protocol utilities for agent communication."""

import re
import httpx
import asyncio
import uuid
from typing import Dict, Optional

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Part,
    TextPart,
    MessageSendParams,
    Message,
    Role,
    SendMessageRequest,
    SendMessageResponse,
)


def parse_tags(str_with_tags: str) -> Dict[str, str]:
    """
    Parse XML-like tags from a string.

    Example:
        Input: "<white_agent_url>http://localhost:9002/</white_agent_url>"
        Output: {"white_agent_url": "http://localhost:9002/"}
    """
    tags = re.findall(r"<(.*?)>(.*?)</\1>", str_with_tags, re.DOTALL)
    return {tag: content.strip() for tag, content in tags}


async def get_agent_card(url: str) -> Optional[AgentCard]:
    """Get agent card from a remote agent."""
    httpx_client = httpx.AsyncClient()
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)

    try:
        card: Optional[AgentCard] = await resolver.get_agent_card()
        return card
    except Exception as e:
        print(f"Error getting agent card from {url}: {e}")
        return None
    finally:
        await httpx_client.aclose()


async def wait_agent_ready(url: str, timeout: int = 30) -> bool:
    """
    Wait until an A2A agent is ready by checking its agent card.

    Args:
        url: The agent's base URL
        timeout: Maximum seconds to wait

    Returns:
        True if agent is ready, False if timeout
    """
    retry_cnt = 0
    while retry_cnt < timeout:
        retry_cnt += 1
        try:
            card = await get_agent_card(url)
            if card is not None:
                return True
            else:
                print(f"Agent card not available yet... retrying {retry_cnt}/{timeout}")
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def send_message(
    url: str,
    message: str,
    task_id: Optional[str] = None,
    context_id: Optional[str] = None,
    timeout: float = 600.0,
) -> SendMessageResponse:
    """
    Send a message to an A2A agent.

    Args:
        url: The agent's base URL
        message: Text message to send
        task_id: Optional task ID for tracking
        context_id: Optional context ID for conversation continuity
        timeout: Request timeout in seconds

    Returns:
        SendMessageResponse from the agent
    """
    card = await get_agent_card(url)
    if card is None:
        raise RuntimeError(f"Could not get agent card from {url}")

    httpx_client = httpx.AsyncClient(timeout=timeout)
    client = A2AClient(httpx_client=httpx_client, agent_card=card)

    message_id = uuid.uuid4().hex
    params = MessageSendParams(
        message=Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            message_id=message_id,
            task_id=task_id,
            context_id=context_id,
        )
    )
    request_id = uuid.uuid4().hex
    req = SendMessageRequest(id=request_id, params=params)

    try:
        response = await client.send_message(request=req)
        return response
    finally:
        await httpx_client.aclose()


def format_swebench_task_message(
    task_id: str,
    problem_statement: str,
    repo: str,
    hints_text: str = "",
    base_commit: str = "",
) -> str:
    """
    Format a SWE-bench task as a message to send to a white agent.

    The white agent should return a unified diff patch in response.
    """
    message = f"""You are a software engineer tasked with fixing a bug in an open source project.

<task_id>{task_id}</task_id>

<repository>{repo}</repository>

<base_commit>{base_commit[:12] if base_commit else "latest"}</base_commit>

<problem_statement>
{problem_statement}
</problem_statement>
"""

    if hints_text:
        message += f"""
<hints>
{hints_text}
</hints>
"""

    message += """
Please analyze this issue and provide a fix as a unified diff patch.
Wrap your patch in <patch>...</patch> tags.

Example format:
<patch>
diff --git a/path/to/file.py b/path/to/file.py
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,6 +10,7 @@
 existing line
+new line to fix the bug
 another existing line
</patch>
"""

    return message

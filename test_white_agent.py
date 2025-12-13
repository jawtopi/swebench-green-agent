#!/usr/bin/env python
"""Quick test script to send a sample SWE-bench task to a white agent."""

import asyncio
from src.green_agent.a2a_utils import send_message, format_swebench_task_message

# Sample task from SWE-bench
SAMPLE_TASK = {
    "task_id": "django__django-11099",
    "repo": "django/django",
    "base_commit": "d4df5e1b0b1c643fe0fc5a9a8a5fcd7e5a5f5e5a",
    "problem_statement": """UsernameValidator allows trailing newline in usernames

Description

ASCIIUsernameValidator and UnicodeUsernameValidator use the regex
r'^[\\w.@+-]+$'

The use of $ instead of \\Z allows a trailing newline in the username.

Should be:
r'^[\\w.@+-]+\\Z'
""",
    "hints_text": "",
}


async def test_white_agent(white_agent_url: str):
    print(f"Testing white agent at: {white_agent_url}")
    print("=" * 60)

    # Format the message
    message = format_swebench_task_message(
        task_id=SAMPLE_TASK["task_id"],
        problem_statement=SAMPLE_TASK["problem_statement"],
        repo=SAMPLE_TASK["repo"],
        hints_text=SAMPLE_TASK["hints_text"],
        base_commit=SAMPLE_TASK["base_commit"],
    )

    print("Sending message:")
    print("-" * 60)
    print(message[:500] + "..." if len(message) > 500 else message)
    print("-" * 60)

    try:
        print("\nWaiting for response (this may take a while)...")
        response = await send_message(
            url=white_agent_url,
            message=message,
            task_id=SAMPLE_TASK["task_id"],
            timeout=300.0,  # 5 minute timeout
        )

        print("\nResponse received!")
        print("=" * 60)

        # Extract text from response
        from a2a.types import SendMessageSuccessResponse, Message, Task
        from a2a.utils import get_text_parts

        res_root = response.root
        if isinstance(res_root, SendMessageSuccessResponse):
            res_result = res_root.result

            # Handle Task response (contains artifacts with the actual response)
            if isinstance(res_result, Task):
                print(f"Task ID: {res_result.id}")
                print(f"Task Status: {res_result.status.state if res_result.status else 'unknown'}")

                # Extract text from task artifacts
                text_content = []
                if res_result.artifacts:
                    for artifact in res_result.artifacts:
                        if artifact.parts:
                            parts_text = get_text_parts(artifact.parts)
                            text_content.extend(parts_text)

                # Also check status message
                if res_result.status and res_result.status.message:
                    status_text = get_text_parts(res_result.status.message.parts)
                    text_content.extend(status_text)

                if text_content:
                    full_text = '\n'.join(text_content)
                    print("\nWhite agent response:")
                    print("-" * 60)
                    print(full_text[:2000] + "..." if len(full_text) > 2000 else full_text)
                    print("-" * 60)

                    # Check for patch
                    from src.green_agent.a2a_utils import parse_tags
                    tags = parse_tags(full_text)
                    if "patch" in tags:
                        print("\n✅ Patch found!")
                        print("Patch content:")
                        print(tags["patch"][:500] + "..." if len(tags["patch"]) > 500 else tags["patch"])
                    else:
                        print("\n❌ No <patch>...</patch> tags found in response")
                else:
                    print("No text content in task artifacts")

            # Handle direct Message response
            elif isinstance(res_result, Message):
                text_parts = get_text_parts(res_result.parts)
                if text_parts:
                    print("White agent response:")
                    print("-" * 60)
                    print(text_parts[0])
                    print("-" * 60)

                    # Check for patch
                    from src.green_agent.a2a_utils import parse_tags
                    tags = parse_tags(text_parts[0])
                    if "patch" in tags:
                        print("\n✅ Patch found!")
                        print("Patch content:")
                        print(tags["patch"][:500] + "..." if len(tags["patch"]) > 500 else tags["patch"])
                    else:
                        print("\n❌ No <patch>...</patch> tags found in response")
                else:
                    print("Empty response from white agent")
            else:
                print(f"Unexpected result type: {type(res_result)}")
                print(f"Result: {res_result}")
        else:
            print(f"Non-success response: {res_root}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys

    white_agent_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9002"

    print(f"\n🧪 SWE-bench Green/White Agent Integration Test")
    print(f"White agent URL: {white_agent_url}\n")

    asyncio.run(test_white_agent(white_agent_url))

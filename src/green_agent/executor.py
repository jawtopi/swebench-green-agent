"""SWE-bench Green Agent Executor - manages assessment and evaluation."""

import asyncio
import json
import time
import tomllib
import uvicorn
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, SendMessageSuccessResponse, Message, Task
from a2a.utils import new_agent_text_message, get_text_parts

from src.green_agent.a2a_utils import parse_tags, send_message, format_swebench_task_message
from src.harness.swebench_runner import run_swebench_task
from src.core.logger import logger

# Default number of parallel workers for batch evaluation
DEFAULT_MAX_WORKERS = 4


def load_agent_card_toml(agent_name: str) -> dict:
    """Load agent card from TOML file."""
    import os
    current_dir = os.path.dirname(__file__)
    with open(f"{current_dir}/{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


def load_swebench_tasks(dataset: str = "verified", task_ids: Optional[list[str]] = None) -> list[dict]:
    """
    Load SWE-bench tasks from HuggingFace datasets.

    Args:
        dataset: One of 'lite' (300), 'verified' (500), or 'full' (2294)
        task_ids: Optional list of specific task IDs to load

    Returns:
        List of task dicts with instance_id, problem_statement, repo, hints_text, base_commit
    """
    from datasets import load_dataset

    # Map dataset name to HuggingFace dataset
    dataset_map = {
        "lite": "princeton-nlp/SWE-bench_Lite",
        "verified": "princeton-nlp/SWE-bench_Verified",
        "full": "princeton-nlp/SWE-bench",
        "test": "princeton-nlp/SWE-bench",
    }

    hf_dataset = dataset_map.get(dataset.lower(), "princeton-nlp/SWE-bench_Verified")
    logger.info(f"Loading SWE-bench dataset: {hf_dataset}")

    # Load the dataset (test split contains the evaluation tasks)
    ds = load_dataset(hf_dataset, split="test")

    tasks = []
    for item in ds:
        task_id = item["instance_id"]

        # Filter to specific task IDs if provided
        if task_ids and task_id not in task_ids:
            continue

        tasks.append({
            "instance_id": task_id,
            "problem_statement": item.get("problem_statement", ""),
            "repo": item.get("repo", ""),
            "hints_text": item.get("hints_text", ""),
            "base_commit": item.get("base_commit", ""),
        })

    logger.info(f"Loaded {len(tasks)} tasks from {hf_dataset}")
    return tasks


async def evaluate_single_task(
    white_agent_url: str,
    task: dict,
    context_id: Optional[str] = None,
    timeout: float = 600.0,
) -> dict:
    """
    Send a single SWE-bench task to a white agent and evaluate the response.

    Args:
        white_agent_url: URL of the white agent to call
        task: Task dict with instance_id, problem_statement, repo, etc.
        context_id: Optional context ID for conversation continuity
        timeout: Timeout in seconds for the white agent response

    Returns:
        Dict with evaluation results
    """
    task_id = task["instance_id"]
    logger.info(f"Evaluating task {task_id} with white agent at {white_agent_url}")

    # Format the task message
    message = format_swebench_task_message(
        task_id=task_id,
        problem_statement=task["problem_statement"],
        repo=task["repo"],
        hints_text=task.get("hints_text", ""),
        base_commit=task.get("base_commit", ""),
    )

    result = {
        "task_id": task_id,
        "resolved": False,
        "verdict": "FAIL",
        "error": None,
        "patch": None,
        "runtime_ms": 0,
    }

    start_time = time.time()

    try:
        # Send task to white agent
        logger.info(f"Sending task {task_id} to white agent...")
        response = await send_message(
            url=white_agent_url,
            message=message,
            task_id=task_id,
            context_id=context_id,
            timeout=timeout,
        )

        # Parse response
        res_root = response.root
        if not isinstance(res_root, SendMessageSuccessResponse):
            result["error"] = "White agent returned non-success response"
            return result

        res_result = res_root.result

        # Extract text from response - handle both Message and Task types
        white_text = None

        if isinstance(res_result, Message):
            # Direct message response
            text_parts = get_text_parts(res_result.parts)
            if text_parts:
                white_text = text_parts[0]

        elif isinstance(res_result, Task):
            # Task response - extract from artifacts and status message
            text_content = []

            # Check artifacts
            if res_result.artifacts:
                for artifact in res_result.artifacts:
                    if artifact.parts:
                        parts_text = get_text_parts(artifact.parts)
                        text_content.extend(parts_text)

            # Check status message
            if res_result.status and res_result.status.message:
                status_text = get_text_parts(res_result.status.message.parts)
                text_content.extend(status_text)

            if text_content:
                white_text = '\n'.join(text_content)

        else:
            result["error"] = f"White agent returned unexpected response type: {type(res_result)}"
            return result

        if not white_text:
            result["error"] = "White agent returned empty response"
            return result

        logger.info(f"Received response from white agent for {task_id}")

        # Parse patch from response (expect <patch>...</patch> tags)
        tags = parse_tags(white_text)
        patch = tags.get("patch")

        if not patch:
            result["error"] = "White agent did not return a patch in <patch>...</patch> tags"
            logger.warning(f"No patch found in response for {task_id}")
            return result

        result["patch"] = patch
        logger.info(f"Extracted patch for {task_id} ({len(patch)} bytes)")

        # Evaluate the patch using SWE-bench harness
        logger.info(f"Running SWE-bench evaluation for {task_id}...")
        swebench_result = run_swebench_task(
            task_id=task_id,
            patch_diff=patch,
        )

        # Update result with evaluation metrics
        result["resolved"] = swebench_result.resolved
        result["verdict"] = swebench_result.verdict
        result["tests_passed"] = swebench_result.tests_passed
        result["total_tests"] = swebench_result.total_tests
        result["fail_to_pass"] = swebench_result.fail_to_pass
        result["fail_to_pass_total"] = swebench_result.fail_to_pass_total
        result["pass_to_pass"] = swebench_result.pass_to_pass
        result["pass_to_pass_total"] = swebench_result.pass_to_pass_total
        result["failure_type"] = swebench_result.failure_type
        result["logs"] = swebench_result.logs_text

    except Exception as e:
        logger.error(f"Error evaluating task {task_id}: {e}")
        result["error"] = str(e)

    result["runtime_ms"] = int((time.time() - start_time) * 1000)
    return result


class SWEBenchGreenAgentExecutor(AgentExecutor):
    """
    AgentExecutor for SWE-bench green agent.

    This executor:
    1. Receives task configuration from the platform
    2. Loads SWE-bench tasks from HuggingFace
    3. Sends problem statements to white agents (in parallel)
    4. Collects patches and evaluates them (in parallel)
    5. Reports metrics back to the platform

    Supports batch evaluation with configurable parallelism via max_workers.
    """

    def __init__(self):
        pass

    async def _evaluate_batch_parallel(
        self,
        tasks: list[dict],
        white_agent_url: str,
        timeout: float,
        max_workers: int,
        event_queue: EventQueue,
    ) -> list[dict]:
        """
        Evaluate multiple tasks in parallel with controlled concurrency.

        Args:
            tasks: List of task dicts to evaluate
            white_agent_url: URL of the white agent
            timeout: Timeout per task in seconds
            max_workers: Maximum number of parallel evaluations
            event_queue: Event queue for progress updates

        Returns:
            List of result dicts
        """
        semaphore = asyncio.Semaphore(max_workers)
        results = []
        completed = 0
        total = len(tasks)

        async def evaluate_with_semaphore(task: dict, index: int) -> dict:
            nonlocal completed
            async with semaphore:
                task_id = task["instance_id"]
                logger.info(f"Green agent: Starting task {index+1}/{total}: {task_id}")

                result = await evaluate_single_task(
                    white_agent_url=white_agent_url,
                    task=task,
                    timeout=timeout,
                )

                completed += 1
                status = "PASS" if result.get("resolved") else "FAIL"
                logger.info(f"Green agent: Completed {completed}/{total}: {task_id} {status}")

                # Send progress update periodically (every 5 tasks or on completion)
                if completed % 5 == 0 or completed == total:
                    await event_queue.enqueue_event(
                        new_agent_text_message(
                            f"Progress: {completed}/{total} tasks completed..."
                        )
                    )

                return result

        # Create tasks for all evaluations
        evaluation_tasks = [
            evaluate_with_semaphore(task, i)
            for i, task in enumerate(tasks)
        ]

        # Run all evaluations with controlled concurrency
        results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_id = tasks[i]["instance_id"]
                logger.error(f"Task {task_id} failed with exception: {result}")
                processed_results.append({
                    "task_id": task_id,
                    "resolved": False,
                    "verdict": "FAIL",
                    "error": str(result),
                    "runtime_ms": 0,
                })
            else:
                processed_results.append(result)

        return processed_results

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the SWE-bench evaluation task."""
        logger.info("Green agent: Received a task, parsing...")
        start_time = time.time()

        # Parse the task configuration from the user input
        user_input = context.get_user_input()
        tags = parse_tags(user_input)

        # Extract required fields
        white_agent_url = tags.get("white_agent_url")
        if not white_agent_url:
            await event_queue.enqueue_event(
                new_agent_text_message("Error: Missing <white_agent_url> in task configuration")
            )
            return

        # Parse task config
        task_config_str = tags.get("task_config", "{}")
        try:
            task_config = json.loads(task_config_str)
        except json.JSONDecodeError as e:
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error: Invalid JSON in <task_config>: {e}")
            )
            return

        # Extract configuration
        dataset = task_config.get("dataset", "verified")
        task_ids = task_config.get("task_ids", None)
        timeout = task_config.get("timeout", 600)
        max_workers = task_config.get("max_workers", DEFAULT_MAX_WORKERS)

        logger.info(
            f"Green agent: Configuration - dataset={dataset}, "
            f"task_ids={task_ids}, timeout={timeout}, max_workers={max_workers}"
        )

        # Load SWE-bench tasks
        logger.info("Green agent: Loading SWE-bench tasks...")
        tasks = load_swebench_tasks(dataset=dataset, task_ids=task_ids)

        if not tasks:
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error: No tasks found for dataset={dataset}, task_ids={task_ids}")
            )
            return

        total_tasks = len(tasks)
        logger.info(f"Green agent: Loaded {total_tasks} tasks, evaluating with {max_workers} workers")

        await event_queue.enqueue_event(
            new_agent_text_message(
                f"Starting evaluation of {total_tasks} tasks with {max_workers} parallel workers..."
            )
        )

        # Evaluate tasks in parallel
        if total_tasks == 1:
            # Single task - no parallelism needed
            results = [await evaluate_single_task(
                white_agent_url=white_agent_url,
                task=tasks[0],
                timeout=timeout,
            )]
        else:
            # Multiple tasks - use parallel evaluation
            results = await self._evaluate_batch_parallel(
                tasks=tasks,
                white_agent_url=white_agent_url,
                timeout=timeout,
                max_workers=max_workers,
                event_queue=event_queue,
            )

        # Calculate metrics
        total_runtime_ms = int((time.time() - start_time) * 1000)
        resolved_count = sum(1 for r in results if r.get("resolved"))
        failed_count = sum(1 for r in results if not r.get("resolved") and not r.get("error"))
        error_count = sum(1 for r in results if r.get("error"))
        resolution_rate = (resolved_count / total_tasks * 100) if total_tasks > 0 else 0

        # Build summary
        summary = f"""
SWE-bench Evaluation Complete

Configuration:
  Dataset: {dataset}
  Total tasks: {total_tasks}
  Max workers: {max_workers}

Results:
  Resolved: {resolved_count}/{total_tasks} ({resolution_rate:.1f}%)
  Failed: {failed_count}
  Errors: {error_count}
  Total runtime: {total_runtime_ms/1000:.1f}s
  Avg per task: {total_runtime_ms/total_tasks/1000:.1f}s

Details:
"""
        for r in results:
            status = "PASS" if r.get("resolved") else "FAIL"
            error_info = f" - {r['error']}" if r.get("error") else ""
            summary += f"  [{status}] {r['task_id']}: {r.get('verdict', 'FAIL')}{error_info}\n"

        logger.info("Green agent: Evaluation complete")
        await event_queue.enqueue_event(new_agent_text_message(summary))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the evaluation (not implemented)."""
        raise NotImplementedError


def start_green_agent(
    agent_name: str = "swebench_green_agent",
    host: str = "localhost",
    port: int = 9001,
    public_url: Optional[str] = None,
):
    """
    Start the SWE-bench green agent server.

    Args:
        agent_name: Name of the agent (must match TOML file name)
        host: Host to bind to
        port: Port to listen on
        public_url: Public URL for the agent card (e.g., Cloudflare tunnel URL)
    """
    import os

    logger.info(f"Starting SWE-bench green agent on {host}:{port}...")

    # Debug: log all environment variables containing agent/id
    logger.info("=== Environment variables ===")
    for key, value in os.environ.items():
        if any(x in key.lower() for x in ['agent', 'id', 'url', 'host', 'port', 'https', 'cloud']):
            logger.info(f"  {key}={value}")
    logger.info("=============================")

    agent_card_dict = load_agent_card_toml(agent_name)

    # AGENT_URL from controller takes highest priority (contains full path with agent ID)
    agent_url = os.environ.get("AGENT_URL")
    if agent_url:
        url = agent_url
        logger.info(f"Using AGENT_URL from env: {url}")
    elif public_url:
        url = public_url
        logger.info(f"Using provided public_url: {url}")
    else:
        # Fallback: construct from CLOUDRUN_HOST or host:port
        cloudrun_host = os.environ.get("CLOUDRUN_HOST")
        https_enabled = os.environ.get("HTTPS_ENABLED", "").lower() == "true"
        agent_id = os.environ.get("AGENT_ID") or os.environ.get("CAGENT_ID")

        if cloudrun_host:
            protocol = "https" if https_enabled else "http"
            url = f"{protocol}://{cloudrun_host}"
            if agent_id:
                url = f"{url}/to_agent/{agent_id}"
            logger.info(f"Constructed URL from env: {url}")
        else:
            url = f"http://{host}:{port}"
            logger.info(f"Using default URL: {url}")
    agent_card_dict["url"] = url
    logger.info(f"Agent card URL: {url}")

    import uuid
    # Generate a stable agent instance ID
    agent_instance_id = uuid.uuid4().hex[:32]

    request_handler = DefaultRequestHandler(
        agent_executor=SWEBenchGreenAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    a2a_app = A2AStarletteApplication(
        agent_card=AgentCard(**agent_card_dict),
        http_handler=request_handler,
    )

    # Build the Starlette app and add AgentBeats-required endpoints
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def status_endpoint(_request):
        """Health check endpoint for AgentBeats platform."""
        return JSONResponse({
            "status": "ok",
            "agent": agent_name,
            "running_agents": 1,
            "maintained_agents": 1,
            "agents": [
                {
                    "id": agent_instance_id,
                    "status": "RUNNING",
                    "url": url,  # Platform will append /.well-known/agent-card.json
                }
            ]
        })

    async def info_endpoint(_request):
        """Controller info endpoint for AgentBeats platform."""
        return JSONResponse({
            "running_agents": 1,
            "maintained_agents": 1,
            "starting_command": "python main.py serve",
            "agents": [
                {
                    "id": agent_instance_id,
                    "status": "RUNNING",
                    "port": port,
                    "url": url,  # Platform will append /.well-known/agent-card.json
                }
            ]
        })

    async def agents_list_endpoint(_request):
        """List all agents for AgentBeats platform."""
        return JSONResponse({
            "agents": [
                {
                    "id": agent_instance_id,
                    "url": url,  # Platform will append /.well-known/agent-card.json
                    "agent_card": agent_card_dict,  # Include full agent card
                    "status": "RUNNING",
                }
            ]
        })

    # Get the A2A app routes and add AgentBeats controller endpoints
    starlette_app = a2a_app.build()

    # Add CORS middleware to allow AgentBeats platform to fetch agent card
    from starlette.middleware.cors import CORSMiddleware
    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for AgentBeats platform
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add endpoint for agent-card.json (AgentBeats expects this path)
    async def agent_card_endpoint(_request):
        """Serve agent card at /.well-known/agent-card.json for AgentBeats."""
        return JSONResponse(agent_card_dict)

    # Add controller endpoints
    starlette_app.routes.append(Route("/status", status_endpoint, methods=["GET"]))
    starlette_app.routes.append(Route("/info", info_endpoint, methods=["GET"]))
    starlette_app.routes.append(Route("/agents", agents_list_endpoint, methods=["GET"]))
    starlette_app.routes.append(Route("/.well-known/agent-card.json", agent_card_endpoint, methods=["GET"]))

    logger.info(f"Agent instance ID: {agent_instance_id}")
    logger.info(f"Agent URL: {url}")
    logger.info(f"Agent card available at: {url}/.well-known/agent-card.json")

    uvicorn.run(starlette_app, host=host, port=port)

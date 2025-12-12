#!/usr/bin/env python3
"""
SWE-bench Green Agent CLI

A Green Agent for the AgentBeats platform that evaluates code patches
using the SWE-bench benchmark.

Usage:
    # Start the green agent server
    python main.py serve --port 9001

    # Run evaluation with a white agent
    python main.py evaluate --white-agent-url http://localhost:9002 --task-ids django__django-10914

    # Run the full launcher (starts green + sends task)
    python main.py launch --white-agent-url http://localhost:9002 --task-ids django__django-10914
"""

import asyncio
import typer
from typing import Optional

app = typer.Typer(
    name="swebench-green-agent",
    help="SWE-bench Green Agent for AgentBeats platform",
)


@app.command()
def serve(
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(9001, "--port", "-p", help="Port to listen on"),
    agent_name: str = typer.Option(
        "swebench_green_agent", "--name", "-n", help="Agent name (must match TOML file)"
    ),
):
    """Start the SWE-bench green agent A2A server."""
    from src.green_agent import start_green_agent

    typer.echo(f"Starting SWE-bench green agent on {host}:{port}...")
    start_green_agent(agent_name=agent_name, host=host, port=port)


@app.command()
def evaluate(
    white_agent_url: str = typer.Option(
        ..., "--white-agent-url", "-w", help="URL of the white agent to evaluate"
    ),
    dataset: str = typer.Option(
        "lite", "--dataset", "-d", help="SWE-bench dataset: lite, verified, or full"
    ),
    task_ids: Optional[str] = typer.Option(
        None, "--task-ids", "-t", help="Comma-separated task IDs (e.g., django__django-10914,astropy__astropy-6938)"
    ),
    timeout: int = typer.Option(600, "--timeout", help="Timeout per task in seconds"),
    green_url: str = typer.Option(
        "http://localhost:9001", "--green-url", "-g", help="URL of the green agent"
    ),
):
    """Send an evaluation task to a running green agent."""
    import json
    from src.green_agent.a2a_utils import send_message, wait_agent_ready

    async def run_evaluation():
        # Wait for green agent to be ready
        typer.echo(f"Waiting for green agent at {green_url}...")
        if not await wait_agent_ready(green_url, timeout=30):
            typer.echo("Error: Green agent not ready", err=True)
            raise typer.Exit(1)
        typer.echo("Green agent is ready.")

        # Build task config
        task_config = {
            "dataset": dataset,
            "timeout": timeout,
        }
        if task_ids:
            task_config["task_ids"] = [t.strip() for t in task_ids.split(",")]

        # Build task message
        task_message = f"""Your task is to run SWE-bench evaluation for the agent located at:
<white_agent_url>
{white_agent_url}
</white_agent_url>
You should use the following task configuration:
<task_config>
{json.dumps(task_config, indent=2)}
</task_config>
"""
        typer.echo("Sending evaluation task to green agent...")
        typer.echo(f"Task config: {json.dumps(task_config)}")

        response = await send_message(green_url, task_message, timeout=timeout * 10)
        typer.echo(f"Response: {response}")

    asyncio.run(run_evaluation())


@app.command()
def launch(
    white_agent_url: str = typer.Option(
        ..., "--white-agent-url", "-w", help="URL of the white agent to evaluate"
    ),
    dataset: str = typer.Option(
        "lite", "--dataset", "-d", help="SWE-bench dataset: lite, verified, or full"
    ),
    task_ids: Optional[str] = typer.Option(
        None, "--task-ids", "-t", help="Comma-separated task IDs"
    ),
    timeout: int = typer.Option(600, "--timeout", help="Timeout per task in seconds"),
    green_host: str = typer.Option("localhost", "--green-host", help="Green agent host"),
    green_port: int = typer.Option(9001, "--green-port", help="Green agent port"),
):
    """Launch the green agent and send an evaluation task."""
    import json
    import multiprocessing
    from src.green_agent import start_green_agent
    from src.green_agent.a2a_utils import send_message, wait_agent_ready

    async def run_launch():
        green_url = f"http://{green_host}:{green_port}"

        # Start green agent in a subprocess
        typer.echo(f"Launching green agent at {green_url}...")
        p_green = multiprocessing.Process(
            target=start_green_agent,
            args=("swebench_green_agent", green_host, green_port),
        )
        p_green.start()

        try:
            # Wait for green agent to be ready
            if not await wait_agent_ready(green_url, timeout=60):
                typer.echo("Error: Green agent failed to start", err=True)
                raise typer.Exit(1)
            typer.echo("Green agent is ready.")

            # Build task config
            task_config = {
                "dataset": dataset,
                "timeout": timeout,
            }
            if task_ids:
                task_config["task_ids"] = [t.strip() for t in task_ids.split(",")]

            # Build task message
            task_message = f"""Your task is to run SWE-bench evaluation for the agent located at:
<white_agent_url>
{white_agent_url}
</white_agent_url>
You should use the following task configuration:
<task_config>
{json.dumps(task_config, indent=2)}
</task_config>
"""
            typer.echo("Sending evaluation task to green agent...")
            typer.echo(f"White agent URL: {white_agent_url}")
            typer.echo(f"Task config: {json.dumps(task_config)}")

            response = await send_message(green_url, task_message, timeout=timeout * len(task_config.get("task_ids", [1])) + 300)
            typer.echo(f"\nEvaluation complete!")
            typer.echo(f"Response: {response}")

        finally:
            typer.echo("Terminating green agent...")
            p_green.terminate()
            p_green.join()
            typer.echo("Done.")

    asyncio.run(run_launch())


@app.command()
def status():
    """Check environment readiness for SWE-bench evaluation."""
    from src.harness.swebench_runner import SWEBENCH_AVAILABLE, check_swebench_available
    from src.harness.sandbox import Sandbox

    typer.echo("Checking SWE-bench environment...\n")

    # Check Docker
    docker_available, docker_message = Sandbox.check_docker_available()
    docker_status = "[OK]" if docker_available else "[FAIL]"
    typer.echo(f"{docker_status} Docker: {docker_message}")

    # Check SWE-bench
    swebench_available, swebench_message = check_swebench_available()
    swebench_status = "[OK]" if swebench_available else "[FAIL]"
    typer.echo(f"{swebench_status} SWE-bench: {swebench_message}")

    # Check A2A SDK
    try:
        import a2a
        a2a_status = "[OK]"
        a2a_message = f"a2a-sdk version {getattr(a2a, '__version__', 'unknown')}"
    except ImportError:
        a2a_status = "[FAIL]"
        a2a_message = "a2a-sdk not installed"
    typer.echo(f"{a2a_status} A2A SDK: {a2a_message}")

    # Check datasets
    try:
        import datasets
        datasets_status = "[OK]"
        datasets_message = f"datasets version {datasets.__version__}"
    except ImportError:
        datasets_status = "[FAIL]"
        datasets_message = "datasets not installed"
    typer.echo(f"{datasets_status} Datasets: {datasets_message}")

    # Overall readiness
    typer.echo("")
    if docker_available and swebench_available:
        typer.echo("[OK] Ready for SWE-bench evaluation")
    else:
        typer.echo("[FAIL] Not ready - please install missing dependencies")


if __name__ == "__main__":
    app()

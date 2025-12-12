# SWE-Bench Green Agent

A Green Agent for the AgentBeats platform that evaluates code patches using the SWE-Bench benchmark. Acts as an orchestrator that sends tasks to white agents, collects their patches, and evaluates them objectively.

## Overview

This Green Agent:
- **Orchestrates** SWE-bench evaluations by calling white agents with problem descriptions
- **Collects** patches from white agent responses
- **Evaluates** patches using Docker-based test execution
- **Reports** deterministic verdicts (PASS/FAIL) with detailed metrics
- **Supports** the full SWE-bench suite (Lite: 300, Verified: 500, Full: 2294 tasks)

### Green vs White Agents (AgentBeats Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgentBeats Platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  AgentBeats      │ Task    │  Green Agent     │             │
│  │  Platform        │────────▶│  (This Repo)     │             │
│  └──────────────────┘         └────────┬─────────┘             │
│                                        │                        │
│                               Problem  │  Calls white agent     │
│                               Statement│  with task details     │
│                                        ▼                        │
│                               ┌──────────────────┐             │
│                               │  White Agent     │             │
│                               │  (Participant)   │             │
│                               │  - Claude        │             │
│                               │  - GPT-4         │             │
│                               │  - Custom Agent  │             │
│                               └────────┬─────────┘             │
│                                        │                        │
│                               Patch    │  Returns unified diff  │
│                               Response │  in <patch> tags       │
│                                        ▼                        │
│                               ┌──────────────────┐             │
│                               │  Green Agent     │             │
│                               │  Evaluates in    │             │
│                               │  Docker + SWE-   │             │
│                               │  bench harness   │             │
│                               └────────┬─────────┘             │
│                                        │                        │
│                                        ▼                        │
│                               ┌──────────────────┐             │
│                               │ Objective Score  │             │
│                               │  PASS or FAIL    │             │
│                               └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

- **Green Agents** (judges/orchestrators): Send problem descriptions to white agents, collect patches, evaluate them
- **White Agents** (participants): Receive problem descriptions, generate code patches to fix bugs

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/swebench-green-agent.git
cd swebench-green-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Check Environment

```bash
python main.py status
```

Expected output:
```
Checking SWE-bench environment...

[OK] Docker: Docker is available and running
[OK] SWE-bench: SWE-bench version 4.1.0 is available
[OK] A2A SDK: a2a-sdk version 0.3.20
[OK] Datasets: datasets version 4.4.1

[OK] Ready for SWE-bench evaluation
```

### Running the Green Agent

#### Option 1: A2A Mode (AgentBeats Compatible)

```bash
# Start the A2A green agent server
python main.py serve --port 9001
```

The agent will be available at `http://localhost:9001` with:
- Agent card at `/.well-known/agent-card.json`
- A2A JSON-RPC endpoint for receiving tasks

## CLI Commands

```bash
python main.py --help
```

| Command | Description |
|---------|-------------|
| `serve` | Start the A2A green agent server |
| `evaluate` | Send evaluation task to a running green agent |
| `launch` | Start green agent and send task in one command |
| `status` | Check environment readiness |

### Examples

```bash
# Start A2A server
python main.py serve --host localhost --port 9001

# Check environment
python main.py status

# Launch evaluation (starts green agent + sends task)
python main.py launch \
  --white-agent-url http://localhost:9002 \
  --task-ids django__django-10914 \
  --dataset lite
```

## Architecture

### Project Structure

```
swebench-green-agent/
├── main.py                           # CLI entry point
├── requirements.txt                  # Dependencies
├── src/
│   ├── green_agent/                  # A2A SDK implementation
│   │   ├── __init__.py
│   │   ├── executor.py               # SWEBenchGreenAgentExecutor
│   │   ├── a2a_utils.py              # A2A communication utilities
│   │   └── swebench_green_agent.toml # Agent card configuration
│   ├── core/                         # Configuration & utilities
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── utils.py
│   └── harness/                      # SWE-bench evaluation core
│       ├── swebench_runner.py        # SWE-bench harness integration
│       └── sandbox.py                # Docker sandbox management
├── examples/                         # Example scripts
│   ├── mock_white_agent.py           # Mock white agent for testing
│   ├── test_orchestration.py         # Full orchestration test
│   ├── test_a2a_flow.py              # A2A communication test
│   └── test_batch_parallel.py        # Batch parallel test
├── tests/
│   └── test_swebench_integration.py
└── data/
    └── swebench_cache/               # Dataset cache
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **CLI** | Command-line interface | `main.py` |
| **A2A Executor** | AgentBeats-compatible orchestrator | `src/green_agent/executor.py` |
| **A2A Utils** | Communication with white agents | `src/green_agent/a2a_utils.py` |
| **SWE-bench Runner** | Docker-based test execution | `src/harness/swebench_runner.py` |
| **Sandbox** | Docker container management | `src/harness/sandbox.py` |

## A2A Protocol (AgentBeats Mode)

### Task Format

The green agent receives tasks with XML-like tags:

```xml
Your task is to run SWE-bench evaluation for the agent located at:
<white_agent_url>
http://localhost:9002/
</white_agent_url>
You should use the following task configuration:
<task_config>
{
  "dataset": "verified",
  "task_ids": null,
  "timeout": 600,
  "max_workers": 8
}
</task_config>
```

### Task Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `dataset` | SWE-bench dataset: `lite`, `verified`, or `full` | `lite` |
| `task_ids` | List of specific task IDs, or `null` for all | `null` |
| `timeout` | Timeout per task in seconds | `600` |
| `max_workers` | Parallel evaluation workers | `4` |

### Batch Evaluation

The green agent supports **parallel batch evaluation** for efficiently processing the full SWE-bench suite:

- **Parallel white agent calls**: Multiple tasks sent to white agent concurrently
- **Parallel Docker evaluation**: Multiple patches evaluated in parallel
- **Configurable concurrency**: Set `max_workers` based on your resources
- **Progress updates**: Real-time progress reported to platform

Example for full SWE-bench Verified (500 tasks):
```json
{
  "dataset": "verified",
  "task_ids": null,
  "timeout": 600,
  "max_workers": 8
}
```

Estimated times with 8 workers:
| Dataset | Tasks | Est. Time |
|---------|-------|-----------|
| Lite | 300 | ~30-60 min |
| Verified | 500 | ~1-2 hours |
| Full | 2,294 | ~4-8 hours |

### White Agent Response Format

White agents must return patches in `<patch>` tags:

```xml
Here's the fix for the issue:

<patch>
diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -303,6 +303,7 @@ def configure(self):
+    # Fix for issue 10914
     self.configured = True
</patch>
```

### Evaluation Flow

1. Green agent receives task from AgentBeats platform
2. Loads SWE-bench task data from HuggingFace
3. Sends problem statement to white agent via A2A
4. Parses `<patch>` from white agent response
5. Evaluates patch using Docker + SWE-bench harness
6. Reports metrics back to platform

## SWE-bench Datasets

| Dataset | Tasks | HuggingFace ID |
|---------|-------|----------------|
| Lite | 300 | `princeton-nlp/SWE-bench_Lite` |
| Verified | 500 | `princeton-nlp/SWE-bench_Verified` |
| Full | 2,294 | `princeton-nlp/SWE-bench` |

## Configuration

### Environment Variables

```bash
# SWE-bench settings
export SWEBENCH_DATASET_SPLIT=lite      # lite, verified, or test
export SWEBENCH_TIMEOUT_SECONDS=600     # Per-task timeout
export SWEBENCH_MAX_WORKERS=4           # Parallel workers for batch
export SWEBENCH_MAX_BATCH_SIZE=500      # Max tasks per batch
export SWEBENCH_DOCKER_NAMESPACE=swebench
```

## Development

### Local Testing

Test the full orchestration locally with the mock white agent:

```bash
# Option 1: Automated test (recommended)
python -m examples.test_orchestration --skip-eval

# Option 2: Manual testing (three terminals)

# Terminal 1 - Mock white agent
python -m examples.mock_white_agent --port 9002

# Terminal 2 - Green agent
python main.py serve --port 9001

# Terminal 3 - Send task
python main.py evaluate \
  --white-agent-url http://localhost:9002 \
  --task-ids django__django-10914 \
  --dataset lite
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src tests/
```

### Requirements

- Python 3.11+
- Docker (for SWE-bench evaluation)
- ~100MB disk space (excluding venv)

### Dependencies

Key packages:
- `a2a-sdk[http-server]>=0.3.8` - A2A protocol
- `swebench>=2.1.0` - SWE-bench harness
- `datasets>=2.0.0` - HuggingFace datasets
- `typer>=0.19.2` - CLI framework

## License

MIT License - see [LICENSE](LICENSE) file for details.

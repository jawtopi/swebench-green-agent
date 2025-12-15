# SWE-Bench Green Agent

A Green Agent for the AgentBeats platform that evaluates code patches using the SWE-Bench benchmark. Acts as an orchestrator that sends tasks to white agents, collects their patches, and evaluates them objectively using Docker-based test execution.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Running White and Green Agents](#running-white-and-green-agents)
- [Testing Green Agent Evaluation](#testing-green-agent-evaluation)
- [Reproducing Benchmark Results](#reproducing-benchmark-results)
- [Running on AgentBeats](#running-on-agentbeats)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Metrics and Evaluation](#metrics-and-evaluation)

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
│                               └────────┬─────────┘             │
│                                        │                        │
│                               Patch    │  Returns unified diff  │
│                               Response │  in <patch> tags       │
│                                        ▼                        │
│                               ┌──────────────────┐             │
│                               │  SWE-bench       │             │
│                               │  Docker Harness  │             │
│                               └────────┬─────────┘             │
│                                        │                        │
│                                        ▼                        │
│                               ┌──────────────────┐             │
│                               │ Objective Score  │             │
│                               │  PASS or FAIL    │             │
│                               └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (required for SWE-bench evaluation)
- ~100MB disk space

### Installation

```bash
# Clone the repository
git clone https://github.com/jawtopi/swebench-green-agent.git
cd swebench-green-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Verify Environment

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

## Running White and Green Agents

### Local Testing (3 Terminals)

**Terminal 1 - Start White Agent:**
```bash
# Navigate to your white agent repository
cd /path/to/white-agent
python main.py serve --port 9002
```

The white agent must be A2A-compatible and return patches in `<patch>...</patch>` tags.

**Terminal 2 - Start Green Agent:**
```bash
cd /path/to/swebench-green-agent
python main.py serve --port 9001
```

**Terminal 3 - Run Evaluation:**
```bash
# Single task evaluation
python main.py evaluate \
  --white-agent-url http://localhost:9002 \
  --green-url http://localhost:9001 \
  --task-ids django__django-10914 \
  --dataset verified

# Batch evaluation (10 random tasks)
python main.py evaluate \
  --white-agent-url http://localhost:9002 \
  --green-url http://localhost:9001 \
  --dataset verified
```

### Combined Launch Command

Start green agent and run evaluation in one command:

```bash
python main.py launch \
  --white-agent-url http://localhost:9002 \
  --task-ids django__django-10914 \
  --dataset verified
```

## Testing Green Agent Evaluation

We provide a validation script to test that the green agent produces accurate evaluation results.

### Run Validation Tests

```bash
# Ensure Docker is running
docker ps

# Run the validation script
python scripts/validate_green_agent.py
```

### Test Cases

The validation script tests three scenarios:

| Test Case | Input | Expected Result |
|-----------|-------|-----------------|
| Partial Fix | Patch that applies but doesn't fix bug | FAIL (test_failure) |
| Empty Patch | No patch content | FAIL |
| Malformed Patch | Invalid file/line references | FAIL (apply_error) |

Expected output:
```
============================================================
GREEN AGENT VALIDATION
============================================================

Test Case 1: Partial fix patch (applies but doesn't fix bug)
  Verdict: FAIL
  Expected: FAIL (patch applies but tests still fail)

Test Case 2: Empty patch for django__django-10914
  Verdict: FAIL
  Expected: FAIL (no fix applied)

Test Case 3: Malformed patch (wrong file/lines)
  Verdict: FAIL
  Expected: FAIL (apply_error)

============================================================
VALIDATION SUMMARY
============================================================
  Partial Patch: FAIL (expected FAIL) - MATCH
  Empty Patch: FAIL (expected FAIL) - MATCH
  Malformed Patch: FAIL (expected FAIL) - MATCH

All validation tests passed!
```

### Run Unit Tests

```bash
pytest tests/test_swebench_integration.py -v
```

## Reproducing Benchmark Results

Our implementation uses the official SWE-bench harness, ensuring reproducible results.

### Verify Harness Reproducibility

```bash
# Test with a known task
python main.py launch \
  --white-agent-url http://localhost:9002 \
  --task-ids django__django-10914 \
  --dataset verified
```

The evaluation uses:
- Official `swebench` Python package (v4.1.0)
- Official SWE-bench Docker images
- Identical test execution as the SWE-bench leaderboard

### Compare with Published Results

Results can be compared against the [SWE-bench Leaderboard](https://www.swebench.com/). Our green agent produces identical pass/fail verdicts for the same patches because we use the unmodified official harness.

## Running on AgentBeats

### Option 1: Cloudflare Tunnel (Recommended)

Run locally with Docker and expose via Cloudflare tunnel:

**Terminal 1 - Start Cloudflare Tunnel:**
```bash
# Install cloudflared if needed: brew install cloudflared
cloudflared tunnel --url http://localhost:8010
```
Note the URL (e.g., `https://random-words.trycloudflare.com`)

**Terminal 2 - Start Green Agent:**
```bash
export CLOUDRUN_HOST="random-words.trycloudflare.com"  # Without https://
export HTTPS_ENABLED="true"
export HOST="0.0.0.0"

agentbeats run_ctrl
```

Then register your agent on AgentBeats using the Cloudflare tunnel URL.

### Option 2: Cloud Deployment (Railway)

Deploy to Railway or similar platform:

```bash
# Set environment variables in Railway dashboard:
# CLOUDRUN_HOST=your-railway-url.up.railway.app
# HTTPS_ENABLED=true

# The Dockerfile handles the rest
```

Note: Railway doesn't support Docker-in-Docker, so full SWE-bench evaluation requires the Cloudflare tunnel approach.

### AgentBeats Configuration

Default evaluation settings:
- **Sample Size**: 10 random tasks from SWE-bench Verified
- **Parallel Workers**: 4
- **Timeout**: 600 seconds per task

These can be configured via the task_config sent to the green agent.

## Architecture

### Project Structure

```
swebench-green-agent/
├── main.py                           # CLI entry point
├── requirements.txt                  # Dependencies
├── Dockerfile                        # Container deployment
├── scripts/
│   └── validate_green_agent.py       # Validation test script
├── src/
│   ├── green_agent/
│   │   ├── executor.py               # Main evaluation logic
│   │   ├── a2a_utils.py              # A2A communication
│   │   └── swebench_green_agent.toml # Agent card config
│   ├── core/
│   │   ├── config.py                 # Configuration
│   │   └── logger.py                 # Logging
│   └── harness/
│       ├── swebench_runner.py        # SWE-bench integration
│       └── sandbox.py                # Docker management
└── tests/
    └── test_swebench_integration.py  # Unit tests
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| CLI | `main.py` | Command-line interface |
| Executor | `src/green_agent/executor.py` | Task orchestration and evaluation |
| A2A Utils | `src/green_agent/a2a_utils.py` | White agent communication |
| SWE-bench Runner | `src/harness/swebench_runner.py` | Docker-based test execution |

## Configuration

### CLI Commands

| Command | Description |
|---------|-------------|
| `serve` | Start the A2A green agent server |
| `evaluate` | Send evaluation task to a running green agent |
| `launch` | Start green agent and send task in one command |
| `status` | Check environment readiness |

### Task Configuration

```json
{
  "dataset": "verified",
  "task_ids": ["django__django-10914"],
  "timeout": 600,
  "max_workers": 4,
  "sample_size": 10
}
```

| Field | Description | Default |
|-------|-------------|---------|
| `dataset` | `lite` (300), `verified` (500), or `full` (2294) | `verified` |
| `task_ids` | Specific tasks or `null` for random sample | `null` |
| `timeout` | Seconds per task | `600` |
| `max_workers` | Parallel workers | `4` |
| `sample_size` | Random tasks when task_ids is null | `10` |

### Environment Variables

```bash
export SWEBENCH_TIMEOUT_SECONDS=600
export SWEBENCH_MAX_WORKERS=4
export SWEBENCH_DOCKER_NAMESPACE=swebench
```

## Metrics and Evaluation

### Primary Metric: Resolution Rate

```
Resolution Rate = (Resolved Tasks / Total Tasks) × 100%
```

A task is **resolved** when:
1. Patch applies cleanly (`git apply` succeeds)
2. All FAIL_TO_PASS tests pass (bug is fixed)
3. All PASS_TO_PASS tests pass (no regressions)

### Detailed Metrics

| Metric | Description |
|--------|-------------|
| `resolved` | Boolean - did the patch fix the bug? |
| `verdict` | PASS or FAIL |
| `fail_to_pass` | Tests fixed by the patch |
| `pass_to_pass` | Tests that didn't regress |
| `failure_type` | `apply_error`, `build_error`, `test_failure`, or `null` |
| `runtime_ms` | Evaluation time in milliseconds |

### Example Output

```
============================================================
GREEN AGENT: EVALUATION COMPLETE
============================================================
Dataset: verified
Total tasks: 10
Resolved: 1/10 (10.0%)
Failed: 8
Errors: 1
Total runtime: 245.3s
Avg per task: 24.5s
============================================================
```

## White Agent Requirements

White agents must:

1. Accept A2A protocol messages
2. Return patches in `<patch>...</patch>` tags
3. Use unified diff format

Example response:
```
<patch>
diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -10,7 +10,7 @@
-    old_line
+    new_line
</patch>
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

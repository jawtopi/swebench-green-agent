# SWE-Bench Green Agent

A Green Agent for the AgentBeats platform that evaluates code patches using the SWE-Bench benchmark. Acts as an orchestrator that sends tasks to white agents, collects their patches, and evaluates them objectively using Docker-based test execution.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Running White and Green Agents](#running-white-and-green-agents)
- [Testing Green Agent Evaluation](#testing-green-agent-evaluation)
- [Reproducing Benchmark Results](#reproducing-benchmark-results)
- [Running on AgentBeats](#running-on-agentbeats)
- [GCP VM Deployment Guide](#gcp-vm-deployment-guide)
- [Demo Script](#demo-script)
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

# Batch evaluation (5 random tasks)
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

We provide multiple scripts to test that the green agent produces accurate evaluation results.

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

### Option 1: Cloudflare Tunnel (Quick Testing)

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

**Note:** Cloudflare tunnels have a 100-second timeout limit which may cause issues with long-running evaluations. For production use, see the GCP VM deployment below.

### Option 2: GCP VM Deployment (Recommended for Production)

See [GCP VM Deployment Guide](#gcp-vm-deployment-guide) for detailed instructions on setting up a VM with Docker support and proper timeout configuration.

### AgentBeats Configuration

Default evaluation settings (optimized for AgentBeats platform):
- **Sample Size**: 5 random tasks from SWE-bench Verified
- **Parallel Workers**: 1 (to avoid overwhelming white agent)
- **Timeout**: 600 seconds per task

These can be configured via the task_config sent to the green agent.

## GCP VM Deployment Guide

For production AgentBeats deployment, we recommend using a GCP Compute Engine VM to avoid Cloudflare tunnel timeout limitations.

### Prerequisites

- GCP account with Compute Engine enabled
- A domain name (for SSL certificate)
- SSH access configured

### Step 1: Create VM Instance

```bash
# Create VM via gcloud CLI
gcloud compute instances create swebench-green-agent \
  --project=YOUR_PROJECT_ID \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced
```

Or use the GCP Console:
- **Machine type**: e2-standard-4 (4 vCPU, 16GB RAM) or larger
- **OS**: Ubuntu 22.04 LTS
- **Disk**: 100GB SSD
- **Firewall**: Allow HTTP (80) and HTTPS (443)

### Step 2: Install Dependencies

SSH into the VM and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker works
docker run hello-world

# Install Python 3.11+ dependencies
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Clone repository
git clone https://github.com/jawtopi/swebench-green-agent.git
cd swebench-green-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python main.py status
```

### Step 3: Configure Nginx with SSL

```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/swebench << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Extended timeouts for long-running evaluations
        proxy_read_timeout 3600s;
        proxy_connect_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/swebench /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d YOUR_DOMAIN.com
```

### Step 4: Configure DNS

Point your domain to the VM's external IP:
- Create an A record pointing to your VM's external IP address

### Step 5: Create Startup Script

```bash
# Create run.sh
cat > ~/swebench-green-agent/run.sh << 'EOF'
#!/bin/bash
cd ~/swebench-green-agent
source venv/bin/activate
python main.py serve --host 0.0.0.0 --port ${AGENT_PORT:-8010}
EOF
chmod +x ~/swebench-green-agent/run.sh
```

### Step 6: Run the Green Agent

```bash
# Set environment variables
export CLOUDRUN_HOST="YOUR_DOMAIN.com"
export HTTPS_ENABLED="true"
export HOST="0.0.0.0"
export AGENT_PORT="8010"

# Start the agent
cd ~/swebench-green-agent
./run.sh
```

Or run with agentbeats controller:
```bash
agentbeats run_ctrl
```

### Step 7: Register on AgentBeats

1. Go to the AgentBeats platform
2. Register your green agent with URL: `https://YOUR_DOMAIN.com`
3. The platform will discover your agent via `/.well-known/agent-card.json`

### Troubleshooting VM Deployment

| Issue | Solution |
|-------|----------|
| 504 Gateway Timeout | Increase nginx proxy_read_timeout |
| White agent 503 errors | Reduce max_workers to 1 |
| Docker permission denied | Run `sudo usermod -aG docker $USER` and re-login |
| SSL certificate issues | Run `sudo certbot renew --dry-run` |

## Demo Script

We provide an interactive demo script that showcases different evaluation scenarios.

### Running the Demo

```bash
python scripts/demo_examples.py
```

### Demo Scenarios

The demo walks through 5 evaluation examples:

| Example | Type | Expected Result | Description |
|---------|------|-----------------|-------------|
| 1 | Gold Patch | PASS | Official django__django-10914 patch from SWE-bench |
| 2 | Gold Patch | PASS | Official django__django-16493 patch from SWE-bench |
| 3 | Malformed | FAIL (apply_error) | Text explanation instead of valid diff |
| 4 | Wrong Value | FAIL (test_failure) | Patch applies but uses wrong value (0o755 vs 0o644) |
| 5 | Empty | FAIL | No patch provided |

The demo uses real gold patches fetched from the SWE-bench dataset (`princeton-nlp/SWE-bench_Verified`) to ensure accurate PASS results.

### Demo Output

```
╔══════════════════════════════════════════════════════════════════════╗
║           SWE-bench Green Agent - Evaluation Demo                    ║
║   Using REAL gold patches from SWE-bench dataset!                    ║
╚══════════════════════════════════════════════════════════════════════╝

Press Enter to start Example 1 (Gold Patch PASS)...

======================================================================
  EXAMPLE 1: PASS - Django File Upload Permissions (Gold Patch)
======================================================================

Task: django__django-10914
Issue: Set default FILE_UPLOAD_PERMISSION to 0o644
Repository: django/django

>>> Gold Patch Content (from SWE-bench)
diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
...

>>> Evaluation Results
  Verdict:        PASS
  Resolved:       True
  FAIL→PASS:      2/2 tests fixed
  PASS→PASS:      1/1 tests still pass
  Runtime:        45.2s

✓ RESULT: PASS
  Gold patch from SWE-bench correctly fixes the bug!
```

## Architecture

### Project Structure

```
swebench-green-agent/
├── main.py                           # CLI entry point
├── requirements.txt                  # Dependencies
├── Dockerfile                        # Container deployment
├── run.sh                            # Startup script
├── scripts/
│   ├── validate_green_agent.py       # Validation test script
│   └── demo_examples.py              # Interactive demo script
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
  "max_workers": 1,
  "sample_size": 5
}
```

| Field | Description | Default |
|-------|-------------|---------|
| `dataset` | `lite` (300), `verified` (500), or `full` (2294) | `verified` |
| `task_ids` | Specific tasks or `null` for random sample | `null` |
| `timeout` | Seconds per task | `600` |
| `max_workers` | Parallel workers | `1` |
| `sample_size` | Random tasks when task_ids is null | `5` |

### Environment Variables

```bash
export SWEBENCH_TIMEOUT_SECONDS=600
export SWEBENCH_MAX_WORKERS=1
export SWEBENCH_DOCKER_NAMESPACE=swebench

# For AgentBeats deployment
export CLOUDRUN_HOST="your-domain.com"
export HTTPS_ENABLED="true"
export HOST="0.0.0.0"
export AGENT_PORT="8010"
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
Total tasks: 5
Resolved: 1/5 (20.0%)
Failed: 3
Errors: 1
Total runtime: 245.3s
Avg per task: 49.1s
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

## Repository

- **GitHub**: https://github.com/jawtopi/swebench-green-agent
- **Branch**: main

## License

MIT License - see [LICENSE](LICENSE) file for details.

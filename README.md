# SWE-Bench Green Agent

A Green Agent for the AgentBeats platform that evaluates code patches using the SWE-Bench benchmark. Acts as an objective "judge" that determines whether a code patch correctly fixes a bug by running automated tests.

## Overview

This Green Agent:
- **Evaluates** code patches for correctness using automated tests
- **Exposes** A2A (Agent-to-Agent) protocol-inspired endpoints
- **Returns** deterministic verdicts (PASS/FAIL) with detailed metrics
- **Demonstrates** reproducible evaluation with sandbox isolation

### Green vs White Agents

- **White Agents** (participants): AI models that generate code patches to fix bugs
- **Green Agents** (judges): Services that evaluate those patches objectively

This is a Green Agent - it judges code quality, it doesn't write code.

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AgentBeats Ecosystem                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │ White Agent  │              │ Green Agent  │            │
│  │ (Participant)│              │   (Judge)    │            │
│  │              │              │              │            │
│  │ - GPT-4      │   Proposes   │ - SWE-Bench  │            │
│  │ - Claude     │─────Patch───▶│ - Evaluator  │            │
│  │ - Gemini     │              │ - This Repo  │            │
│  │              │              │              │            │
│  └──────────────┘              └──────────────┘            │
│                                       │                     │
│                                       ▼                     │
│                              ┌─────────────────┐            │
│                              │ Objective Score │            │
│                              │  PASS or FAIL   │            │
│                              └─────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Evaluation Workflow

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Input                                                │
│ ────────────────────────────────────────────────────────────│
│  POST /task                                                  │
│  {                                                           │
│    "task_id": "numpy-1234",        ← SWE-Bench task         │
│    "patch_choice": "good"          ← Code patch to test     │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Sandbox Creation                                     │
│ ────────────────────────────────────────────────────────────│
│  Create isolated environment: runs/numpy-1234-good/          │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Patch Application                                    │
│ ────────────────────────────────────────────────────────────│
│  Apply patch: data/tasks/numpy-1234/good.patch               │
│                                                              │
│  Success? ────No────▶ Return FAIL (apply_error)             │
│      │                                                       │
│     Yes                                                      │
│      │                                                       │
└──────┼──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Test Execution                                       │
│ ────────────────────────────────────────────────────────────│
│  Run automated test suite                                    │
│                                                              │
│  test_01 ... PASSED                                          │
│  test_02 ... PASSED                                          │
│  ...                                                         │
│  test_12 ... PASSED                                          │
│                                                              │
│  Result: 12/12 tests passed                                  │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: Verdict Determination                                │
│ ────────────────────────────────────────────────────────────│
│  IF tests_passed == total_tests:                             │
│      verdict = "PASS"                                        │
│  ELSE:                                                       │
│      verdict = "FAIL"                                        │
│      failure_type = "test_failure"                           │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 6: Output                                               │
│ ────────────────────────────────────────────────────────────│
│  {                                                           │
│    "task_id": "numpy-1234",                                  │
│    "tests_passed": 12,                                       │
│    "total_tests": 12,                                        │
│    "verdict": "PASS",                ← Objective result      │
│    "runtime_ms": 106,                                        │
│    "failure_type": null,                                     │
│    "logs_uri": "/logs/numpy-1234-good.txt"                   │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **FastAPI Server** | HTTP API with A2A endpoints | `src/app.py` |
| **Test Runner** | Orchestrates evaluation workflow | `src/harness/runner.py` |
| **Sandbox Manager** | Isolates each evaluation | `src/harness/sandbox.py` |
| **A2A Endpoints** | `/card`, `/reset`, `/task` | `src/a2a/` |
| **Demo Tasks** | Sample patches from SWE-Bench | `data/tasks/` |

## Features

✅ **A2A-Inspired Protocol** - Standard endpoints for agent discovery and task execution
✅ **Deterministic Evaluation** - Same patch always produces same verdict
✅ **Sandbox Isolation** - Each evaluation runs in isolated environment
✅ **Comprehensive Logging** - Detailed execution logs for every evaluation
✅ **Multiple Failure Modes** - Distinguishes between patch errors and test failures
✅ **Docker Support** - Containerized deployment ready

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/swebench-green-agent.git
cd swebench-green-agent

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Using make
make run

# Or directly with uvicorn
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

## Usage Examples

### 1. Get Agent Metadata

```bash
curl http://localhost:8000/card
```

**Response:**
```json
{
  "name": "SWE-Bench Green Agent",
  "description": "A minimal Green Agent for AgentBeats...",
  "model_type": "green",
  "protocol": "A2A",
  "version": "1.0.0",
  "capabilities": ["swe-bench", "patch-evaluation", "test-execution"]
}
```

### 2. Evaluate a Correct Patch (PASS)

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"task_id": "numpy-1234", "patch_choice": "good"}'
```

**Response:**
```json
{
  "task_id": "numpy-1234",
  "tests_passed": 12,
  "total_tests": 12,
  "verdict": "PASS",
  "runtime_ms": 106,
  "failure_type": null,
  "logs_uri": "/logs/numpy-1234-good.txt"
}
```

### 3. Evaluate an Incorrect Patch (FAIL)

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"task_id": "numpy-1234", "patch_choice": "bad"}'
```

**Response:**
```json
{
  "task_id": "numpy-1234",
  "tests_passed": 8,
  "total_tests": 12,
  "verdict": "FAIL",
  "runtime_ms": 105,
  "failure_type": "test_failure",
  "logs_uri": "/logs/numpy-1234-bad.txt"
}
```

### 4. View Execution Logs

```bash
curl http://localhost:8000/logs/numpy-1234-good.txt
```

### 5. Reset Environment

```bash
curl -X POST http://localhost:8000/reset
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service information |
| `/card` | GET | Agent metadata (A2A discovery) |
| `/reset` | POST | Clean environment for reproducibility |
| `/task` | POST | Evaluate a code patch |
| `/logs/{filename}` | GET | Retrieve execution logs |
| `/health` | GET | Health check |

## Demo Tasks

The project includes two demo SWE-Bench tasks with pre-made patches:

### Task 1: numpy-1234 (Array Indexing Bug)

**Bug:** Array slicing returns references instead of copies
**Tests:** 12 total

- **good.patch** → ✅ PASS (12/12 tests)
- **bad.patch** → ❌ FAIL (8/12 tests, `test_failure`)

### Task 2: django-5678 (Query Optimization)

**Bug:** QuerySet operations not using database indexes
**Tests:** 8 total

- **good.patch** → ✅ PASS (8/8 tests)
- **bad.patch** → ❌ FAIL (0/8 tests, `apply_error`)

## Verdict Logic

### PASS
All tests pass successfully.

### FAIL
One or more tests fail OR patch cannot be applied.

**Failure Types:**
- `apply_error` - Patch has formatting errors and won't apply to codebase
- `test_failure` - Patch applied successfully but tests failed

## Project Structure

```
swebench-green-agent/
├── src/
│   ├── app.py                 # FastAPI server & routes
│   ├── schemas.py             # Pydantic request/response models
│   ├── core/
│   │   ├── config.py          # Configuration & constants
│   │   ├── logger.py          # Logging setup
│   │   └── utils.py           # Helper utilities
│   ├── harness/
│   │   ├── runner.py          # Test execution engine
│   │   └── sandbox.py         # Sandbox isolation
│   └── a2a/
│       ├── card.py            # GET /card endpoint
│       ├── reset.py           # POST /reset endpoint
│       └── task.py            # POST /task endpoint
├── tests/
│   └── test_app.py            # Automated test suite (10 tests)
├── data/
│   └── tasks/                 # Demo SWE-Bench tasks
│       ├── numpy-1234/
│       └── django-5678/
├── logs/                      # Execution logs (generated)
├── runs/                      # Sandbox directories (generated)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
├── Makefile                   # Build commands
└── README.md                  # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test
pytest tests/test_app.py::test_card -v

# Run with coverage
pytest --cov=src tests/
```

**All 10 tests pass ✅**

### Available Commands

```bash
make venv          # Create virtual environment
make install       # Install dependencies
make run           # Start server
make test          # Run tests
make clean         # Clean logs and runs
make docker-build  # Build Docker image
make docker-run    # Run in Docker
```

### Docker

**Build:**
```bash
docker build -t swebench-green-agent .
```

**Run:**
```bash
docker run -p 8000:8000 swebench-green-agent
```

## Technical Details

### Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI 0.115+
- **Validation:** Pydantic 2.10+
- **Testing:** pytest 8.3+
- **Server:** Uvicorn with auto-reload

### Response Schema

```python
{
  "task_id": str,              # Task identifier
  "tests_passed": int,         # Number of passing tests
  "total_tests": int,          # Total number of tests
  "verdict": "PASS" | "FAIL",  # Overall result
  "runtime_ms": int,           # Execution time
  "failure_type": str | null,  # "apply_error" | "test_failure" | null
  "logs_uri": str              # Path to detailed logs
}
```

### Implementation Note

This is a **demo implementation** for the AgentBeats platform. The test execution is simulated with predetermined results for demonstration purposes. A production version would:

- Load real SWE-Bench JSON task definitions
- Clone actual repositories via git
- Run real pytest executions in Docker containers
- Parse actual test output

The **architecture and API design are production-ready**; only the test execution layer needs to be swapped from simulation to real execution.

## Requirements

- Python 3.11 or higher
- 100MB disk space (excluding venv)
- macOS, Linux, or Windows (WSL recommended)

## License

MIT License - see [LICENSE](LICENSE) file for details.

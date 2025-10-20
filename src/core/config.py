"""Configuration and constants."""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TASKS_DIR = DATA_DIR / "tasks"
LOGS_DIR = BASE_DIR / "logs"
RUNS_DIR = BASE_DIR / "runs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)

# Agent metadata
AGENT_NAME = "SWE-Bench Green Agent"
AGENT_DESCRIPTION = "A minimal Green Agent for AgentBeats that evaluates code patches using SWE-Bench"
AGENT_AUTHOR = "AgentBeats Demo"
AGENT_VERSION = "1.0.0"

# Execution settings
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_LOG_SIZE = 1024 * 1024  # 1MB

# Demo task configurations
DEMO_TASKS = {
    "numpy-1234": {
        "description": "Array indexing bug fix in NumPy",
        "total_tests": 12,
        "repo": "numpy/numpy",
        "good_pass": 12,
        "bad_pass": 8,
    },
    "django-5678": {
        "description": "Query optimization issue in Django ORM",
        "total_tests": 8,
        "repo": "django/django",
        "good_pass": 8,
        "bad_pass": 0,  # patch fails to apply
    },
}

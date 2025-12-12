"""Configuration and constants."""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
RUNS_DIR = BASE_DIR / "runs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)

# Agent metadata
AGENT_NAME = "SWE-Bench Green Agent"
AGENT_DESCRIPTION = (
    "A Green Agent for AgentBeats that evaluates code patches using the SWE-Bench harness. "
    "Orchestrates evaluation by calling white agents and running Docker-based tests."
)
AGENT_AUTHOR = "AgentBeats"
AGENT_VERSION = "2.0.0"

# Execution settings
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_LOG_SIZE = 1024 * 1024  # 1MB

# =============================================================================
# SWE-bench Configuration
# =============================================================================

# Dataset split to use: "verified", "test", "lite"
SWEBENCH_DATASET_SPLIT = os.getenv("SWEBENCH_DATASET_SPLIT", "verified")

# Docker namespace for SWE-bench task images
SWEBENCH_DOCKER_NAMESPACE = os.getenv("SWEBENCH_DOCKER_NAMESPACE", "swebench")

# Timeout for SWE-bench evaluation (seconds)
SWEBENCH_TIMEOUT_SECONDS = int(os.getenv("SWEBENCH_TIMEOUT_SECONDS", "600"))

# Whether to cache Docker containers between runs
SWEBENCH_CACHE_CONTAINERS = os.getenv("SWEBENCH_CACHE_CONTAINERS", "true").lower() == "true"

# =============================================================================
# Batch/Parallel Execution Configuration
# =============================================================================

# Maximum parallel workers for batch evaluation
SWEBENCH_MAX_WORKERS = int(os.getenv("SWEBENCH_MAX_WORKERS", "4"))

# Maximum tasks per batch request
SWEBENCH_MAX_BATCH_SIZE = int(os.getenv("SWEBENCH_MAX_BATCH_SIZE", "500"))

# Whether to force rebuild Docker images
SWEBENCH_FORCE_REBUILD = os.getenv("SWEBENCH_FORCE_REBUILD", "false").lower() == "true"

# Whether to clean up Docker images after evaluation
SWEBENCH_CLEAN_IMAGES = os.getenv("SWEBENCH_CLEAN_IMAGES", "false").lower() == "true"

# Path to cache downloaded datasets
SWEBENCH_CACHE_DIR = Path(os.getenv("SWEBENCH_CACHE_DIR", str(DATA_DIR / "swebench_cache")))
SWEBENCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

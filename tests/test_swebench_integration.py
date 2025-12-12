"""Tests for SWE-bench integration.

Tests the A2A-based executor and SWE-bench runner functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.harness.swebench_runner import SwebenchResult, run_swebench_task


# =============================================================================
# SwebenchResult Tests
# =============================================================================


def test_swebench_result_dataclass():
    """Test SwebenchResult dataclass creation."""
    result = SwebenchResult(
        task_id="test-task",
        verdict="PASS",
        tests_passed=5,
        total_tests=5,
        failure_type=None,
        runtime_ms=1000,
        logs_text="Test logs",
    )
    assert result.task_id == "test-task"
    assert result.verdict == "PASS"
    assert result.tests_passed == 5
    assert result.failure_type is None


def test_swebench_result_fail():
    """Test SwebenchResult dataclass with failure."""
    result = SwebenchResult(
        task_id="test-task",
        verdict="FAIL",
        tests_passed=3,
        total_tests=5,
        failure_type="test_failure",
        runtime_ms=2000,
        logs_text="Test failed",
    )
    assert result.verdict == "FAIL"
    assert result.tests_passed == 3
    assert result.total_tests == 5
    assert result.failure_type == "test_failure"


# =============================================================================
# SWE-bench Runner Tests
# =============================================================================


def test_swebench_runner_graceful_error():
    """Test graceful handling when SWE-bench evaluation fails."""
    with patch("src.harness.swebench_runner.SWEBENCH_AVAILABLE", True):
        with patch("src.harness.swebench_runner.get_dataset_from_preds") as mock_get:
            mock_get.side_effect = Exception("Dataset not found")

            result = run_swebench_task(
                task_id="test-task",
                patch_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-x\n+y",
            )

            assert result.verdict == "FAIL"
            assert result.failure_type == "unknown"


def test_swebench_runner_result_types():
    """Test SwebenchResult failure types."""
    # Test apply_error
    result = SwebenchResult(
        task_id="test-task",
        verdict="FAIL",
        tests_passed=0,
        total_tests=0,
        failure_type="apply_error",
        runtime_ms=500,
        logs_text="error: patch does not apply",
    )
    assert result.failure_type == "apply_error"

    # Test build_error
    result2 = SwebenchResult(
        task_id="test-task",
        verdict="FAIL",
        tests_passed=0,
        total_tests=0,
        failure_type="build_error",
        runtime_ms=1000,
        logs_text="compilation failed",
    )
    assert result2.failure_type == "build_error"


# =============================================================================
# A2A Utils Tests
# =============================================================================


def test_parse_tags():
    """Test XML-like tag parsing."""
    from src.green_agent.a2a_utils import parse_tags

    text = """
    Some text
    <tag1>value1</tag1>
    More text
    <tag2>value2</tag2>
    """

    tags = parse_tags(text)
    assert tags["tag1"] == "value1"
    assert tags["tag2"] == "value2"


def test_parse_tags_multiline():
    """Test parsing tags with multiline content."""
    from src.green_agent.a2a_utils import parse_tags

    text = """
    <patch>
    line1
    line2
    line3
    </patch>
    """

    tags = parse_tags(text)
    assert "line1" in tags["patch"]
    assert "line2" in tags["patch"]
    assert "line3" in tags["patch"]


def test_parse_tags_no_match():
    """Test parsing when no tags found."""
    from src.green_agent.a2a_utils import parse_tags

    text = "No tags here"
    tags = parse_tags(text)
    assert tags == {}


def test_format_swebench_task_message():
    """Test formatting SWE-bench task message."""
    from src.green_agent.a2a_utils import format_swebench_task_message

    message = format_swebench_task_message(
        task_id="django__django-10914",
        problem_statement="There is a bug...",
        repo="django/django",
        hints_text="Check the settings",
        base_commit="abc123",
    )

    assert "<task_id>" in message
    assert "django__django-10914" in message
    assert "<problem_statement>" in message
    assert "There is a bug..." in message
    assert "<repository>" in message
    assert "django/django" in message


# =============================================================================
# Executor Tests
# =============================================================================


def test_executor_parse_task_config():
    """Test executor task config parsing."""
    from src.green_agent.a2a_utils import parse_tags
    import json

    task_input = """
    Your task is to run SWE-bench evaluation for the agent located at:
    <white_agent_url>
    http://localhost:9002
    </white_agent_url>
    You should use the following task configuration:
    <task_config>
    {
      "dataset": "lite",
      "task_ids": ["django__django-10914"],
      "timeout": 60,
      "max_workers": 2
    }
    </task_config>
    """

    # Test that the tags can be parsed correctly
    tags = parse_tags(task_input)
    assert tags["white_agent_url"].strip() == "http://localhost:9002"

    task_config = json.loads(tags["task_config"])
    assert task_config["dataset"] == "lite"
    assert task_config["task_ids"] == ["django__django-10914"]
    assert task_config["timeout"] == 60
    assert task_config["max_workers"] == 2


# =============================================================================
# Config Tests
# =============================================================================


def test_config_defaults():
    """Test configuration default values."""
    from src.core.config import (
        SWEBENCH_TIMEOUT_SECONDS,
        SWEBENCH_MAX_WORKERS,
        SWEBENCH_MAX_BATCH_SIZE,
    )

    # These should have sensible defaults
    assert SWEBENCH_TIMEOUT_SECONDS >= 60
    assert SWEBENCH_MAX_WORKERS >= 1
    assert SWEBENCH_MAX_BATCH_SIZE >= 1


def test_swebench_cache_dir_exists():
    """Test that cache directory is created."""
    from src.core.config import SWEBENCH_CACHE_DIR

    assert SWEBENCH_CACHE_DIR.exists()


# =============================================================================
# Sandbox Tests
# =============================================================================


def test_sandbox_check_docker():
    """Test Docker availability check."""
    from src.harness.sandbox import Sandbox

    available, message = Sandbox.check_docker_available()
    # Don't assert the result - Docker may or may not be available
    # Just verify the function runs without error
    assert isinstance(available, bool)
    assert isinstance(message, str)

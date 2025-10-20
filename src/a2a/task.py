"""Task evaluation endpoint implementation."""

from src.schemas import TaskRequest, TaskResponse
from src.harness.runner import TestRunner
from src.core.logger import logger


def run_task_evaluation(request: TaskRequest) -> TaskResponse:
    """
    Run evaluation for a SWE-Bench task with the specified patch.

    Args:
        request: TaskRequest with task_id and patch_choice

    Returns:
        TaskResponse with evaluation results
    """
    logger.info(f"Received task request: {request.task_id} with patch: {request.patch_choice}")

    try:
        # Create test runner
        runner = TestRunner(
            task_id=request.task_id,
            patch_choice=request.patch_choice,
        )

        # Run evaluation
        result = runner.run()

        # Convert to TaskResponse
        return TaskResponse(**result)

    except ValueError as e:
        # Handle invalid task ID
        logger.error(f"Invalid task request: {str(e)}")
        return TaskResponse(
            task_id=request.task_id,
            tests_passed=0,
            total_tests=0,
            verdict="FAIL",
            runtime_ms=0,
            failure_type="test_failure",
            logs_uri=f"/logs/{request.task_id}-error.txt",
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error during task evaluation: {str(e)}")
        return TaskResponse(
            task_id=request.task_id,
            tests_passed=0,
            total_tests=0,
            verdict="FAIL",
            runtime_ms=0,
            failure_type="test_failure",
            logs_uri=f"/logs/{request.task_id}-error.txt",
        )

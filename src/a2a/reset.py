"""Reset endpoint implementation."""

from src.schemas import ResetResponse
from src.harness.sandbox import Sandbox
from src.core.logger import logger


def reset_environment() -> ResetResponse:
    """
    Reset the evaluation environment by cleaning all sandboxes and logs.

    Returns:
        ResetResponse with status information
    """
    logger.info("Resetting environment...")

    try:
        # Clean all sandboxes and logs
        cleaned_dirs = Sandbox.reset_all()

        logger.info(f"Environment reset complete. Cleaned {len(cleaned_dirs)} items.")

        return ResetResponse(
            status="success",
            message=f"Environment reset successfully. Cleaned {len(cleaned_dirs)} items.",
            directories_cleaned=cleaned_dirs,
        )

    except Exception as e:
        logger.error(f"Error during reset: {str(e)}")
        return ResetResponse(
            status="error",
            message=f"Failed to reset environment: {str(e)}",
            directories_cleaned=[],
        )

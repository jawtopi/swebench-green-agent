"""
SWE-Bench Green Agent - FastAPI Application

A minimal Green Agent for AgentBeats that evaluates code patches
using the SWE-Bench benchmark.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

from src.schemas import AgentCard, TaskRequest, TaskResponse, ResetResponse
from src.a2a.card import get_agent_card
from src.a2a.reset import reset_environment
from src.a2a.task import run_task_evaluation
from src.core.config import LOGS_DIR, AGENT_NAME, AGENT_VERSION
from src.core.logger import logger

# Create FastAPI app
app = FastAPI(
    title=AGENT_NAME,
    description="A Green Agent for AgentBeats that evaluates code patches using SWE-Bench",
    version=AGENT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info(f"Starting {AGENT_NAME} v{AGENT_VERSION}")
    logger.info(f"Logs directory: {LOGS_DIR}")


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service information."""
    return {
        "service": AGENT_NAME,
        "version": AGENT_VERSION,
        "status": "running",
        "endpoints": {
            "card": "/card",
            "reset": "/reset",
            "task": "/task",
            "logs": "/logs/{filename}",
        },
    }


@app.get("/card", response_model=AgentCard)
async def card():
    """
    GET /card - Return A2A-compliant agent card metadata.

    Returns agent information including name, description, capabilities,
    and protocol version.
    """
    logger.info("Received request for agent card")
    return get_agent_card()


@app.post("/reset", response_model=ResetResponse)
async def reset():
    """
    POST /reset - Reset the evaluation environment.

    Clears all working directories and logs to ensure reproducibility
    for subsequent evaluations.
    """
    logger.info("Received reset request")
    return reset_environment()


@app.post("/task", response_model=TaskResponse)
async def task(request: TaskRequest):
    """
    POST /task - Run evaluation for a SWE-Bench task.

    Evaluates a code patch for the specified task and returns
    objective metrics including test results and verdict.

    Args:
        request: TaskRequest with task_id and patch_choice

    Returns:
        TaskResponse with evaluation results
    """
    logger.info(f"Received task request: {request.task_id} with patch: {request.patch_choice}")

    try:
        result = run_task_evaluation(request)
        return result
    except Exception as e:
        logger.error(f"Error processing task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/{filename}")
async def get_log(filename: str):
    """
    GET /logs/{filename} - Retrieve execution logs.

    Args:
        filename: Name of the log file

    Returns:
        Log file contents as plain text
    """
    log_path = LOGS_DIR / filename

    if not log_path.exists():
        logger.warning(f"Log file not found: {filename}")
        raise HTTPException(status_code=404, detail=f"Log file not found: {filename}")

    logger.info(f"Serving log file: {filename}")
    return FileResponse(
        log_path,
        media_type="text/plain",
        filename=filename,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": AGENT_NAME}


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

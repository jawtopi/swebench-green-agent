"""Pydantic models for request/response validation."""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# A2A Card Schema
class AgentCard(BaseModel):
    """Agent card metadata following A2A protocol."""

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    model_type: str = Field(..., description="Type of agent (e.g., 'green', 'white')")
    author: str = Field(..., description="Author or organization")
    protocol: str = Field(default="A2A", description="Protocol version")
    version: str = Field(default="1.0.0", description="Agent version")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")


# Task Request Schema
class TaskRequest(BaseModel):
    """Request schema for POST /task endpoint."""

    task_id: str = Field(..., description="SWE-Bench task identifier (e.g., 'numpy-1234')")
    patch_choice: Literal["good", "bad"] = Field(..., description="Which patch to evaluate")


# Task Response Schema
class TaskResponse(BaseModel):
    """Response schema for POST /task endpoint."""

    task_id: str = Field(..., description="SWE-Bench task identifier")
    tests_passed: int = Field(..., description="Number of tests that passed")
    total_tests: int = Field(..., description="Total number of tests")
    verdict: Literal["PASS", "FAIL"] = Field(..., description="Overall evaluation verdict")
    runtime_ms: int = Field(..., description="Execution time in milliseconds")
    failure_type: Optional[Literal["apply_error", "test_failure"]] = Field(
        None, description="Type of failure if verdict is FAIL"
    )
    logs_uri: str = Field(..., description="Path to execution logs")


# Reset Response Schema
class ResetResponse(BaseModel):
    """Response schema for POST /reset endpoint."""

    status: str = Field(..., description="Reset status")
    message: str = Field(..., description="Human-readable message")
    directories_cleaned: list[str] = Field(default_factory=list, description="Directories that were cleaned")

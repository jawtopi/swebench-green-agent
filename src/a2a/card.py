"""Agent card endpoint implementation."""

from src.schemas import AgentCard
from src.core.config import (
    AGENT_NAME,
    AGENT_DESCRIPTION,
    AGENT_AUTHOR,
    AGENT_VERSION,
)


def get_agent_card() -> AgentCard:
    """
    Return A2A-compliant agent card metadata.

    Returns:
        AgentCard with agent information
    """
    return AgentCard(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model_type="green",
        author=AGENT_AUTHOR,
        protocol="A2A",
        version=AGENT_VERSION,
        capabilities=[
            "swe-bench",
            "patch-evaluation",
            "test-execution",
            "deterministic-scoring",
        ],
    )

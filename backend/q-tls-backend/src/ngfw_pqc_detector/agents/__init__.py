"""
Modern multi-agent system for security analysis.

This package implements a cutting-edge agent architecture using:
- LangGraph for state machine orchestration
- A2A protocol for agent-to-agent communication
- Vector memory for semantic search
- Streaming responses
- Comprehensive observability
"""

from .protocol.a2a import AgentMessage, AgentProtocol, AgentRegistry
from .protocol.base_agent import BaseAgent, AgentCapability

__all__ = [
    "AgentMessage",
    "AgentProtocol",
    "AgentRegistry",
    "BaseAgent",
    "AgentCapability",
]



"""
Compatibility wrapper for the new telemetry-grounded security analyst agent runtime.
"""

from .agent_runtime import SecurityAnalystAgentRuntime


class SecurityAnalystAgentGraph(SecurityAnalystAgentRuntime):
    """Backward-compatible alias for the new runtime."""



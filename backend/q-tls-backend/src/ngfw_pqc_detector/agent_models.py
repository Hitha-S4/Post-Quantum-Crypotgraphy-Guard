"""
Pydantic models for the telemetry-grounded security analyst agent.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AgentRole = Literal["system", "user", "assistant", "tool"]
AgentExecutionStatus = Literal["completed", "clarification_needed"]
AgentSeverity = Literal["critical", "high", "medium", "low", "info"]


class AgentChatMessage(BaseModel):
    """Single message in the agent conversation."""

    role: AgentRole
    content: str = Field(..., min_length=1)
    name: Optional[str] = None


class SecurityAnalystAgentRequest(BaseModel):
    """Request payload for the security analyst agent."""

    query: str = Field(..., min_length=1, description="Natural language question for the agent")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation identifier used to persist memory across turns",
    )
    messages: List[AgentChatMessage] = Field(
        default_factory=list,
        description="Optional prior chat messages to seed the conversation context",
    )
    time_window_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Time window in minutes used for analytics and investigation",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of records to inspect per tool query",
    )
    include_raw_records: bool = Field(
        default=False,
        description="Whether investigation details should include raw sampled records",
    )


class AgentEvidenceItem(BaseModel):
    """Structured evidence item returned by the agent."""

    source: str
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)


class AgentInvestigationItem(BaseModel):
    """Backward-compatible investigation item for legacy imports."""

    title: str
    severity: AgentSeverity
    summary: str
    recommendation: str
    evidence: List[AgentEvidenceItem] = Field(default_factory=list)


class AgentToolCall(BaseModel):
    """Represents one tool selection made by the agent."""

    tool_name: str
    purpose: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AgentTraceStep(BaseModel):
    """One trace step emitted by a node in the agent graph."""

    node: str
    status: Literal["completed", "warning", "clarification_needed"]
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class AgentVerificationResult(BaseModel):
    """Verification result that confirms whether the answer is grounded."""

    grounded: bool
    sufficient: bool
    issues: List[str] = Field(default_factory=list)
    grounded_tool_names: List[str] = Field(default_factory=list)


class AgentClarificationRequest(BaseModel):
    """Clarification request emitted when the question is underspecified."""

    question: str
    reason: str
    options: List[str] = Field(default_factory=list)


class AgentProviderMetadata(BaseModel):
    """LLM provider metadata for the current execution."""

    name: str
    model: str


class SecurityAnalystAgentResponse(BaseModel):
    """Response payload for the security analyst agent."""

    conversation_id: str
    query: str
    status: AgentExecutionStatus
    summary: str
    answer: str
    risk_level: AgentSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    tool_calls: List[AgentToolCall] = Field(default_factory=list)
    evidence: List[AgentEvidenceItem] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    trace: List[AgentTraceStep] = Field(default_factory=list)
    verification: AgentVerificationResult
    clarification: Optional[AgentClarificationRequest] = None
    provider: Optional[AgentProviderMetadata] = None
    generated_at: str
    raw_context: Optional[Dict[str, Any]] = None


class AgentConversationRecord(BaseModel):
    """Persisted conversation state for memory."""

    conversation_id: str
    created_at: str
    updated_at: str
    messages: List[AgentChatMessage] = Field(default_factory=list)
    last_tool_calls: List[AgentToolCall] = Field(default_factory=list)
    last_response_metadata: Dict[str, Any] = Field(default_factory=dict)



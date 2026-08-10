"""
Provider-agnostic agent runtime with explicit node-style orchestration.

This module replaces the old pseudo-agent flow with a more structured runtime that:
- maintains conversation memory
- loads prompts from YAML
- uses provider adapters for model calls
- routes intent to telemetry tools
- verifies grounding before answering
- returns structured trace/confidence/clarification metadata
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Protocol
from uuid import uuid4

import httpx
import yaml

from .agent_models import (
    AgentChatMessage,
    AgentConversationRecord,
    AgentEvidenceItem,
    AgentToolCall,
    SecurityAnalystAgentRequest,
    SecurityAnalystAgentResponse,
)
from .core.config import settings
from .services.database import DatabaseService, mongo_db

logger = logging.getLogger(__name__)


class AgentTraceStep:
    """Trace record for one graph node execution."""

    def __init__(
        self,
        node: str,
        status: str,
        details: Dict[str, Any],
        timestamp: str,
    ) -> None:
        self.node = node
        self.status = status
        self.details = details
        self.timestamp = timestamp

    def model_dump(self) -> Dict[str, Any]:
        return {
            "node": self.node,
            "status": self.status,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class AgentVerificationResult:
    """Verification result for response grounding."""

    def __init__(
        self,
        grounded: bool,
        sufficient: bool,
        issues: List[str],
        grounded_tool_names: List[str],
    ) -> None:
        self.grounded = grounded
        self.sufficient = sufficient
        self.issues = issues
        self.grounded_tool_names = grounded_tool_names

    def model_dump(self) -> Dict[str, Any]:
        return {
            "grounded": self.grounded,
            "sufficient": self.sufficient,
            "issues": self.issues,
            "grounded_tool_names": self.grounded_tool_names,
        }


class AgentClarificationRequest:
    """Clarification request returned when the question is underspecified."""

    def __init__(
        self,
        question: str,
        reason: str,
        options: Optional[List[str]] = None,
    ) -> None:
        self.question = question
        self.reason = reason
        self.options = options or []

    def model_dump(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "reason": self.reason,
            "options": self.options,
        }


class LLMProvider(Protocol):
    """Provider contract for agent planning and response generation."""

    provider_name: str
    model_name: str

    @property
    def enabled(self) -> bool:
        """Whether the provider can be used."""
        ...

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a JSON object."""
        ...

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a text response."""
        ...


class ConversationMemoryStore:
    """Stores agent conversations with MongoDB fallback to in-memory storage."""

    def __init__(self) -> None:
        self._local_store: Dict[str, AgentConversationRecord] = {}

    @property
    def collection(self):
        if mongo_db is None:
            return None
        return mongo_db["agent_conversations"]

    async def get(self, conversation_id: str) -> Optional[AgentConversationRecord]:
        now = datetime.utcnow()
        collection = self.collection

        if collection is not None:
            document = await collection.find_one({"conversation_id": conversation_id})
            if not document:
                return None
            document.pop("_id", None)
            record = AgentConversationRecord(**document)
            if now - datetime.fromisoformat(record.updated_at) > timedelta(
                minutes=settings.AGENT_MEMORY_TTL_MINUTES
            ):
                await collection.delete_one({"conversation_id": conversation_id})
                return None
            return record

        record = self._local_store.get(conversation_id)
        if not record:
            return None
        if now - datetime.fromisoformat(record.updated_at) > timedelta(
            minutes=settings.AGENT_MEMORY_TTL_MINUTES
        ):
            self._local_store.pop(conversation_id, None)
            return None
        return record

    async def save(self, record: AgentConversationRecord) -> None:
        trimmed = AgentConversationRecord(
            conversation_id=record.conversation_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            messages=record.messages[-settings.AGENT_MEMORY_MAX_MESSAGES :],
            last_tool_calls=record.last_tool_calls,
            last_response_metadata=record.last_response_metadata,
        )
        collection = self.collection
        if collection is not None:
            await collection.replace_one(
                {"conversation_id": trimmed.conversation_id},
                trimmed.model_dump(),
                upsert=True,
            )
            return
        self._local_store[trimmed.conversation_id] = trimmed


class DisabledProvider:
    """Fallback provider that reports itself as unavailable."""

    provider_name = "disabled"
    model_name = "disabled"

    @property
    def enabled(self) -> bool:
        return False

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise RuntimeError("No enabled LLM provider configured")

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        raise RuntimeError("No enabled LLM provider configured")


class OpenAIProvider:
    """OpenAI provider adapter."""

    def __init__(self) -> None:
        self.provider_name = "openai"
        self.model_name = settings.AGENT_MODEL
        self.api_key = settings.AGENT_OPENAI_API_KEY or settings.AGENT_API_KEY

    @property
    def enabled(self) -> bool:
        return settings.AGENT_PROVIDER == "openai" and bool(self.api_key)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = await self.complete_text(system_prompt, user_prompt, metadata)
        return json.loads(text)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload = {
            "model": self.model_name,
            "temperature": settings.AGENT_TEMPERATURE,
            "response_format": {"type": "json_object"}
            if metadata and metadata.get("response_format") == "json"
            else None,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if payload["response_format"] is None:
            payload.pop("response_format")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.AGENT_LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AnthropicProvider:
    """Anthropic provider adapter."""

    def __init__(self) -> None:
        self.provider_name = "anthropic"
        self.model_name = settings.AGENT_MODEL
        self.api_key = settings.AGENT_ANTHROPIC_API_KEY

    @property
    def enabled(self) -> bool:
        return settings.AGENT_PROVIDER == "anthropic" and bool(self.api_key)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = await self.complete_text(system_prompt, user_prompt, metadata)
        return json.loads(text)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=settings.AGENT_LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "max_tokens": settings.AGENT_MAX_OUTPUT_TOKENS,
                    "temperature": settings.AGENT_TEMPERATURE,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [])
            text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
            return "\n".join(text_blocks).strip()


class LocalLLMProvider:
    """Local Ollama-compatible provider adapter."""

    def __init__(self) -> None:
        self.provider_name = "local"
        self.model_name = settings.AGENT_MODEL

    @property
    def enabled(self) -> bool:
        return settings.AGENT_PROVIDER == "local" and bool(settings.AGENT_LOCAL_BASE_URL)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = await self.complete_text(system_prompt, user_prompt, metadata)
        return json.loads(text)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        base_url = (settings.AGENT_LOCAL_BASE_URL or "http://localhost:11434").rstrip("/")
        prompt = (
            f"{system_prompt}\n\n"
            "Respond exactly to the user's request. "
            "If JSON is required, output valid JSON only.\n\n"
            f"{user_prompt}"
        )

        async with httpx.AsyncClient(timeout=settings.AGENT_LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.AGENT_TEMPERATURE,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", "")).strip()


class AgentPromptLibrary:
    """Loads agent prompts from YAML."""

    def __init__(self) -> None:
        prompt_path = Path(__file__).resolve().parent / "prompts" / "prompt.yaml"
        with prompt_path.open("r", encoding="utf-8") as handle:
            self._data = yaml.safe_load(handle)

    def get(self, key: str) -> str:
        value = self._data.get(key)
        if not isinstance(value, str):
            raise KeyError(f"Prompt '{key}' not found")
        return value


class AgentToolRegistry:
    """Registry of telemetry tools the agent can invoke."""

    TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
        "get_connection_stats": {
            "description": "Get aggregate connection statistics over a time window.",
            "arguments": ["time_window_minutes"],
        },
        "get_recent_connections": {
            "description": "Get recent TLS connections for investigation and examples.",
            "arguments": ["limit"],
        },
        "get_pqc_connections": {
            "description": "Get recent PQC or hybrid-enabled connections.",
            "arguments": ["limit"],
        },
        "get_connections_in_timewindow": {
            "description": "Get TLS connections within a specific time window.",
            "arguments": ["time_window_minutes", "filters"],
        },
        "get_accumulated_stats": {
            "description": "Get accumulated operational counters.",
            "arguments": [],
        },
        "get_recent_alerts": {
            "description": "Get recent alerts with severity and metadata.",
            "arguments": ["limit"],
        },
        "get_topology_snapshot": {
            "description": "Get current network topology snapshot.",
            "arguments": ["time_window_minutes"],
        },
    }

    def describe_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": name, **schema}
            for name, schema in self.TOOL_SCHEMAS.items()
        ]


class SecurityAnalystAgentRuntime:
    """Explicit node-based security analyst runtime."""

    def __init__(self) -> None:
        self.memory_store = ConversationMemoryStore()
        self.prompts = AgentPromptLibrary()
        self.tool_registry = AgentToolRegistry()
        self.database_service = DatabaseService()
        self.provider = self._build_provider()

    def _build_provider(self) -> LLMProvider:
        for provider in (OpenAIProvider(), AnthropicProvider(), LocalLLMProvider()):
            if provider.enabled:
                return provider
        return DisabledProvider()

    async def run(self, request: SecurityAnalystAgentRequest) -> SecurityAnalystAgentResponse:
        conversation_id = request.conversation_id or str(uuid4())
        memory = await self.memory_store.get(conversation_id)

        state: Dict[str, Any] = {
            "request": request,
            "conversation_id": conversation_id,
            "memory": memory,
            "trace": [],
            "tool_calls": [],
            "tool_results": {},
            "evidence": [],
            "status": "completed",
            "clarification": None,
            "verification": AgentVerificationResult(
                grounded=False,
                sufficient=False,
                issues=["Verification not executed"],
                grounded_tool_names=[],
            ),
        }

        state = await self._node_load_memory(state)
        state = await self._node_plan(state)
        if state.get("status") == "clarification_needed":
            state = await self._node_finalize(state)
            await self._save_memory(state)
            return state["response"]

        state = await self._node_execute_tools(state)
        state = await self._node_verify(state)
        state = await self._node_respond(state)
        state = await self._node_finalize(state)
        await self._save_memory(state)
        return state["response"]

    async def _node_load_memory(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request: SecurityAnalystAgentRequest = state["request"]
        memory: Optional[AgentConversationRecord] = state["memory"]

        messages = list(memory.messages) if memory else []
        messages.extend(request.messages)
        messages.append(AgentChatMessage(role="user", content=request.query))
        state["conversation_messages"] = messages

        self._trace(
            state,
            "load_memory",
            "completed",
            {
                "conversation_id": state["conversation_id"],
                "memory_message_count": len(memory.messages) if memory else 0,
                "request_message_count": len(request.messages),
            },
        )
        return state

    async def _node_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request: SecurityAnalystAgentRequest = state["request"]
        query = request.query.strip()
        query_lower = query.lower()

        if not self.provider.enabled:
            raise RuntimeError(
                "No LLM provider is configured. Set [`AGENT_PROVIDER`](backend/q-tls-backend/src/ngfw_pqc_detector/core/config.py) and matching API credentials."
            )
        
        # Direct tool name match - bypass LLM for exact tool names
        if query_lower in self.tool_registry.TOOL_SCHEMAS:
            logger.info(f"Direct tool match detected: {query_lower}")
            tool_calls = [
                AgentToolCall(
                    tool_name=query_lower,
                    purpose=f"Execute {query_lower}",
                    arguments={},
                )
            ]
            state["plan"] = {
                "intent": "direct_tool_call",
                "analysis_focus": [query_lower],
                "tool_calls": tool_calls,
            }
            state["tool_calls"] = tool_calls
            self._trace(
                state,
                "plan",
                "completed",
                {
                    "intent": "direct_tool_call",
                    "tool_count": 1,
                    "direct_match": True,
                },
            )
            return state

        planning_payload = {
            "query": query,
            "time_window_minutes": request.time_window_minutes,
            "limit": request.limit,
            "messages": [message.model_dump() for message in state["conversation_messages"][-8:]],
            "tools": self.tool_registry.describe_tools(),
        }

        system_prompt = self.prompts.get("planner_system")
        user_prompt = json.dumps(planning_payload, default=str)

        plan = await self.provider.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            metadata={"response_format": "json"},
        )

        clarification_needed = bool(plan.get("clarification_needed"))
        if clarification_needed:
            clarification = AgentClarificationRequest(
                question=plan.get(
                    "clarification_question",
                    "Please clarify the exact asset, metric, or time scope you want me to investigate.",
                ),
                reason=plan.get(
                    "clarification_reason",
                    "The query is underspecified for a grounded telemetry-backed answer.",
                ),
                options=plan.get("clarification_options", []),
            )
            state["status"] = "clarification_needed"
            state["clarification"] = clarification
            state["plan"] = {
                "intent": plan.get("intent", "clarify"),
                "tool_calls": [],
                "analysis_focus": plan.get("analysis_focus", []),
            }
            self._trace(
                state,
                "plan",
                "clarification_needed",
                {
                    "intent": state["plan"]["intent"],
                    "question": clarification.question,
                },
            )
            return state

        raw_tool_calls = plan.get("tool_calls", [])
        
        # Fallback: If query exactly matches a tool name and no tools selected, force that tool
        query_lower = query.lower().strip()
        if not raw_tool_calls and query_lower in self.tool_registry.TOOL_SCHEMAS:
            raw_tool_calls = [{
                "tool_name": query_lower,
                "purpose": f"Execute {query_lower}",
                "arguments": {}
            }]
        
        tool_calls = [
            AgentToolCall(
                tool_name=item["tool_name"],
                purpose=item.get("purpose", "Investigate telemetry"),
                arguments=item.get("arguments", {}),
            )
            for item in raw_tool_calls
            if item.get("tool_name") in self.tool_registry.TOOL_SCHEMAS
        ]

        state["plan"] = {
            "intent": plan.get("intent", "investigate"),
            "analysis_focus": plan.get("analysis_focus", []),
            "tool_calls": tool_calls,
        }
        state["tool_calls"] = tool_calls

        self._trace(
            state,
            "plan",
            "completed",
            {
                "intent": state["plan"]["intent"],
                "tool_count": len(tool_calls),
            },
        )
        return state

    async def _node_execute_tools(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request: SecurityAnalystAgentRequest = state["request"]
        tool_results: Dict[str, Any] = {}
        evidence: List[AgentEvidenceItem] = []

        for tool_call in state["tool_calls"]:
            arguments = dict(tool_call.arguments)
            arguments.setdefault("time_window_minutes", request.time_window_minutes)
            arguments.setdefault("limit", request.limit)
            result = await self._run_tool(tool_call.tool_name, arguments)
            tool_results[tool_call.tool_name] = result
            evidence.append(
                AgentEvidenceItem(
                    source=tool_call.tool_name,
                    summary=f"Telemetry fetched via {tool_call.tool_name}",
                    data=self._summarize_for_evidence(result),
                )
            )

        state["tool_results"] = tool_results
        state["evidence"] = evidence

        self._trace(
            state,
            "execute_tools",
            "completed",
            {
                "executed_tools": [tool.tool_name for tool in state["tool_calls"]],
            },
        )
        return state

    async def _node_verify(self, state: Dict[str, Any]) -> Dict[str, Any]:
        tool_names = [tool.tool_name for tool in state["tool_calls"]]
        sufficient = bool(tool_names) and bool(state["tool_results"])
        grounded = sufficient and all(state["tool_results"].get(name) is not None for name in tool_names)

        issues: List[str] = []
        if not tool_names:
            issues.append("Planner did not select any telemetry tools.")
        if not state["tool_results"]:
            issues.append("No telemetry results were returned.")
        if grounded and sufficient:
            issues = []

        verification = AgentVerificationResult(
            grounded=grounded,
            sufficient=sufficient,
            issues=issues,
            grounded_tool_names=tool_names if grounded else [],
        )
        state["verification"] = verification

        self._trace(
            state,
            "verify",
            "completed" if grounded else "warning",
            {
                "grounded": grounded,
                "sufficient": sufficient,
                "issues": issues,
            },
        )
        return state

    async def _node_respond(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request: SecurityAnalystAgentRequest = state["request"]
        verification: AgentVerificationResult = state["verification"]

        if not verification.grounded:
            raise RuntimeError(
                "Agent response blocked because the answer is not grounded in telemetry tool output."
            )

        response_payload = {
            "query": request.query,
            "intent": state["plan"]["intent"],
            "analysis_focus": state["plan"].get("analysis_focus", []),
            "tool_calls": [tool.model_dump() for tool in state["tool_calls"]],
            "tool_results": state["tool_results"],
            "verification": verification.model_dump(),
            "conversation_messages": [
                message.model_dump() for message in state["conversation_messages"][-8:]
            ],
        }

        answer = await self.provider.complete_text(
            system_prompt=self.prompts.get("responder_system"),
            user_prompt=json.dumps(response_payload, default=str),
            metadata={"response_format": "text"},
        )

        metrics = self._extract_metrics(state["tool_results"])
        confidence = self._derive_confidence(verification, state["tool_calls"], state["tool_results"])

        state["answer"] = answer.strip()
        state["summary"] = self._build_summary(state["plan"]["intent"], metrics, verification)
        state["metrics"] = metrics
        state["confidence"] = confidence
        state["risk_level"] = self._derive_risk_level(metrics, state["tool_results"])

        self._trace(
            state,
            "respond",
            "completed",
            {
                "confidence": confidence,
                "risk_level": state["risk_level"],
            },
        )
        return state

    async def _node_finalize(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request: SecurityAnalystAgentRequest = state["request"]
        generated_at = datetime.utcnow().isoformat()

        if state.get("status") == "clarification_needed":
            response = SecurityAnalystAgentResponse(
                conversation_id=state["conversation_id"],
                query=request.query,
                status="clarification_needed",
                summary="More detail is required before running telemetry-backed analysis.",
                answer="I need clarification before I can run the correct telemetry investigation.",
                risk_level="info",
                confidence=0.0,
                tool_calls=[],
                evidence=[],
                metrics={},
                trace=[step.model_dump() if hasattr(step, 'model_dump') else step for step in state["trace"]],
                verification=AgentVerificationResult(
                    grounded=False,
                    sufficient=False,
                    issues=["Clarification required before tool execution."],
                    grounded_tool_names=[],
                ).model_dump(),
                clarification=state["clarification"],
                provider=(
                    {
                        "name": self.provider.provider_name,
                        "model": self.provider.model_name,
                    }
                    if self.provider.enabled
                    else None
                ),
                generated_at=generated_at,
                raw_context=None,
            )
            state["response"] = response
            return state

        response = SecurityAnalystAgentResponse(
            conversation_id=state["conversation_id"],
            query=request.query,
            status="completed",
            summary=state["summary"],
            answer=state["answer"],
            risk_level=state["risk_level"],
            confidence=state["confidence"],
            tool_calls=state["tool_calls"],
            evidence=state["evidence"],
            metrics=state["metrics"],
            trace=[step.model_dump() if hasattr(step, 'model_dump') else step for step in state["trace"]],
            verification=state["verification"].model_dump() if hasattr(state["verification"], 'model_dump') else state["verification"],
            clarification=None,
            provider={
                "name": self.provider.provider_name,
                "model": self.provider.model_name,
            },
            generated_at=generated_at,
            raw_context=state["tool_results"] if request.include_raw_records else None,
        )
        state["response"] = response
        return state

    async def _save_memory(self, state: Dict[str, Any]) -> None:
        request: SecurityAnalystAgentRequest = state["request"]
        response: SecurityAnalystAgentResponse = state["response"]
        previous: Optional[AgentConversationRecord] = state["memory"]
        now = datetime.utcnow().isoformat()

        messages = list(previous.messages) if previous else []
        messages.append(AgentChatMessage(role="user", content=request.query))
        messages.append(AgentChatMessage(role="assistant", content=response.answer))

        record = AgentConversationRecord(
            conversation_id=response.conversation_id,
            created_at=previous.created_at if previous else now,
            updated_at=now,
            messages=messages,
            last_tool_calls=response.tool_calls,
            last_response_metadata={
                "status": response.status,
                "confidence": response.confidence,
                "risk_level": response.risk_level,
            },
        )
        await self.memory_store.save(record)

    async def _run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name == "get_connection_stats":
            return await self.database_service.get_connection_stats()

        if tool_name == "get_recent_connections":
            return await self.database_service.get_recent_connections(arguments.get("limit", 10))

        if tool_name == "get_pqc_connections":
            return await self.database_service.get_pqc_connections(arguments.get("limit", 10))

        if tool_name == "get_connections_in_timewindow":
            filters = arguments.get("filters") or {}
            return await self.database_service.get_connections_in_timewindow(
                arguments.get("time_window_minutes", 60),
                filters,
            )

        if tool_name == "get_accumulated_stats":
            from .services.database import mongo_db as db
            if db is None:
                logger.warning("MongoDB not available for get_accumulated_stats")
                return {}
            result = await db["accumulated_network_stats"].find_one(
                {"_id": "accumulated_stats_v1"},
                {"_id": 0},
            )
            if result:
                logger.info(f"get_accumulated_stats returned {len(result)} fields")
            else:
                logger.warning("get_accumulated_stats found no document")
            return result if result else {}

        if tool_name == "get_recent_alerts":
            if mongo_db is None:
                return []
            cursor = mongo_db["alerts"].find().sort("timestamp", -1).limit(arguments.get("limit", 10))
            alerts = await cursor.to_list(length=arguments.get("limit", 10))
            for alert in alerts:
                alert["_id"] = str(alert["_id"])
            return alerts

        if tool_name == "get_topology_snapshot":
            if mongo_db is None:
                return {"nodes": [], "edges": []}
            cutoff = datetime.utcnow() - timedelta(minutes=arguments.get("time_window_minutes", 60))
            nodes = await mongo_db["network_nodes"].find({"last_seen": {"$gte": cutoff}}).to_list(length=500)
            edges = await mongo_db["network_edges"].find({"last_seen": {"$gte": cutoff}}).to_list(length=500)
            for item in nodes:
                item["_id"] = str(item["_id"])
            for item in edges:
                item["_id"] = str(item["_id"])
            return {"nodes": nodes, "edges": edges}

        raise ValueError(f"Unsupported tool: {tool_name}")

    def _trace(
        self,
        state: Dict[str, Any],
        node: str,
        status: Literal["completed", "warning", "clarification_needed"],
        details: Dict[str, Any],
    ) -> None:
        state["trace"].append(
            AgentTraceStep(
                node=node,
                status=status,
                details=details,
                timestamp=datetime.utcnow().isoformat(),
            )
        )

    def _derive_confidence(
        self,
        verification: AgentVerificationResult,
        tool_calls: List[AgentToolCall],
        tool_results: Dict[str, Any],
    ) -> float:
        if not verification.grounded:
            return 0.0
        populated_results = sum(1 for tool in tool_calls if tool_results.get(tool.tool_name) is not None)
        if not tool_calls:
            return 0.0
        return round(min(0.99, 0.45 + (populated_results / len(tool_calls)) * 0.5), 2)

    def _derive_risk_level(self, metrics: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        vulnerable = metrics.get("vulnerable_connections") or metrics.get("total_pqc_vulnerable") or 0
        recent_alerts = tool_results.get("get_recent_alerts") or []
        high_alerts = 0
        for alert in recent_alerts:
            severity = str(alert.get("severity", "")).lower()
            if severity in {"critical", "high", "1", "2"}:
                high_alerts += 1
        if vulnerable >= 20 or high_alerts >= 5:
            return "critical"
        if vulnerable >= 10 or high_alerts >= 3:
            return "high"
        if vulnerable >= 1 or high_alerts >= 1:
            return "medium"
        return "low"

    def _extract_metrics(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}

        stats = tool_results.get("get_connection_stats") or {}
        for key in (
            "total_connections",
            "pqc_connections",
            "hybrid_connections",
            "classical_connections",
            "pqc_percentage",
        ):
            if key in stats:
                metrics[key] = stats[key]

        accumulated = tool_results.get("get_accumulated_stats") or {}
        for key in (
            "total_flows",
            "total_tls_flows",
            "total_pqc_safe",
            "total_pqc_vulnerable",
            "total_alerts",
            "total_critical_alerts",
            "total_high_alerts",
        ):
            if key in accumulated:
                metrics[key] = accumulated[key]

        alerts = tool_results.get("get_recent_alerts")
        if isinstance(alerts, list):
            metrics["recent_alert_count"] = len(alerts)

        topology = tool_results.get("get_topology_snapshot")
        if isinstance(topology, dict):
            metrics["topology_nodes"] = len(topology.get("nodes", []))
            metrics["topology_edges"] = len(topology.get("edges", []))

        recent_connections = tool_results.get("get_recent_connections")
        if isinstance(recent_connections, list):
            metrics["recent_connection_count"] = len(recent_connections)

        pqc_connections = tool_results.get("get_pqc_connections")
        if isinstance(pqc_connections, list):
            metrics["recent_pqc_connection_count"] = len(pqc_connections)

        timed_connections = tool_results.get("get_connections_in_timewindow")
        if isinstance(timed_connections, list):
            metrics["window_connection_count"] = len(timed_connections)
            metrics["vulnerable_connections"] = sum(
                1
                for connection in timed_connections
                if str(connection.get("crypto_type", "")).lower() == "classical"
                or not bool(connection.get("is_pqc"))
            )

        return metrics

    def _summarize_for_evidence(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, dict):
            keys = list(result.keys())[:8]
            return {"type": "dict", "keys": keys}
        if isinstance(result, list):
            return {"type": "list", "count": len(result)}
        return {"type": type(result).__name__}

    def _build_summary(
        self,
        intent: str,
        metrics: Dict[str, Any],
        verification: AgentVerificationResult,
    ) -> str:
        if not verification.grounded:
            return "Unable to produce a grounded answer."
        metric_fragments = []
        for key in (
            "total_connections",
            "pqc_connections",
            "vulnerable_connections",
            "recent_alert_count",
            "topology_nodes",
        ):
            if key in metrics:
                metric_fragments.append(f"{key}={metrics[key]}")
        joined = ", ".join(metric_fragments) if metric_fragments else "grounded telemetry collected"
        return f"Intent '{intent}' completed with {joined}."



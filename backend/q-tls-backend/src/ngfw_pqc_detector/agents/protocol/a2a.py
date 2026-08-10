"""
Agent-to-Agent (A2A) Protocol Implementation.

This module implements a custom A2A protocol for inter-agent communication,
enabling agents to discover, communicate, and coordinate with each other.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages in the A2A protocol."""
    
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"
    ERROR = "error"


class MessagePriority(int, Enum):
    """Message priority levels."""
    
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class AgentMessage(BaseModel):
    """
    Standard message format for agent-to-agent communication.
    
    Follows A2A protocol specifications for interoperability.
    """
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    from_agent: str
    to_agent: Optional[str] = None  # None for broadcasts
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    priority: MessagePriority = MessagePriority.NORMAL
    
    # Message content
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Response tracking
    correlation_id: Optional[str] = None  # For request-response pairing
    requires_response: bool = False
    timeout_seconds: int = 30


class AgentCapability(BaseModel):
    """Describes a capability that an agent provides."""
    
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class AgentInfo(BaseModel):
    """Information about a registered agent."""
    
    agent_id: str
    agent_type: str
    capabilities: List[AgentCapability]
    endpoint: Optional[str] = None
    status: str = "active"  # active, busy, offline
    registered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_heartbeat: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRegistry:
    """
    Central registry for agent discovery and management.
    
    Implements service discovery pattern for multi-agent systems.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._agent_instances: Dict[str, Any] = {}  # Store actual agent instances
        self._lock = asyncio.Lock()
        logger.info("Agent registry initialized")
    
    async def register(self, agent_info: AgentInfo, agent_instance: Any = None) -> bool:
        """Register an agent in the system."""
        async with self._lock:
            self._agents[agent_info.agent_id] = agent_info
            if agent_instance:
                self._agent_instances[agent_info.agent_id] = agent_instance
            logger.info(
                f"Agent registered: {agent_info.agent_id} "
                f"(type: {agent_info.agent_type}, "
                f"capabilities: {len(agent_info.capabilities)})"
            )
            return True
    
    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent from the system."""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                if agent_id in self._agent_instances:
                    del self._agent_instances[agent_id]
                logger.info(f"Agent unregistered: {agent_id}")
                return True
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        return self._agents.get(agent_id)
    
    async def get_agent_instance(self, agent_id: str) -> Optional[Any]:
        """Get the actual agent instance."""
        return self._agent_instances.get(agent_id)
    
    async def find_agents_by_type(self, agent_type: str) -> List[AgentInfo]:
        """Find all agents of a specific type."""
        return [
            agent for agent in self._agents.values()
            if agent.agent_type == agent_type and agent.status == "active"
        ]
    
    async def find_agents_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """Find all agents that provide a specific capability."""
        matching_agents = []
        for agent in self._agents.values():
            if agent.status != "active":
                continue
            for cap in agent.capabilities:
                if cap.name == capability_name:
                    matching_agents.append(agent)
                    break
        return matching_agents
    
    async def list_all_agents(self) -> List[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())
    
    async def update_heartbeat(self, agent_id: str) -> bool:
        """Update the last heartbeat timestamp for an agent."""
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].last_heartbeat = datetime.utcnow().isoformat()
                return True
            return False
    
    async def update_status(self, agent_id: str, status: str) -> bool:
        """Update the status of an agent."""
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = status
                logger.info(f"Agent {agent_id} status updated to: {status}")
                return True
            return False


class AgentProtocol:
    """
    A2A Protocol implementation for agent communication.
    
    Provides methods for sending messages, broadcasting, and handling responses.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._message_handlers: Dict[str, Any] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        logger.info("Agent protocol initialized")
    
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        action: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False,
        timeout_seconds: int = 30
    ) -> Optional[AgentMessage]:
        """
        Send a message to another agent.
        
        Args:
            from_agent: ID of the sending agent
            to_agent: ID of the receiving agent
            action: Action to perform
            payload: Message payload
            priority: Message priority
            requires_response: Whether a response is expected
            timeout_seconds: Timeout for response
            
        Returns:
            Response message if requires_response=True, None otherwise
        """
        message = AgentMessage(
            message_type=MessageType.REQUEST,
            from_agent=from_agent,
            to_agent=to_agent,
            action=action,
            payload=payload,
            priority=priority,
            requires_response=requires_response,
            timeout_seconds=timeout_seconds
        )
        
        logger.info(
            f"Sending message from {from_agent} to {to_agent}: "
            f"action={action}, priority={priority.name}"
        )
        
        # Check if target agent exists
        target_agent_info = await self.registry.get_agent(to_agent)
        if not target_agent_info:
            logger.error(f"Target agent not found: {to_agent}")
            return None
        
        if target_agent_info.status != "active":
            logger.warning(f"Target agent {to_agent} is not active: {target_agent_info.status}")
        
        # Get the actual agent instance from registry
        agent_instance = await self.registry.get_agent_instance(to_agent)
        if not agent_instance:
            logger.error(f"Agent instance not found for: {to_agent}")
            return None
        
        # If response is required, set up future
        if requires_response:
            future = asyncio.Future()
            self._pending_responses[message.message_id] = future
            
            try:
                # Deliver message to agent and get response
                logger.info(f"Delivering message to agent {to_agent}")
                response_data = await agent_instance.process_message(message)
                
                # Create response message
                response_msg = AgentMessage(
                    message_type=MessageType.RESPONSE,
                    from_agent=to_agent,
                    to_agent=from_agent,
                    action=f"response_{action}",
                    payload=response_data,
                    correlation_id=message.message_id
                )
                
                # Resolve the future with the response
                if not future.done():
                    future.set_result(response_msg)
                
                return response_msg
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for response from {to_agent}")
                if message.message_id in self._pending_responses:
                    del self._pending_responses[message.message_id]
                return None
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if message.message_id in self._pending_responses:
                    del self._pending_responses[message.message_id]
                return None
        else:
            # Fire and forget - just deliver the message
            try:
                await agent_instance.process_message(message)
            except Exception as e:
                logger.error(f"Error delivering message to {to_agent}: {e}")
        
        return None
    
    async def broadcast(
        self,
        from_agent: str,
        action: str,
        payload: Dict[str, Any],
        agent_types: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> List[str]:
        """
        Broadcast a message to multiple agents.
        
        Args:
            from_agent: ID of the sending agent
            action: Action to broadcast
            payload: Message payload
            agent_types: Optional list of agent types to target
            priority: Message priority
            
        Returns:
            List of agent IDs that received the broadcast
        """
        message = AgentMessage(
            message_type=MessageType.BROADCAST,
            from_agent=from_agent,
            to_agent=None,
            action=action,
            payload=payload,
            priority=priority
        )
        
        # Get target agents
        if agent_types:
            target_agents = []
            for agent_type in agent_types:
                agents = await self.registry.find_agents_by_type(agent_type)
                target_agents.extend(agents)
        else:
            target_agents = await self.registry.list_all_agents()
        
        # Filter out the sender and inactive agents
        target_agents = [
            agent for agent in target_agents
            if agent.agent_id != from_agent and agent.status == "active"
        ]
        
        logger.info(
            f"Broadcasting from {from_agent}: action={action}, "
            f"targets={len(target_agents)}"
        )
        
        return [agent.agent_id for agent in target_agents]
    
    async def request_analysis(
        self,
        from_agent: str,
        capability: str,
        data: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Request analysis from an agent with a specific capability.
        
        Args:
            from_agent: ID of the requesting agent
            capability: Required capability
            data: Data to analyze
            timeout: Timeout in seconds
            
        Returns:
            Analysis result or None if no capable agent found
        """
        # Find agents with the required capability
        capable_agents = await self.registry.find_agents_by_capability(capability)
        
        if not capable_agents:
            logger.warning(f"No agents found with capability: {capability}")
            return None
        
        # Use the first available agent (could implement load balancing here)
        target_agent = capable_agents[0]
        
        logger.info(
            f"Requesting {capability} analysis from {target_agent.agent_id}"
        )
        
        response = await self.send_message(
            from_agent=from_agent,
            to_agent=target_agent.agent_id,
            action=f"analyze_{capability}",
            payload=data,
            requires_response=True,
            timeout_seconds=timeout
        )
        
        if response:
            return response.payload
        return None
    
    async def send_response(
        self,
        original_message: AgentMessage,
        response_payload: Dict[str, Any],
        from_agent: str
    ) -> None:
        """
        Send a response to a previous message.
        
        Args:
            original_message: The message being responded to
            response_payload: Response data
            from_agent: ID of the responding agent
        """
        response = AgentMessage(
            message_type=MessageType.RESPONSE,
            from_agent=from_agent,
            to_agent=original_message.from_agent,
            action=f"response_{original_message.action}",
            payload=response_payload,
            correlation_id=original_message.message_id
        )
        
        # If there's a pending future, resolve it
        if original_message.message_id in self._pending_responses:
            future = self._pending_responses[original_message.message_id]
            if not future.done():
                future.set_result(response)
            del self._pending_responses[original_message.message_id]
        
        logger.info(
            f"Sent response from {from_agent} to {original_message.from_agent}"
        )
    
    def register_handler(self, action: str, handler: Any) -> None:
        """Register a handler for a specific action."""
        self._message_handlers[action] = handler
        logger.info(f"Registered handler for action: {action}")
    
    async def handle_message(self, message: AgentMessage) -> None:
        """Handle an incoming message."""
        if message.action in self._message_handlers:
            handler = self._message_handlers[message.action]
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error handling message {message.action}: {e}")
        else:
            logger.warning(f"No handler registered for action: {message.action}")


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_global_registry() -> AgentRegistry:
    """Get or create the global agent registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry



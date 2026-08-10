"""
Base agent class for all specialized agents.

Provides common functionality for agent lifecycle, communication, and state management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .a2a import (
    AgentCapability,
    AgentInfo,
    AgentMessage,
    AgentProtocol,
    AgentRegistry,
    MessagePriority,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    Provides:
    - Agent lifecycle management (start, stop, heartbeat)
    - A2A protocol integration
    - Message handling
    - State management
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        registry: AgentRegistry,
        protocol: AgentProtocol,
        capabilities: Optional[List[AgentCapability]] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.registry = registry
        self.protocol = protocol
        self.capabilities = capabilities or []
        
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(f"Initialized {self.agent_type} agent: {self.agent_id}")
    
    async def start(self) -> None:
        """Start the agent and register it in the system."""
        if self._running:
            logger.warning(f"Agent {self.agent_id} is already running")
            return
        
        # Register agent
        agent_info = AgentInfo(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
            status="active",
            metadata=self.get_metadata()
        )
        
        # Register with agent instance so A2A can call process_message
        await self.registry.register(agent_info, agent_instance=self)
        
        # Start heartbeat
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Agent-specific initialization
        await self.on_start()
        
        logger.info(f"Agent {self.agent_id} started successfully")
    
    async def stop(self) -> None:
        """Stop the agent and unregister it."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Agent-specific cleanup
        await self.on_stop()
        
        # Unregister agent
        await self.registry.unregister(self.agent_id)
        
        logger.info(f"Agent {self.agent_id} stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to the registry."""
        while self._running:
            try:
                await self.registry.update_heartbeat(self.agent_id)
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error for {self.agent_id}: {e}")
    
    async def send_message(
        self,
        to_agent: str,
        action: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False
    ) -> Optional[AgentMessage]:
        """Send a message to another agent."""
        return await self.protocol.send_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            action=action,
            payload=payload,
            priority=priority,
            requires_response=requires_response
        )
    
    async def broadcast(
        self,
        action: str,
        payload: Dict[str, Any],
        agent_types: Optional[List[str]] = None
    ) -> List[str]:
        """Broadcast a message to multiple agents."""
        return await self.protocol.broadcast(
            from_agent=self.agent_id,
            action=action,
            payload=payload,
            agent_types=agent_types
        )
    
    async def request_analysis(
        self,
        capability: str,
        data: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Request analysis from an agent with a specific capability."""
        return await self.protocol.request_analysis(
            from_agent=self.agent_id,
            capability=capability,
            data=data,
            timeout=timeout
        )
    
    async def handle_message(self, message: AgentMessage) -> None:
        """
        Handle an incoming message.
        
        Routes to specific handler methods based on action.
        """
        try:
            # Update status to busy
            await self.registry.update_status(self.agent_id, "busy")
            
            # Process message
            result = await self.process_message(message)
            
            # Send response if required
            if message.requires_response:
                await self.protocol.send_response(
                    original_message=message,
                    response_payload=result or {},
                    from_agent=self.agent_id
                )
            
            # Update status back to active
            await self.registry.update_status(self.agent_id, "active")
            
        except Exception as e:
            logger.error(f"Error handling message in {self.agent_id}: {e}")
            await self.registry.update_status(self.agent_id, "active")
    
    # Abstract methods to be implemented by subclasses
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process an incoming message and return result.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get agent-specific metadata.
        
        Must be implemented by subclasses.
        """
        pass
    
    async def on_start(self) -> None:
        """Hook called when agent starts. Override in subclasses if needed."""
        pass
    
    async def on_stop(self) -> None:
        """Hook called when agent stops. Override in subclasses if needed."""
        pass
    
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self._running



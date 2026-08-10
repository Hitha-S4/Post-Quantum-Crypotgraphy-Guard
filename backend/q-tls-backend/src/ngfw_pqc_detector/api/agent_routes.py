"""
Separate agent routes file to isolate agent endpoint
"""
import logging
from fastapi import APIRouter, HTTPException, Request

from ngfw_pqc_detector.agent_graph import SecurityAnalystAgentGraph
from ngfw_pqc_detector.agent_models import SecurityAnalystAgentRequest

logger = logging.getLogger(__name__)

agent_router = APIRouter()

# Lazy initialization for legacy agent
_agent_graph = None
_modern_orchestrator = None
_agent_registry = None
_agent_protocol = None
_initialization_count = 0

def get_agent_graph():
    """Get legacy agent (for backward compatibility)."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = SecurityAnalystAgentGraph()
    return _agent_graph


def get_modern_orchestrator(accumulated_stats_service=None, alert_service=None):
    """Get modern LangGraph orchestrator with A2A protocol."""
    global _modern_orchestrator, _agent_registry, _agent_protocol, _initialization_count
    
    if _modern_orchestrator is None:
        try:
            from ngfw_pqc_detector.agents.protocol.a2a import AgentRegistry, AgentProtocol, AgentCapability
            from ngfw_pqc_detector.agents.orchestrator import OrchestratorAgent
            from ngfw_pqc_detector.core.config import settings
            
            # Initialize registry and protocol
            _agent_registry = AgentRegistry()
            _agent_protocol = AgentProtocol(_agent_registry)
            
            # Import REAL agent implementations
            from ngfw_pqc_detector.agents.specialized.pqc_agent import PQCExpertAgent
            from ngfw_pqc_detector.agents.specialized.security_agent import SecurityAnalystAgent
            
            # Create REAL PQC agent with actual service
            pqc_agent = PQCExpertAgent(
                agent_id="pqc_expert",
                agent_type="pqc_expert",
                registry=_agent_registry,
                protocol=_agent_protocol,
                capabilities=[
                    AgentCapability(name="pqc_analysis", description="Analyzes post-quantum cryptography usage"),
                    AgentCapability(name="algorithm_detection", description="Detects PQC algorithms in use")
                ],
                accumulated_stats_service=accumulated_stats_service
            )
            
            # Create REAL Security Analyst agent
            security_agent = SecurityAnalystAgent(
                agent_id="security_analyst",
                agent_type="security_analyst",
                registry=_agent_registry,
                protocol=_agent_protocol,
                capabilities=[
                    AgentCapability(name="security_analysis", description="Analyzes network security posture"),
                    AgentCapability(name="threat_assessment", description="Assesses security threats and risks")
                ],
                alert_service=alert_service,
                accumulated_stats_service=accumulated_stats_service
            )
            
            # Start the agents to register them
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(pqc_agent.start())
                asyncio.create_task(security_agent.start())
            else:
                loop.run_until_complete(pqc_agent.start())
                loop.run_until_complete(security_agent.start())
            
            logger.info(f"Started REAL PQC Expert and Security Analyst agents with live data access")
            
            # Initialize orchestrator
            _modern_orchestrator = OrchestratorAgent(
                agent_id="main_orchestrator",
                registry=_agent_registry,
                protocol=_agent_protocol,
                llm_base_url=getattr(settings, 'AGENT_LOCAL_BASE_URL', 'http://localhost:11434'),
                model_name=getattr(settings, 'AGENT_MODEL', 'llama3')
            )
            
            _initialization_count += 1
            logger.info(f"Modern LangGraph orchestrator initialized (count: {_initialization_count})")
        except Exception as e:
            logger.error(f"Failed to initialize modern orchestrator: {e}")
            raise
    elif accumulated_stats_service is not None or alert_service is not None:
        # Services will be injected when agents process messages
        # Agents get services from app.state in their process_message method
        logger.info("Services available for agent injection")
    
    return _modern_orchestrator


@agent_router.post("/ai/agent/security-analyst")
async def run_security_analyst_agent(request: SecurityAnalystAgentRequest):
    """
    Run the security analyst agent workflow (legacy endpoint).
    
    This endpoint uses the original agent implementation for backward compatibility.
    For the modern multi-agent system, use /ai/agent/orchestrator
    """
    logger.info("Security analyst agent endpoint called (legacy)")
    try:
        agent = get_agent_graph()
        logger.info(f"Agent graph obtained: {agent}")
        result = await agent.run(request)
        logger.info("Agent execution completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error running security analyst agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run security analyst agent: {str(e)}")


@agent_router.post("/ai/agent/orchestrator")
async def run_orchestrator_agent(request: SecurityAnalystAgentRequest, http_request: Request):
    """
    Run the modern LangGraph orchestrator with multi-agent coordination.
    
    This endpoint uses:
    - LangGraph for state machine orchestration
    - A2A protocol for agent-to-agent communication
    - Multiple specialized agents working together
    - Advanced routing and aggregation
    
    Features:
    - Automatic agent selection based on query
    - Parallel agent invocation
    - Result aggregation with confidence scoring
    - LLM-powered response generation
    """
    logger.info("Modern orchestrator endpoint called")
    logger.info(f"Query: {request.query}")
    
    try:
        # Get services from app state
        accumulated_stats_service = getattr(http_request.app.state, 'accumulated_stats_service', None)
        alert_service = getattr(http_request.app.state, 'alert_service', None)
        
        if accumulated_stats_service:
            logger.info("✓ Got accumulated_stats_service from app.state")
        else:
            logger.warning("⚠ accumulated_stats_service not found in app.state")
            
        if alert_service:
            logger.info("✓ Got alert_service from app.state")
        else:
            logger.warning("⚠ alert_service not found in app.state")
        
        # Get orchestrator instance with services
        orchestrator = get_modern_orchestrator(
            accumulated_stats_service=accumulated_stats_service,
            alert_service=alert_service
        )
        
        # Start orchestrator if not running
        if not orchestrator.is_running():
            await orchestrator.start()
            logger.info("Orchestrator started")
        
        # Run the query through LangGraph workflow
        result = await orchestrator.run_query(request)
        
        logger.info("Orchestrator execution completed successfully")
        logger.info(f"Confidence: {result.confidence:.2f}, Risk: {result.risk_level}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error running orchestrator: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run orchestrator agent: {str(e)}"
        )


@agent_router.get("/ai/agent/status")
async def get_agent_status():
    """
    Get status of all agents in the system.
    
    Returns information about:
    - Registered agents
    - Agent capabilities
    - Agent health status
    - System metrics
    """
    try:
        orchestrator = get_modern_orchestrator()
        
        if not orchestrator.is_running():
            return {
                "status": "stopped",
                "message": "Orchestrator is not running",
                "agents": []
            }
        
        # Get all registered agents
        registry = orchestrator.registry
        agents = await registry.list_all_agents()
        
        return {
            "status": "running",
            "orchestrator": {
                "agent_id": orchestrator.agent_id,
                "type": orchestrator.agent_type,
                "running": orchestrator.is_running(),
                "metadata": orchestrator.get_metadata()
            },
            "registered_agents": [
                {
                    "agent_id": agent.agent_id,
                    "type": agent.agent_type,
                    "status": agent.status,
                    "capabilities": [cap.name for cap in agent.capabilities],
                    "last_heartbeat": agent.last_heartbeat
                }
                for agent in agents
            ],
            "total_agents": len(agents)
        }
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {
            "status": "error",
            "message": str(e),
            "agents": []
        }



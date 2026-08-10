"""
LangGraph-based Orchestrator Agent.

This is the main coordinator that routes queries to specialized agents
and aggregates their results using LangGraph state machine.
"""

import logging
from typing import Annotated, Any, Dict, List, Literal, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from ..agent_models import (
    AgentExecutionStatus,
    AgentSeverity,
    SecurityAnalystAgentRequest,
    SecurityAnalystAgentResponse,
)
from .protocol.a2a import AgentProtocol, AgentRegistry, MessagePriority
from .protocol.base_agent import AgentCapability, BaseAgent

logger = logging.getLogger(__name__)


class OrchestratorState(TypedDict):
    """State for the orchestrator LangGraph."""
    
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    selected_agents: List[str]
    agent_results: Dict[str, Any]
    final_answer: str
    confidence: float
    risk_level: str
    metadata: Dict[str, Any]
    next_step: str


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent using LangGraph for state machine coordination.
    
    Routes queries to specialized agents and aggregates results.
    """
    
    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        protocol: AgentProtocol,
        llm_base_url: str = "http://localhost:11434",
        model_name: str = "llama3"
    ):
        capabilities = [
            AgentCapability(
                name="orchestrate",
                description="Coordinate multiple specialized agents",
                tags=["coordination", "routing", "aggregation"]
            ),
            AgentCapability(
                name="route_query",
                description="Route queries to appropriate specialized agents",
                tags=["routing", "decision-making"]
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            agent_type="orchestrator",
            registry=registry,
            protocol=protocol,
            capabilities=capabilities
        )
        
        # Initialize LLM
        self.llm = ChatOllama(
            base_url=llm_base_url,
            model=model_name,
            temperature=0.2
        )
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        
        logger.info(f"Orchestrator agent initialized with LangGraph")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph state machine for orchestration."""
        
        workflow = StateGraph(OrchestratorState)
        
        # Add nodes
        workflow.add_node("router", self._node_router)
        workflow.add_node("security_analyst", self._node_security_analyst)
        workflow.add_node("network_topology", self._node_network_topology)
        workflow.add_node("pqc_expert", self._node_pqc_expert)
        workflow.add_node("aggregator", self._node_aggregator)
        workflow.add_node("responder", self._node_responder)
        
        # Set entry point
        workflow.set_entry_point("router")
        
        # Add conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "security_analyst": "security_analyst",
                "network_topology": "network_topology",
                "pqc_expert": "pqc_expert",
                "aggregator": "aggregator"
            }
        )
        
        # All specialized agents go to aggregator
        workflow.add_edge("security_analyst", "aggregator")
        workflow.add_edge("network_topology", "aggregator")
        workflow.add_edge("pqc_expert", "aggregator")
        
        # Aggregator goes to responder
        workflow.add_edge("aggregator", "responder")
        
        # Responder is the end
        workflow.add_edge("responder", END)
        
        return workflow
    
    async def _node_router(self, state: OrchestratorState) -> OrchestratorState:
        """Route the query to appropriate agents."""
        query = state["query"].lower()
        
        # Determine which agents to invoke based on query
        selected_agents = []
        
        # Security-related queries
        if any(word in query for word in ["alert", "threat", "vulnerability", "attack", "security"]):
            selected_agents.append("security_analyst")
        
        # Network topology queries
        if any(word in query for word in ["topology", "network", "connection", "node", "edge"]):
            selected_agents.append("network_topology")
        
        # PQC-related queries
        if any(word in query for word in ["pqc", "quantum", "cipher", "crypto", "algorithm"]):
            selected_agents.append("pqc_expert")
        
        # Default: use security analyst
        if not selected_agents:
            selected_agents.append("security_analyst")
        
        logger.info(f"Router selected agents: {selected_agents}")
        
        state["selected_agents"] = selected_agents
        state["agent_results"] = {}
        
        return state
    
    def _route_decision(self, state: OrchestratorState) -> str:
        """Decide which agent to invoke next."""
        selected = state["selected_agents"]
        
        if not selected:
            return "aggregator"
        
        # Return the first agent in the list
        next_agent = selected[0]
        
        # Remove it from the list for next iteration
        state["selected_agents"] = selected[1:]
        
        return next_agent
    
    async def _node_security_analyst(self, state: OrchestratorState) -> OrchestratorState:
        """Invoke security analyst agent."""
        logger.info("Invoking security analyst agent")
        
        try:
            # Find security analyst agent
            agents = await self.registry.find_agents_by_type("security_analyst")
            
            if agents:
                result = await self.request_analysis(
                    capability="security_analysis",
                    data={"query": state["query"]},
                    timeout=30
                )
                
                if result:
                    state["agent_results"]["security_analyst"] = result
                    logger.info("Security analyst completed")
            else:
                logger.warning("No security analyst agent found")
                state["agent_results"]["security_analyst"] = {
                    "error": "Security analyst not available"
                }
        
        except Exception as e:
            logger.error(f"Error invoking security analyst: {e}")
            state["agent_results"]["security_analyst"] = {"error": str(e)}
        
        return state
    
    async def _node_network_topology(self, state: OrchestratorState) -> OrchestratorState:
        """Invoke network topology agent."""
        logger.info("Invoking network topology agent")
        
        try:
            result = await self.request_analysis(
                capability="topology_analysis",
                data={"query": state["query"]},
                timeout=30
            )
            
            if result:
                state["agent_results"]["network_topology"] = result
                logger.info("Network topology agent completed")
            else:
                state["agent_results"]["network_topology"] = {
                    "info": "Topology analysis not available"
                }
        
        except Exception as e:
            logger.error(f"Error invoking network topology agent: {e}")
            state["agent_results"]["network_topology"] = {"error": str(e)}
        
        return state
    
    async def _node_pqc_expert(self, state: OrchestratorState) -> OrchestratorState:
        """Invoke PQC expert agent."""
        logger.info("Invoking PQC expert agent")
        
        try:
            result = await self.request_analysis(
                capability="pqc_analysis",
                data={"query": state["query"]},
                timeout=30
            )
            
            if result:
                state["agent_results"]["pqc_expert"] = result
                logger.info("PQC expert completed")
            else:
                state["agent_results"]["pqc_expert"] = {
                    "info": "PQC analysis not available"
                }
        
        except Exception as e:
            logger.error(f"Error invoking PQC expert: {e}")
            state["agent_results"]["pqc_expert"] = {"error": str(e)}
        
        return state
    
    async def _node_aggregator(self, state: OrchestratorState) -> OrchestratorState:
        """Aggregate results from all agents."""
        logger.info("Aggregating results from agents")
        
        results = state["agent_results"]
        
        # Calculate confidence based on successful agent responses
        successful_agents = sum(
            1 for result in results.values()
            if "error" not in result
        )
        total_agents = len(results) if results else 1
        confidence = successful_agents / total_agents
        
        state["confidence"] = confidence
        state["metadata"] = {
            "agents_invoked": list(results.keys()),
            "successful_agents": successful_agents,
            "total_agents": total_agents
        }
        
        logger.info(f"Aggregation complete: confidence={confidence:.2f}")
        
        return state
    
    async def _node_responder(self, state: OrchestratorState) -> OrchestratorState:
        """Generate final response using LLM."""
        logger.info("Generating final response")
        
        # Prepare context for LLM
        context = f"Query: {state['query']}\n\n"
        context += "Agent Results:\n"
        
        for agent_name, result in state["agent_results"].items():
            context += f"\n{agent_name}:\n{result}\n"
        
        # Generate response
        messages = [
            SystemMessage(content="You are a security analyst coordinating multiple specialized agents. Synthesize their findings into a clear, actionable response."),
            HumanMessage(content=context)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            state["final_answer"] = response.content
            
            # Determine risk level based on results
            state["risk_level"] = self._determine_risk_level(state["agent_results"])
            
            logger.info("Response generation complete")
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state["final_answer"] = "Error generating response. Please try again."
            state["risk_level"] = "medium"
        
        return state
    
    def _determine_risk_level(self, results: Dict[str, Any]) -> str:
        """Determine overall risk level from agent results."""
        # Simple heuristic - can be made more sophisticated
        if any("critical" in str(result).lower() for result in results.values()):
            return "critical"
        elif any("high" in str(result).lower() for result in results.values()):
            return "high"
        elif any("error" in result for result in results.values()):
            return "medium"
        else:
            return "low"
    
    async def process_message(self, message: Any) -> Dict[str, Any]:
        """Process incoming message using LangGraph workflow."""
        try:
            query = message.payload.get("query", "")
            
            # Initialize state
            initial_state: OrchestratorState = {
                "messages": [HumanMessage(content=query)],
                "query": query,
                "selected_agents": [],
                "agent_results": {},
                "final_answer": "",
                "confidence": 0.0,
                "risk_level": "medium",
                "metadata": {},
                "next_step": ""
            }
            
            # Run the workflow
            final_state = await self.app.ainvoke(initial_state)
            
            return {
                "answer": final_state["final_answer"],
                "confidence": final_state["confidence"],
                "risk_level": final_state["risk_level"],
                "agent_results": final_state["agent_results"],
                "metadata": final_state["metadata"]
            }
        
        except Exception as e:
            logger.error(f"Error in orchestrator workflow: {e}")
            return {
                "error": str(e),
                "answer": "An error occurred during orchestration",
                "confidence": 0.0,
                "risk_level": "medium"
            }
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get orchestrator metadata."""
        return {
            "type": "orchestrator",
            "framework": "langgraph",
            "llm_model": self.llm.model,
            "capabilities": ["routing", "aggregation", "coordination"]
        }
    
    async def run_query(self, request: SecurityAnalystAgentRequest) -> SecurityAnalystAgentResponse:
        """
        Main entry point for running queries through the orchestrator.
        
        This is called by the API endpoint.
        """
        try:
            # Create initial state
            initial_state: OrchestratorState = {
                "messages": [HumanMessage(content=request.query)],
                "query": request.query,
                "selected_agents": [],
                "agent_results": {},
                "final_answer": "",
                "confidence": 0.0,
                "risk_level": "medium",
                "metadata": {},
                "next_step": ""
            }
            
            # Run the LangGraph workflow
            final_state = await self.app.ainvoke(initial_state)
            
            # Build response
            response = SecurityAnalystAgentResponse(
                conversation_id=request.conversation_id or "default",
                query=request.query,
                status="completed",  # Use string literal, not enum
                summary=f"Orchestrated analysis using {len(final_state['agent_results'])} agents",
                answer=final_state["final_answer"],
                risk_level=final_state["risk_level"],  # Already a string from state
                confidence=final_state["confidence"],
                tool_calls=[],
                evidence=[],
                metrics=final_state["metadata"],
                trace=[],
                verification={
                    "grounded": True,
                    "sufficient": final_state["confidence"] > 0.5,
                    "issues": [],
                    "grounded_tool_names": list(final_state["agent_results"].keys())
                },
                generated_at="",
                provider={"name": "langgraph", "model": self.llm.model}
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Error in run_query: {e}")
            raise



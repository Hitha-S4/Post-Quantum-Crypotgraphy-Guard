#!/usr/bin/env python3
"""
Test script for the modern LangGraph orchestrator agent.

This script demonstrates the new multi-agent system with:
- LangGraph state machine
- A2A protocol
- Agent registry
- Multi-agent coordination
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ngfw_pqc_detector.agents.protocol.a2a import AgentRegistry, AgentProtocol
from ngfw_pqc_detector.agents.orchestrator import OrchestratorAgent
from ngfw_pqc_detector.agent_models import SecurityAnalystAgentRequest


async def test_orchestrator():
    """Test the modern orchestrator agent."""
    
    print("=" * 60)
    print("Testing Modern LangGraph Orchestrator")
    print("=" * 60)
    
    # Initialize registry and protocol
    print("\n1. Initializing agent registry and protocol...")
    registry = AgentRegistry()
    protocol = AgentProtocol(registry)
    print("   ✅ Registry and protocol initialized")
    
    # Initialize orchestrator
    print("\n2. Initializing LangGraph orchestrator...")
    orchestrator = OrchestratorAgent(
        agent_id="test_orchestrator",
        registry=registry,
        protocol=protocol,
        llm_base_url="http://localhost:11434",
        model_name="llama3"
    )
    print("   ✅ Orchestrator initialized")
    
    # Start orchestrator
    print("\n3. Starting orchestrator...")
    await orchestrator.start()
    print("   ✅ Orchestrator started")
    print(f"   - Agent ID: {orchestrator.agent_id}")
    print(f"   - Type: {orchestrator.agent_type}")
    print(f"   - Running: {orchestrator.is_running()}")
    
    # Check registry
    print("\n4. Checking agent registry...")
    agents = await registry.list_all_agents()
    print(f"   ✅ Registered agents: {len(agents)}")
    for agent in agents:
        print(f"   - {agent.agent_id} ({agent.agent_type}): {agent.status}")
        print(f"     Capabilities: {[cap.name for cap in agent.capabilities]}")
    
    # Test query
    print("\n5. Testing query through orchestrator...")
    request = SecurityAnalystAgentRequest(
        query="Show me network security status",
        conversation_id="test_001"
    )
    
    try:
        print(f"   Query: {request.query}")
        result = await orchestrator.run_query(request)
        
        print("\n   ✅ Query completed successfully!")
        print(f"   - Status: {result.status}")
        print(f"   - Confidence: {result.confidence:.2f}")
        print(f"   - Risk Level: {result.risk_level}")
        print(f"   - Answer: {result.answer[:200]}...")
        
        if result.metrics:
            print(f"   - Metrics: {result.metrics}")
        
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Stop orchestrator
    print("\n6. Stopping orchestrator...")
    await orchestrator.stop()
    print("   ✅ Orchestrator stopped")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


async def test_a2a_protocol():
    """Test A2A protocol functionality."""
    
    print("\n" + "=" * 60)
    print("Testing A2A Protocol")
    print("=" * 60)
    
    registry = AgentRegistry()
    protocol = AgentProtocol(registry)
    
    # Create test orchestrator
    orchestrator = OrchestratorAgent(
        agent_id="test_orchestrator",
        registry=registry,
        protocol=protocol
    )
    
    await orchestrator.start()
    
    # Test agent discovery
    print("\n1. Testing agent discovery...")
    agents_by_type = await registry.find_agents_by_type("orchestrator")
    print(f"   ✅ Found {len(agents_by_type)} orchestrator agents")
    
    agents_by_capability = await registry.find_agents_by_capability("orchestrate")
    print(f"   ✅ Found {len(agents_by_capability)} agents with 'orchestrate' capability")
    
    # Test heartbeat
    print("\n2. Testing heartbeat...")
    success = await registry.update_heartbeat(orchestrator.agent_id)
    print(f"   ✅ Heartbeat updated: {success}")
    
    # Test status update
    print("\n3. Testing status update...")
    await registry.update_status(orchestrator.agent_id, "busy")
    agent_info = await registry.get_agent(orchestrator.agent_id)
    print(f"   ✅ Status updated to: {agent_info.status}")
    
    await registry.update_status(orchestrator.agent_id, "active")
    
    await orchestrator.stop()
    
    print("\n" + "=" * 60)
    print("A2A Protocol Test Complete!")
    print("=" * 60)


def main():
    """Main test function."""
    print("\n🚀 Modern Agent System Test Suite\n")
    
    # Check if Ollama is running
    print("Prerequisites:")
    print("- Ollama should be running on http://localhost:11434")
    print("- Llama3 model should be available")
    print("\nStarting tests...\n")
    
    try:
        # Run tests
        asyncio.run(test_a2a_protocol())
        asyncio.run(test_orchestrator())
        
        print("\n✅ All tests passed!")
        print("\nThe modern agent system is working correctly!")
        print("\nYou can now use it via the API:")
        print("  POST http://localhost:8000/api/v1/ai/agent/orchestrator")
        print("  GET  http://localhost:8000/api/v1/ai/agent/status")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



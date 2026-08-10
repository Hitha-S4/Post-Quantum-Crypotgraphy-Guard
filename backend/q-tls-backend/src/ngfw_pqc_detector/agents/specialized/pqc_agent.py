"""
PQC Expert Agent - Analyzes Post-Quantum Cryptography usage and provides insights.
"""

import logging
from typing import Any, Dict

from ngfw_pqc_detector.agents.protocol.base_agent import BaseAgent
from ngfw_pqc_detector.agents.protocol.a2a import AgentMessage

logger = logging.getLogger(__name__)


class PQCExpertAgent(BaseAgent):
    """
    Specialized agent for Post-Quantum Cryptography analysis.
    Fetches real data from accumulated stats service.
    """
    
    def __init__(self, *args, accumulated_stats_service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats_service = accumulated_stats_service
        logger.info(f"PQC Expert Agent initialized: {self.agent_id}")
    
    async def process_message(self, message: Any) -> Dict[str, Any]:
        """
        Process incoming analysis requests and return real PQC data.
        """
        try:
            logger.info(f"PQC Expert processing message")
            
            # Get stats service from app if not set
            if self.stats_service is None:
                from ngfw_pqc_detector.main import app
                if hasattr(app.state, 'accumulated_stats_service'):
                    self.stats_service = app.state.accumulated_stats_service
                else:
                    logger.error("Stats service not available in app state")
                    return {
                        "status": "error",
                        "message": "Statistics service not initialized"
                    }
            
            # Get real accumulated statistics
            stats = await self.stats_service.get_accumulated_stats()
            
            if not stats:
                return {
                    "status": "error",
                    "message": "No PQC statistics available",
                    "pqc_connections": 0,
                    "classical_connections": 0
                }
            
            # Calculate metrics using correct field names
            pqc_total = stats.total_pqc_safe + stats.total_pqc_vulnerable
            classical_total = stats.total_tls_flows - pqc_total if stats.total_tls_flows > pqc_total else 0
            total = stats.total_tls_flows
            pqc_percentage = (pqc_total / total * 100) if total > 0 else 0
            
            # Extract top algorithms from key exchange distribution
            top_algorithms = []
            if hasattr(stats, 'key_exchange_distribution') and stats.key_exchange_distribution:
                # Get PQC algorithms from key exchange distribution
                for algo, count in sorted(
                    stats.key_exchange_distribution.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]:
                    # Filter for PQC algorithms (typically contain "kyber", "dilithium", etc.)
                    if any(pqc_term in algo.lower() for pqc_term in ['kyber', 'dilithium', 'falcon', 'sphincs', 'ntru']):
                        top_algorithms.append(algo)
            
            # Build comprehensive response
            response = {
                "status": "success",
                "pqc_status": f"PQC adoption at {pqc_percentage:.1f}%",
                "summary": self._generate_summary(pqc_percentage, pqc_total, classical_total),
                "metrics": {
                    "pqc_connections": pqc_total,
                    "classical_connections": classical_total,
                    "total_connections": total,
                    "pqc_percentage": round(pqc_percentage, 2)
                },
                "algorithms": {
                    "top_algorithms": top_algorithms[:3] if top_algorithms else ["No PQC algorithms detected"],
                    "total_unique": len(top_algorithms)
                },
                "posture_distribution": {
                    "pqc_safe": stats.total_pqc_safe,
                    "pqc_vulnerable": stats.total_pqc_vulnerable,
                    "pqc_unknown": stats.total_pqc_unknown,
                    "classical": classical_total
                },
                "recommendation": self._generate_recommendation(pqc_percentage),
                "risk_assessment": self._assess_risk(pqc_percentage),
                "timestamp": stats.last_updated.isoformat() if stats.last_updated else None
            }
            
            logger.info(f"PQC analysis complete: {pqc_percentage:.1f}% adoption")
            return response
            
        except Exception as e:
            logger.error(f"Error in PQC analysis: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to analyze PQC data: {str(e)}"
            }
    
    def _generate_summary(self, pqc_pct: float, pqc_count: int, classical_count: int) -> str:
        """Generate human-readable summary."""
        if pqc_pct == 0:
            return f"No PQC adoption detected. All {classical_count} connections use classical cryptography."
        elif pqc_pct < 25:
            return f"Low PQC adoption ({pqc_pct:.1f}%). {pqc_count} PQC vs {classical_count} classical connections."
        elif pqc_pct < 50:
            return f"Moderate PQC adoption ({pqc_pct:.1f}%). {pqc_count} connections using post-quantum algorithms."
        elif pqc_pct < 75:
            return f"Good PQC adoption ({pqc_pct:.1f}%). {pqc_count} PQC-protected connections."
        else:
            return f"Excellent PQC adoption ({pqc_pct:.1f}%). {pqc_count} connections quantum-resistant."
    
    def _generate_recommendation(self, pqc_pct: float) -> str:
        """Generate actionable recommendations."""
        if pqc_pct == 0:
            return "URGENT: Begin PQC migration immediately. All connections vulnerable to quantum attacks."
        elif pqc_pct < 25:
            return "HIGH PRIORITY: Accelerate PQC adoption. Most connections remain vulnerable."
        elif pqc_pct < 50:
            return "RECOMMENDED: Continue PQC migration efforts. Half of connections still at risk."
        elif pqc_pct < 75:
            return "GOOD PROGRESS: Maintain momentum. Focus on remaining classical connections."
        else:
            return "EXCELLENT: Strong quantum resistance. Monitor and maintain PQC coverage."
    
    def _assess_risk(self, pqc_pct: float) -> str:
        """Assess quantum threat risk level."""
        if pqc_pct < 25:
            return "CRITICAL"
        elif pqc_pct < 50:
            return "HIGH"
        elif pqc_pct < 75:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return agent metadata."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": [cap.name for cap in (self.capabilities or [])],
            "status": "active",
            "description": "Analyzes post-quantum cryptography adoption and provides security recommendations"
        }

# Made with Bob

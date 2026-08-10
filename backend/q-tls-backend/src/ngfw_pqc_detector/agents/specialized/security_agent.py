"""
Security Analyst Agent - Analyzes security posture and threats
"""
import logging
from typing import Dict, Any, Optional
from ngfw_pqc_detector.agents.protocol.base_agent import BaseAgent
from ngfw_pqc_detector.agents.protocol.a2a import AgentCapability

logger = logging.getLogger(__name__)


class SecurityAnalystAgent(BaseAgent):
    """
    Security analyst agent that analyzes network security posture,
    identifies threats, and provides recommendations.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        registry,
        protocol,
        capabilities: list[AgentCapability],
        alert_service=None,
        accumulated_stats_service=None
    ):
        super().__init__(agent_id, agent_type, registry, protocol, capabilities)
        self.alert_service = alert_service
        self.stats_service = accumulated_stats_service
    
    async def process_message(self, message: Any) -> Dict[str, Any]:
        """
        Process security analysis requests and return threat assessment.
        """
        try:
            logger.info(f"Security Analyst processing message")
            
            # Get services from app if not set
            if self.alert_service is None or self.stats_service is None:
                from ngfw_pqc_detector.main import app
                if hasattr(app.state, 'alert_service'):
                    self.alert_service = app.state.alert_service
                if hasattr(app.state, 'accumulated_stats_service'):
                    self.stats_service = app.state.accumulated_stats_service
            
            if not self.alert_service or not self.stats_service:
                logger.error("Required services not available")
                return {
                    "status": "error",
                    "message": "Security services not initialized"
                }
            
            # Get real security data
            stats = await self.stats_service.get_accumulated_stats()
            
            if not stats:
                return {
                    "status": "error",
                    "message": "No security statistics available"
                }
            
            # Calculate security metrics
            total_alerts = stats.total_alerts
            critical_alerts = stats.total_critical_alerts
            high_alerts = stats.total_high_alerts
            medium_alerts = stats.total_medium_alerts
            low_alerts = stats.total_low_alerts
            
            # Calculate threat level
            threat_score = (
                (critical_alerts * 10) +
                (high_alerts * 5) +
                (medium_alerts * 2) +
                (low_alerts * 1)
            )
            
            # Assess security posture
            pqc_safe = stats.total_pqc_safe
            pqc_vulnerable = stats.total_pqc_vulnerable
            total_tls = stats.total_tls_flows
            
            vulnerability_percentage = (pqc_vulnerable / total_tls * 100) if total_tls > 0 else 0
            
            # Build comprehensive response
            response = {
                "status": "success",
                "security_posture": self._assess_posture(threat_score, vulnerability_percentage),
                "summary": self._generate_summary(total_alerts, critical_alerts, vulnerability_percentage),
                "threat_metrics": {
                    "total_alerts": total_alerts,
                    "critical_alerts": critical_alerts,
                    "high_alerts": high_alerts,
                    "medium_alerts": medium_alerts,
                    "low_alerts": low_alerts,
                    "threat_score": threat_score
                },
                "vulnerability_assessment": {
                    "pqc_safe_connections": pqc_safe,
                    "pqc_vulnerable_connections": pqc_vulnerable,
                    "total_tls_connections": total_tls,
                    "vulnerability_percentage": round(vulnerability_percentage, 2)
                },
                "risk_level": self._assess_risk(threat_score, vulnerability_percentage),
                "recommendations": self._generate_recommendations(critical_alerts, vulnerability_percentage),
                "priority_actions": self._get_priority_actions(critical_alerts, high_alerts)
            }
            
            logger.info(f"Security analysis complete: {response['security_posture']}")
            return response
            
        except Exception as e:
            logger.error(f"Error in security analysis: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Security analysis failed: {str(e)}"
            }
    
    def _assess_posture(self, threat_score: int, vulnerability_pct: float) -> str:
        """Assess overall security posture"""
        if threat_score > 100 or vulnerability_pct > 50:
            return "CRITICAL - Immediate action required"
        elif threat_score > 50 or vulnerability_pct > 25:
            return "HIGH RISK - Urgent attention needed"
        elif threat_score > 20 or vulnerability_pct > 10:
            return "MODERATE RISK - Monitoring required"
        else:
            return "GOOD - Continue monitoring"
    
    def _generate_summary(self, total_alerts: int, critical: int, vuln_pct: float) -> str:
        """Generate security summary"""
        return (
            f"Security analysis shows {total_alerts} total alerts "
            f"({critical} critical). {vuln_pct:.1f}% of connections are "
            f"vulnerable to quantum attacks."
        )
    
    def _assess_risk(self, threat_score: int, vulnerability_pct: float) -> str:
        """Assess risk level"""
        if threat_score > 100 or vulnerability_pct > 50:
            return "critical"
        elif threat_score > 50 or vulnerability_pct > 25:
            return "high"
        elif threat_score > 20 or vulnerability_pct > 10:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, critical: int, vuln_pct: float) -> list[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if critical > 0:
            recommendations.append(
                f"Address {critical} critical alerts immediately"
            )
        
        if vuln_pct > 25:
            recommendations.append(
                "Accelerate PQC adoption to reduce quantum vulnerability"
            )
        elif vuln_pct > 10:
            recommendations.append(
                "Plan PQC migration for vulnerable connections"
            )
        
        if not recommendations:
            recommendations.append(
                "Maintain current security posture and continue monitoring"
            )
        
        return recommendations
    
    def _get_priority_actions(self, critical: int, high: int) -> list[str]:
        """Get priority actions"""
        actions = []
        
        if critical > 0:
            actions.append("Investigate and remediate critical alerts")
        
        if high > 5:
            actions.append("Review and address high-priority alerts")
        
        if critical == 0 and high == 0:
            actions.append("Continue routine security monitoring")
        
        return actions
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return agent metadata"""
        return {
            "version": "1.0.0",
            "specialization": "security_analysis",
            "data_sources": ["alerts", "accumulated_stats"],
            "capabilities": ["threat_assessment", "vulnerability_analysis", "risk_scoring"]
        }
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info(f"Security Analyst Agent {self.agent_id} started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info(f"Security Analyst Agent {self.agent_id} stopped")

# Made with Bob

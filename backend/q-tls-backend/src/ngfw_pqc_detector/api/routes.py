"""
API Routes for NGFW PQC Detector
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ngfw_pqc_detector.services.database import DatabaseService
from ngfw_pqc_detector.services.analytics_engine import SuricataAnalytics
from ngfw_pqc_detector.models import TLSConnection
from ngfw_pqc_detector.core.config import settings

logger = logging.getLogger(__name__)

# Import agent modules - these MUST succeed for the agent route to work
from ngfw_pqc_detector.agent_graph import SecurityAnalystAgentGraph
from ngfw_pqc_detector.agent_models import SecurityAnalystAgentRequest

router = APIRouter()
db_service = DatabaseService()
analytics = SuricataAnalytics()

# Lazy initialization to avoid import-time errors
_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = SecurityAnalystAgentGraph()
    return _agent_graph


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "NGFW PQC Detector"}


@router.get("/stats")
async def get_stats():
    """Get TLS connection statistics"""
    try:
        stats = await db_service.get_connection_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/connections/recent")
async def get_recent_connections(limit: int = Query(default=100, ge=1, le=1000)):
    """Get recent TLS connections"""
    try:
        connections = await db_service.get_recent_connections(limit=limit)
        return {
            "count": len(connections),
            "connections": [
                {
                    "id": conn["id"],
                    "timestamp": conn["timestamp"].isoformat(),
                    "source_ip": conn["source_ip"],
                    "source_port": conn["source_port"],
                    "destination_ip": conn["destination_ip"],
                    "destination_port": conn["destination_port"],
                    "server_name": conn.get("server_name"),
                    "tls_version": conn["tls_version"],
                    "crypto_type": conn["crypto_type"],
                    "is_pqc": conn["is_pqc"],
                    "is_hybrid": conn["is_hybrid"],
                    "detection_confidence": conn["detection_confidence"],
                }
                for conn in connections
            ],
        }
    except Exception as e:
        logger.error(f"Error getting recent connections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve connections")


@router.get("/connections/pqc")
async def get_pqc_connections(limit: int = Query(default=100, ge=1, le=1000)):
    """Get connections using Post-Quantum Cryptography"""
    try:
        connections = await db_service.get_pqc_connections(limit=limit)
        return {
            "count": len(connections),
            "connections": [
                {
                    "id": conn["id"],
                    "timestamp": conn["timestamp"].isoformat(),
                    "source_ip": conn["source_ip"],
                    "source_port": conn["source_port"],
                    "destination_ip": conn["destination_ip"],
                    "destination_port": conn["destination_port"],
                    "server_name": conn.get("server_name"),
                    "tls_version": conn["tls_version"],
                    "crypto_type": conn["crypto_type"],
                    "is_hybrid": conn["is_hybrid"],
                    "detection_confidence": conn["detection_confidence"],
                    "cipher_suite": conn.get("cipher_suite_name"),
                }
                for conn in connections
            ],
        }
    except Exception as e:
        logger.error(f"Error getting PQC connections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve PQC connections")


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "NGFW PQC Detector API",
        "version": "2.0.0",
        "description": "Next-Generation Firewall with Post-Quantum Cryptography Detection and Security Alerts",
        "websockets": {
            "batch_updates": "/ws/batch-updates",
            "data_updates": "/ws/data-updates",
            "kafka_stream": "/ws/kafka-stream",
            "alerts": "/ws/alerts",
        },
        "endpoints": {
            "health": "/api/v1/health",
            "stats": "/api/v1/stats",
            "recent_connections": "/api/v1/connections/recent",
            "pqc_connections": "/api/v1/connections/pqc",
            "dashboard": "/api/v1/analytics/dashboard",
            "metrics": "/api/v1/analytics/metrics",
            "alerts_list": "/api/v1/alerts/list",
            "alerts_by_severity": "/api/v1/alerts/by-severity/{severity}",
            "alerts_unacknowledged": "/api/v1/alerts/unacknowledged",
            "alerts_stats": "/api/v1/alerts/stats",
            "acknowledge_alert": "/api/v1/alerts/{alert_id}/acknowledge",
        },
    }


@router.get("/test-before-agent")
async def test_before_agent():
    """Test route to verify routes are being registered"""
    return {"status": "test route works"}


@router.post("/ai/agent/security-analyst")
async def run_security_analyst_agent(request: SecurityAnalystAgentRequest):
    """Run the Layer 1 security analyst agent workflow."""
    logger.info("Security analyst agent endpoint called")
    try:
        agent = get_agent_graph()
        logger.info(f"Agent graph obtained: {agent}")
        result = await agent.run(request)
        logger.info("Agent execution completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error running security analyst agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run security analyst agent: {str(e)}")


@router.get("/analytics/dashboard")
async def get_analytics_dashboard(time_window: int = Query(default=60, ge=1, le=1440)):
    """
    Get complete analytics dashboard data

    Args:
        time_window: Time window in minutes (default: 60, max: 1440/24h)
    """
    try:
        data = await analytics.get_dashboard_summary(time_window)
        data["timestamp"] = datetime.utcnow().isoformat()
        return data
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@router.get("/analytics/metrics")
async def get_analytics_metrics(time_window: int = Query(default=60, ge=1, le=1440)):
    """
    Get key analytics metrics

    Args:
        time_window: Time window in minutes (default: 60, max: 1440/24h)
    """
    try:
        total_flows = await analytics.get_total_flows(time_window)
        tls_connections = await analytics.get_tls_connections(time_window)
        pqc_safe = await analytics.get_pqc_safe_connections(time_window)
        vulnerable = await analytics.get_vulnerable_connections(time_window)

        return {
            "total_flows": total_flows,
            "tls_connections": tls_connections,
            "pqc_safe": pqc_safe,
            "vulnerable": vulnerable,
            "pqc_percentage": (pqc_safe / tls_connections * 100) if tls_connections > 0 else 0,
            "timestamp": datetime.utcnow().isoformat(),
            "time_window_minutes": time_window,
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/analytics/protocol-distribution")
async def get_protocol_distribution(
    time_window: int = Query(default=60, ge=1, le=1440), limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get protocol distribution statistics

    Args:
        time_window: Time window in minutes (default: 60)
        limit: Maximum number of protocols to return (default: 10)
    """
    try:
        data = await analytics.get_protocol_distribution(time_window, limit)
        return {
            "distribution": data,
            "timestamp": datetime.utcnow().isoformat(),
            "time_window_minutes": time_window,
        }
    except Exception as e:
        logger.error(f"Error getting protocol distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve protocol distribution")


@router.get("/analytics/pqc-distribution")
async def get_pqc_distribution(time_window: int = Query(default=60, ge=1, le=1440)):
    """
    Get PQC status distribution

    Args:
        time_window: Time window in minutes (default: 60)
    """
    try:
        data = await analytics.get_pqc_status_distribution(time_window)
        return {
            "distribution": data,
            "timestamp": datetime.utcnow().isoformat(),
            "time_window_minutes": time_window,
        }
    except Exception as e:
        logger.error(f"Error getting PQC distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve PQC distribution")


@router.get("/analytics/live-flows")
async def get_live_flows(limit: int = Query(default=50, ge=1, le=200)):
    """
    Get recent live network flows

    Args:
        limit: Maximum number of flows to return (default: 50)
    """
    try:
        flows = await analytics.get_live_network_flows(limit)
        return {"flows": flows, "count": len(flows), "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting live flows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve live flows")


@router.get("/analytics/security-alerts")
async def get_security_alerts(limit: int = Query(default=10, ge=1, le=100)):
    """
    Get recent security alerts

    Args:
        limit: Maximum number of alerts to return (default: 10)
    """
    try:
        alerts = await analytics.get_security_alerts(limit)
        return {"alerts": alerts, "count": len(alerts), "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting security alerts: {e}", exc_info=True)


@router.get("/statistics/aggregated")
async def get_aggregated_statistics(time_window: int = Query(default=60, ge=1, le=1440)):
    """
    Get aggregated statistics for a time window

    Args:
        time_window: Time window in minutes (default: 60, max: 1440/24h)
    """
    try:
        from ngfw_pqc_detector.services.background_jobs import background_jobs_service

        if not background_jobs_service.stats_service:
            raise HTTPException(status_code=503, detail="Statistics service not initialized")

        stats = await background_jobs_service.stats_service.get_latest_statistics(time_window)

        if not stats:
            raise HTTPException(
                status_code=404, detail="No statistics available for this time window"
            )

        return stats.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting aggregated statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve aggregated statistics")


@router.get("/statistics/live")
async def get_live_statistics():
    """
    Get live statistics including current rates and system health
    """
    try:
        from ngfw_pqc_detector.services.background_jobs import get_current_live_stats

        live_stats = await get_current_live_stats()

        if not live_stats:
            raise HTTPException(status_code=503, detail="Live statistics not available")

        return live_stats.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve live statistics")


@router.get("/statistics/cipher-suites")
async def get_cipher_suite_statistics(
    time_window: int = Query(default=60, ge=1, le=1440), limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get top cipher suites statistics

    Args:
        time_window: Time window in minutes (default: 60)
        limit: Maximum number of cipher suites to return (default: 10)
    """
    try:
        from ngfw_pqc_detector.services.background_jobs import background_jobs_service

        if not background_jobs_service.stats_service:
            raise HTTPException(status_code=503, detail="Statistics service not initialized")

        stats = await background_jobs_service.stats_service.get_latest_statistics(time_window)

        if not stats:
            raise HTTPException(status_code=404, detail="No statistics available")

        return {
            "cipher_suites": [cs.model_dump() for cs in stats.top_cipher_suites[:limit]],
            "timestamp": stats.timestamp.isoformat(),
            "time_window_minutes": time_window,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cipher suite statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cipher suite statistics")


@router.get("/statistics/servers")
async def get_server_statistics(
    time_window: int = Query(default=60, ge=1, le=1440), limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get top servers statistics

    Args:
        time_window: Time window in minutes (default: 60)
        limit: Maximum number of servers to return (default: 10)
    """
    try:
        from ngfw_pqc_detector.services.background_jobs import background_jobs_service

        if not background_jobs_service.stats_service:
            raise HTTPException(status_code=503, detail="Statistics service not initialized")

        stats = await background_jobs_service.stats_service.get_latest_statistics(time_window)

        if not stats:
            raise HTTPException(status_code=404, detail="No statistics available")

        return {
            "servers": [server.model_dump() for server in stats.top_servers[:limit]],
            "timestamp": stats.timestamp.isoformat(),
            "time_window_minutes": time_window,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting server statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve server statistics")


@router.get("/statistics/time-series")
async def get_time_series_statistics(time_window: int = Query(default=60, ge=1, le=1440)):
    """
    Get time series data for trending

    Args:
        time_window: Time window in minutes (default: 60)
    """
    try:
        from ngfw_pqc_detector.services.background_jobs import background_jobs_service

        if not background_jobs_service.stats_service:
            raise HTTPException(status_code=503, detail="Statistics service not initialized")

        stats = await background_jobs_service.stats_service.get_latest_statistics(time_window)

        if not stats:
            raise HTTPException(status_code=404, detail="No statistics available")

        return {
            "time_series": [dp.model_dump() for dp in stats.time_series],
            "timestamp": stats.timestamp.isoformat(),
            "time_window_minutes": time_window,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time series statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve time series statistics")
        raise HTTPException(status_code=500, detail="Failed to retrieve security alerts")


@router.get("/accumulated-stats")
async def get_accumulated_statistics():
    """
    Get real-time accumulated statistics

    Returns accumulated counters for:
    - Total flows (TCP, UDP, TLS, other)
    - PQC status (safe, vulnerable, unknown)
    - Protocol distribution
    - TLS version distribution
    - Cipher suite distribution
    - Alerts by severity
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db
        from ngfw_pqc_detector.services.accumulated_stats_service import AccumulatedStatsService

        # Get the accumulated stats service
        accumulated_stats_service = AccumulatedStatsService(
            stats_collection=mongo_db["accumulated_network_stats"],
            flows_collection=mongo_db["network_flows"],
            tls_sessions_collection=mongo_db["tls_sessions"],
            alerts_collection=mongo_db["alerts"],
        )

        stats = await accumulated_stats_service.get_accumulated_stats()

        if not stats:
            raise HTTPException(status_code=404, detail="No accumulated statistics available")

        return stats.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting accumulated statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve accumulated statistics")


@router.get("/network-flows/recent")
async def get_recent_network_flows(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get recent network flows

    Args:
        limit: Maximum number of flows to return (default: 50, max: 500)
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        flows_collection = mongo_db["network_flows"]
        cursor = flows_collection.find().sort("event_time", -1).limit(limit)
        flows = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for flow in flows:
            flow["id"] = str(flow.pop("_id"))
            flow["event_time"] = flow["event_time"].isoformat()

        return {"count": len(flows), "flows": flows}
    except Exception as e:
        logger.error(f"Error getting network flows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve network flows")


@router.get("/tls-sessions/recent")
async def get_recent_tls_sessions(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get recent TLS sessions

    Args:
        limit: Maximum number of sessions to return (default: 50, max: 500)
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        tls_collection = mongo_db["tls_sessions"]
        cursor = tls_collection.find().sort("event_time", -1).limit(limit)
        sessions = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for session in sessions:
            session["id"] = str(session.pop("_id"))
            session["event_time"] = session["event_time"].isoformat()

        return {"count": len(sessions), "sessions": sessions}
    except Exception as e:
        logger.error(f"Error getting TLS sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve TLS sessions")


@router.get("/alerts/recent")
async def get_recent_alerts(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get recent security alerts

    Args:
        limit: Maximum number of alerts to return (default: 50, max: 500)
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        alerts_collection = mongo_db["alerts"]
        cursor = alerts_collection.find().sort("event_time", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["event_time"] = alert["event_time"].isoformat()

        return {"count": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/alerts/list")
async def list_all_alerts(
    limit: int = Query(default=100, ge=1, le=1000),
    severity: Optional[str] = Query(
        default=None, description="Filter by severity: critical, high, medium, low, info"
    ),
    alert_type: Optional[str] = Query(default=None, description="Filter by alert type"),
    acknowledged: Optional[bool] = Query(
        default=None, description="Filter by acknowledgment status"
    ),
):
    """
    List all security alerts with optional filters

    Args:
        limit: Maximum number of alerts to return (default: 100, max: 1000)
        severity: Filter by severity level
        alert_type: Filter by alert type
        acknowledged: Filter by acknowledgment status

    Returns:
        List of alerts matching the filters
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        alerts_collection = mongo_db["alerts"]

        # Build query filter
        query = {}
        if severity:
            query["severity"] = severity
        if alert_type:
            query["alert_type"] = alert_type
        if acknowledged is not None:
            query["acknowledged"] = acknowledged

        # Query alerts
        cursor = alerts_collection.find(query).sort("timestamp", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string and format timestamps
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["timestamp"] = alert["timestamp"].isoformat()
            if alert.get("acknowledged_at"):
                alert["acknowledged_at"] = alert["acknowledged_at"].isoformat()

        return {
            "count": len(alerts),
            "alerts": alerts,
            "filters": {
                "severity": severity,
                "alert_type": alert_type,
                "acknowledged": acknowledged,
            },
        }
    except Exception as e:
        logger.error(f"Error listing alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list alerts")


@router.get("/alerts/by-severity/{severity}")
async def get_alerts_by_severity(severity: str, limit: int = Query(default=100, ge=1, le=1000)):
    """
    Get alerts by severity level

    Args:
        severity: Severity level (critical, high, medium, low, info)
        limit: Maximum number of alerts to return

    Returns:
        List of alerts with the specified severity
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        alerts_collection = mongo_db["alerts"]
        cursor = alerts_collection.find({"severity": severity}).sort("timestamp", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string and format timestamps
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["timestamp"] = alert["timestamp"].isoformat()
            if alert.get("acknowledged_at"):
                alert["acknowledged_at"] = alert["acknowledged_at"].isoformat()

        return {"severity": severity, "count": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting alerts by severity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts by severity")


@router.get("/alerts/unacknowledged")
async def get_unacknowledged_alerts(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Get unacknowledged alerts

    Args:
        limit: Maximum number of alerts to return

    Returns:
        List of unacknowledged alerts
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        alerts_collection = mongo_db["alerts"]
        cursor = alerts_collection.find({"acknowledged": False}).sort("timestamp", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string and format timestamps
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["timestamp"] = alert["timestamp"].isoformat()

        return {"count": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting unacknowledged alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve unacknowledged alerts")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: Optional[str] = Query(
        default=None, description="User who acknowledged the alert"
    ),
):
    """
    Acknowledge an alert

    Args:
        alert_id: Alert ID
        acknowledged_by: User who acknowledged the alert (optional)

    Returns:
        Success status
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db
        from bson import ObjectId
        from datetime import datetime

        alerts_collection = mongo_db["alerts"]

        result = await alerts_collection.update_one(
            {"_id": ObjectId(alert_id)},
            {
                "$set": {
                    "acknowledged": True,
                    "acknowledged_at": datetime.utcnow(),
                    "acknowledged_by": acknowledged_by,
                }
            },
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")

        return {
            "success": True,
            "alert_id": alert_id,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/alerts/stats")
async def get_alert_statistics():
    """
    Get alert statistics

    Returns:
        Statistics about alerts including counts by severity and type
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db

        alerts_collection = mongo_db["alerts"]

        # Aggregate statistics
        pipeline = [
            {
                "$facet": {
                    "total": [{"$count": "count"}],
                    "by_severity": [
                        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    "by_type": [
                        {"$group": {"_id": "$alert_type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    "unacknowledged": [{"$match": {"acknowledged": False}}, {"$count": "count"}],
                }
            }
        ]

        result = await alerts_collection.aggregate(pipeline).to_list(length=1)

        if result:
            stats = result[0]
            total = stats["total"][0]["count"] if stats["total"] else 0
            unacknowledged = stats["unacknowledged"][0]["count"] if stats["unacknowledged"] else 0

            by_severity = {item["_id"]: item["count"] for item in stats["by_severity"]}
            by_type = {item["_id"]: item["count"] for item in stats["by_type"]}
        else:
            total = 0
            unacknowledged = 0
            by_severity = {}
            by_type = {}

        return {
            "total_alerts": total,
            "unacknowledged_alerts": unacknowledged,
            "acknowledged_alerts": total - unacknowledged,
            "by_severity": by_severity,
            "by_type": by_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve alert statistics")


@router.get("/pqc-status-history")
async def get_pqc_status_history(
    hours: int = Query(
        default=24, ge=1, le=168, description="Number of hours to look back (max 7 days)"
    ),
    interval_minutes: int = Query(
        default=60, ge=5, le=1440, description="Data point interval in minutes"
    ),
):
    """
    Get historical PQC status data for line graph visualization

    Returns time series data showing PQC safe, vulnerable, and unknown counts over time.
    Perfect for creating line graphs showing PQC adoption trends.

    Args:
        hours: Number of hours to look back (default: 24, max: 168/7 days)
        interval_minutes: Interval between data points in minutes (default: 60)

    Returns:
        {
            "timeRange": {
                "start": "2026-02-10T00:00:00Z",
                "end": "2026-02-10T24:00:00Z",
                "hours": 24,
                "intervalMinutes": 60
            },
            "dataPoints": [
                {
                    "timestamp": "2026-02-10T00:00:00Z",
                    "pqcSafe": 150,
                    "pqcVulnerable": 300,
                    "pqcUnknown": 50,
                    "total": 500,
                    "pqcSafePercentage": 30.0,
                    "pqcVulnerablePercentage": 60.0,
                    "pqcUnknownPercentage": 10.0
                },
                ...
            ],
            "summary": {
                "totalDataPoints": 24,
                "avgPqcSafe": 145,
                "avgPqcVulnerable": 285,
                "avgPqcSafePercentage": 29.5,
                "trend": "increasing"
            }
        }
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db
        from datetime import datetime, timedelta

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Calculate number of intervals
        total_minutes = hours * 60
        num_intervals = total_minutes // interval_minutes

        tls_sessions = mongo_db["tls_sessions"]

        # Generate data points
        data_points = []

        for i in range(num_intervals):
            interval_start = start_time + timedelta(minutes=i * interval_minutes)
            interval_end = interval_start + timedelta(minutes=interval_minutes)

            # Aggregate data for this interval
            pipeline = [
                {"$match": {"event_time": {"$gte": interval_start, "$lt": interval_end}}},
                {"$group": {"_id": "$pqc_status", "count": {"$sum": 1}}},
            ]

            results = await tls_sessions.aggregate(pipeline).to_list(length=None)

            # Build data point
            counts = {r["_id"]: r["count"] for r in results}
            safe = counts.get("SAFE", 0)
            vulnerable = counts.get("VULNERABLE", 0)
            unknown = counts.get("UNKNOWN", 0)
            total = safe + vulnerable + unknown

            data_point = {
                "timestamp": interval_start.isoformat() + "Z",
                "pqcSafe": safe,
                "pqcVulnerable": vulnerable,
                "pqcUnknown": unknown,
                "total": total,
                "pqcSafePercentage": round((safe / total * 100) if total > 0 else 0, 2),
                "pqcVulnerablePercentage": round((vulnerable / total * 100) if total > 0 else 0, 2),
                "pqcUnknownPercentage": round((unknown / total * 100) if total > 0 else 0, 2),
            }

            data_points.append(data_point)

        # Calculate summary statistics
        if data_points:
            total_safe = sum(dp["pqcSafe"] for dp in data_points)
            total_vulnerable = sum(dp["pqcVulnerable"] for dp in data_points)
            avg_safe = total_safe // len(data_points) if data_points else 0
            avg_vulnerable = total_vulnerable // len(data_points) if data_points else 0

            # Calculate trend (compare first half vs second half)
            mid_point = len(data_points) // 2
            if mid_point > 0:
                first_half_avg = (
                    sum(dp["pqcSafePercentage"] for dp in data_points[:mid_point]) / mid_point
                )
                second_half_avg = sum(dp["pqcSafePercentage"] for dp in data_points[mid_point:]) / (
                    len(data_points) - mid_point
                )

                if second_half_avg > first_half_avg + 5:
                    trend = "increasing"
                elif second_half_avg < first_half_avg - 5:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            avg_safe_pct = sum(dp["pqcSafePercentage"] for dp in data_points) / len(data_points)
        else:
            avg_safe = 0
            avg_vulnerable = 0
            avg_safe_pct = 0
            trend = "no_data"

        return {
            "timeRange": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z",
                "hours": hours,
                "intervalMinutes": interval_minutes,
            },
            "dataPoints": data_points,
            "summary": {
                "totalDataPoints": len(data_points),
                "avgPqcSafe": avg_safe,
                "avgPqcVulnerable": avg_vulnerable,
                "avgPqcSafePercentage": round(avg_safe_pct, 2),
                "trend": trend,
            },
        }

    except Exception as e:
        logger.error(f"Error getting PQC status history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve PQC status history")


@router.get("/topology/graph")
async def get_network_topology_graph(
    time_window: int = Query(default=60, ge=1, le=1440, description="Time window in minutes"),
    include_inactive: bool = Query(default=False, description="Include inactive nodes/edges"),
):
    """
    Get network topology graph for visualization

    Returns nodes and edges representing the network connections with security status.
    Perfect for creating network topology visualizations showing which machines connect
    to which destinations and whether connections are secure (PQC-safe) or insecure.

    Args:
        time_window: Time window in minutes (default: 60, max: 1440/24h)
        include_inactive: Include nodes/edges not seen in time window

    Returns:
        {
            "timestamp": "2026-02-10T13:55:00Z",
            "timeWindowMinutes": 60,
            "nodes": {
                "192.168.1.87": {
                    "nodeId": "192.168.1.87",
                    "nodeType": "internal",
                    "hostname": null,
                    "firstSeen": "2026-02-10T13:00:00Z",
                    "lastSeen": "2026-02-10T13:55:00Z",
                    "connectionCount": 150,
                    "secureConnections": 45,
                    "insecureConnections": 105,
                    "ports": [52349, 52350, 52351],
                    "protocols": ["TCP", "UDP"]
                },
                "13.126.138.201": {
                    "nodeId": "13.126.138.201",
                    "nodeType": "external",
                    "hostname": "enterprise.example.com",
                    ...
                }
            },
            "edges": {
                "192.168.1.87:52349->13.126.138.201:443": {
                    "edgeId": "192.168.1.87:52349->13.126.138.201:443",
                    "sourceIp": "192.168.1.87",
                    "sourcePort": 52349,
                    "destinationIp": "13.126.138.201",
                    "destinationPort": 443,
                    "protocol": "TCP",
                    "firstSeen": "2026-02-10T13:24:45Z",
                    "lastSeen": "2026-02-10T13:55:00Z",
                    "connectionCount": 25,
                    "security": {
                        "isSecure": false,
                        "cryptoType": "classical",
                        "pqcStatus": "vulnerable",
                        "confidence": 0.6667,
                        "hasEch": true,
                        "posture": "ECH_PROTECTED"
                    },
                    "tlsVersion": "TLS 1.3",
                    "serverName": "enterprise.example.com",
                    "bytesToServer": 15000,
                    "bytesToClient": 45000,
                    "totalBytes": 60000
                }
            },
            "summary": {
                "totalNodes": 25,
                "totalEdges": 150,
                "secureConnections": 45,
                "insecureConnections": 95,
                "unknownConnections": 10
            }
        }
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db
        from ngfw_pqc_detector.services.topology_service import TopologyService

        # Get topology service
        topology_service = TopologyService(
            nodes_collection=mongo_db["network_nodes"],
            edges_collection=mongo_db["network_edges"],
        )

        # Get topology
        topology = await topology_service.get_topology(
            time_window_minutes=time_window, include_inactive=include_inactive
        )

        # Convert to JSON-serializable format
        nodes_dict = {}
        for node_id, node in topology.nodes.items():
            node_dict = node.model_dump()
            node_dict["firstSeen"] = node.first_seen.isoformat() + "Z"
            node_dict["lastSeen"] = node.last_seen.isoformat() + "Z"
            nodes_dict[node_id] = node_dict

        edges_dict = {}
        for edge_id, edge in topology.edges.items():
            edge_dict = edge.model_dump()
            edge_dict["firstSeen"] = edge.first_seen.isoformat() + "Z"
            edge_dict["lastSeen"] = edge.last_seen.isoformat() + "Z"
            edges_dict[edge_id] = edge_dict

        return {
            "timestamp": topology.timestamp.isoformat() + "Z",
            "timeWindowMinutes": time_window,
            "nodes": nodes_dict,
            "edges": edges_dict,
            "summary": {
                "totalNodes": topology.total_nodes,
                "totalEdges": topology.total_edges,
                "secureConnections": topology.secure_connections,
                "insecureConnections": topology.insecure_connections,
                "unknownConnections": topology.unknown_connections,
            },
        }

    except Exception as e:
        logger.error(f"Error getting network topology: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve network topology")


@router.get("/topology/stats")
async def get_topology_statistics(
    time_window: int = Query(default=60, ge=1, le=1440, description="Time window in minutes")
):
    """
    Get network topology statistics

    Returns aggregated statistics about the network topology including top talkers,
    protocol distribution, and security metrics.

    Args:
        time_window: Time window in minutes (default: 60, max: 1440/24h)

    Returns:
        {
            "totalNodes": 25,
            "totalConnections": 150,
            "secureConnections": 45,
            "insecureConnections": 95,
            "unknownConnections": 10,
            "internalNodes": 5,
            "externalNodes": 20,
            "protocolDistribution": {
                "TCP": 140,
                "UDP": 10
            },
            "topSources": [
                {"ip": "192.168.1.87", "connections": 75},
                {"ip": "192.168.1.100", "connections": 50}
            ],
            "topDestinations": [
                {"ip": "13.126.138.201", "connections": 60},
                {"ip": "52.84.123.45", "connections": 45}
            ],
            "pqcSafePercentage": 30.0,
            "classicalPercentage": 63.33,
            "hybridPercentage": 6.67
        }
    """
    try:
        from ngfw_pqc_detector.services.database import mongo_db
        from ngfw_pqc_detector.services.topology_service import TopologyService

        # Get topology service
        topology_service = TopologyService(
            nodes_collection=mongo_db["network_nodes"],
            edges_collection=mongo_db["network_edges"],
        )

        # Get statistics
        stats = await topology_service.get_topology_stats(time_window_minutes=time_window)

        return stats.model_dump()

    except Exception as e:
        logger.error(f"Error getting topology statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve topology statistics")

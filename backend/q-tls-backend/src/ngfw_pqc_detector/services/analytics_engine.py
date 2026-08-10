"""
Suricata Analytics Engine
Provides real-time analytics and metrics for TLS connections using MongoDB
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ngfw_pqc_detector.services import database
from ngfw_pqc_detector.models import CryptoType

logger = logging.getLogger(__name__)


class SuricataAnalytics:
    """Analytics engine for Suricata TLS data"""

    def __init__(self):
        """Initialize analytics engine"""
        self.logger = logger
    
    @property
    def collection(self):
        """Get MongoDB collection (lazy loading)"""
        return database.tls_connections_collection

    async def get_dashboard_summary(self, time_window_minutes: int = 60) -> Dict:
        """
        Get complete dashboard summary with all metrics
        
        Args:
            time_window_minutes: Time window in minutes for metrics
            
        Returns:
            Dictionary with dashboard data
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        # Get all metrics
        total_flows = await self._get_total_flows(cutoff_time)
        tls_connections = await self._get_tls_connections(cutoff_time)
        pqc_safe = await self._get_pqc_safe_connections(cutoff_time)
        vulnerable = await self._get_vulnerable_connections(cutoff_time)
        protocol_dist = await self._get_protocol_distribution(cutoff_time, 10)
        pqc_dist = await self._get_pqc_status_distribution(cutoff_time)
        live_flows = await self._get_live_network_flows(50)
        alerts = await self._get_security_alerts(10)
        top_destinations = await self._get_top_destinations(cutoff_time, 10)
        
        return {
            "metrics": {
                "total_flows": total_flows,
                "tls_connections": tls_connections,
                "pqc_safe": pqc_safe,
                "vulnerable": vulnerable,
                "pqc_percentage": (pqc_safe / tls_connections * 100) if tls_connections > 0 else 0
            },
            "protocol_distribution": protocol_dist,
            "pqc_status_distribution": pqc_dist,
            "live_flows": live_flows,
            "security_alerts": alerts,
            "top_destinations": top_destinations,
            "time_window_minutes": time_window_minutes
        }

    async def get_total_flows(self, time_window_minutes: int = 60) -> int:
        """Get total number of flows in time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return await self._get_total_flows(cutoff_time)

    async def get_tls_connections(self, time_window_minutes: int = 60) -> int:
        """Get total TLS connections in time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return await self._get_tls_connections(cutoff_time)

    async def get_pqc_safe_connections(self, time_window_minutes: int = 60) -> int:
        """Get PQC-safe connections in time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return await self._get_pqc_safe_connections(cutoff_time)

    async def get_vulnerable_connections(self, time_window_minutes: int = 60) -> int:
        """Get vulnerable (classical crypto) connections in time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return await self._get_vulnerable_connections(cutoff_time)

    async def get_protocol_distribution(
        self, time_window_minutes: int = 60, limit: int = 10
    ) -> List[Dict]:
        """Get protocol distribution"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return await self._get_protocol_distribution(cutoff_time, limit)

    async def get_pqc_status_distribution(self, time_window_minutes: int = 60) -> Dict:
        """Get PQC status distribution"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        return await self._get_pqc_status_distribution(cutoff_time)

    async def get_live_network_flows(self, limit: int = 50) -> List[Dict]:
        """Get recent live network flows"""
        return await self._get_live_network_flows(limit)

    async def get_security_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent security alerts"""
        return await self._get_security_alerts(limit)

    # Internal helper methods using MongoDB aggregation
    async def _get_total_flows(self, cutoff_time: datetime) -> int:
        """Internal: Get total flows"""
        count = await self.collection.count_documents({"timestamp": {"$gte": cutoff_time}})
        return count

    async def _get_tls_connections(self, cutoff_time: datetime) -> int:
        """Internal: Get TLS connections"""
        count = await self.collection.count_documents({"timestamp": {"$gte": cutoff_time}})
        return count

    async def _get_pqc_safe_connections(self, cutoff_time: datetime) -> int:
        """Internal: Get PQC-safe connections"""
        count = await self.collection.count_documents({
            "timestamp": {"$gte": cutoff_time},
            "is_pqc": True
        })
        return count

    async def _get_vulnerable_connections(self, cutoff_time: datetime) -> int:
        """Internal: Get vulnerable connections"""
        count = await self.collection.count_documents({
            "timestamp": {"$gte": cutoff_time},
            "crypto_type": CryptoType.CLASSICAL.value
        })
        return count

    async def _get_protocol_distribution(
        self, cutoff_time: datetime, limit: int
    ) -> List[Dict]:
        """Internal: Get protocol distribution"""
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$group": {
                "_id": "$tls_version",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "protocol": "$_id",
                "count": 1
            }}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=limit)
        return result

    async def _get_pqc_status_distribution(self, cutoff_time: datetime) -> Dict:
        """Internal: Get PQC status distribution"""
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$group": {
                "_id": "$crypto_type",
                "count": {"$sum": 1}
            }}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        distribution = {item["_id"]: item["count"] for item in results}
        
        return {
            "classical": distribution.get(CryptoType.CLASSICAL.value, 0),
            "pqc": distribution.get(CryptoType.PQC.value, 0),
            "hybrid": distribution.get(CryptoType.HYBRID.value, 0),
            "unknown": distribution.get(CryptoType.UNKNOWN.value, 0)
        }

    async def _get_live_network_flows(self, limit: int) -> List[Dict]:
        """Internal: Get live network flows"""
        cursor = self.collection.find().sort("timestamp", -1).limit(limit)
        flows = await cursor.to_list(length=limit)
        
        result = []
        for record in flows:
            result.append({
                "id": str(record["_id"]),
                "timestamp": record["timestamp"].isoformat(),
                "source_ip": record["source_ip"],
                "source_port": record["source_port"],
                "destination_ip": record["destination_ip"],
                "destination_port": record["destination_port"],
                "server_name": record.get("server_name"),
                "tls_version": record["tls_version"],
                "crypto_type": record["crypto_type"],
                "is_pqc": record["is_pqc"],
                "is_hybrid": record["is_hybrid"],
                "cipher_suite": record.get("cipher_suite_name")
            })
        
        return result

    async def _get_security_alerts(self, limit: int) -> List[Dict]:
        """Internal: Get security alerts (vulnerable connections)"""
        cursor = (
            self.collection.find({"crypto_type": CryptoType.CLASSICAL.value})
            .sort("timestamp", -1)
            .limit(limit)
        )
        alerts = await cursor.to_list(length=limit)
        
        result = []
        for record in alerts:
            result.append({
                "id": str(record["_id"]),
                "timestamp": record["timestamp"].isoformat(),
                "severity": "medium",
                "type": "vulnerable_crypto",
                "message": f"Classical cryptography detected: {record.get('server_name') or record['destination_ip']}",
                "source_ip": record["source_ip"],
                "destination_ip": record["destination_ip"],
                "server_name": record.get("server_name"),
                "tls_version": record["tls_version"],
                "cipher_suite": record.get("cipher_suite_name")
            })
        
        return result

    async def _get_top_destinations(
        self, cutoff_time: datetime, limit: int
    ) -> List[Dict]:
        """Internal: Get top destination IPs"""
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$group": {
                "_id": {
                    "destination_ip": "$destination_ip",
                    "server_name": "$server_name"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "destination_ip": "$_id.destination_ip",
                "server_name": "$_id.server_name",
                "connection_count": "$count"
            }}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        result = await cursor.to_list(length=limit)
        return result
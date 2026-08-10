"""
Accumulated Statistics Service
Maintains real-time accumulated counters in MongoDB
"""

import logging
import re
from datetime import datetime
from typing import Optional, Dict
from motor.motor_asyncio import AsyncIOMotorCollection

from ngfw_pqc_detector.models.accumulated_stats import (
    AccumulatedNetworkStats,
    NetworkFlowRecord,
    TLSSessionRecord,
    AlertRecord,
)

logger = logging.getLogger(__name__)


class AccumulatedStatsService:
    """
    Service for managing accumulated statistics
    Uses a single document that gets updated with each event
    """

    STATS_DOC_ID = "accumulated_stats_v1"

    def __init__(
        self,
        stats_collection: AsyncIOMotorCollection,
        flows_collection: AsyncIOMotorCollection,
        tls_sessions_collection: AsyncIOMotorCollection,
        alerts_collection: AsyncIOMotorCollection,
    ):
        self.stats_collection = stats_collection
        self.flows_collection = flows_collection
        self.tls_sessions_collection = tls_sessions_collection
        self.alerts_collection = alerts_collection

    async def initialize(self):
        """Initialize the accumulated statistics document"""
        # Check if stats document exists
        existing = await self.stats_collection.find_one({"_id": self.STATS_DOC_ID})

        if not existing:
            # Create initial document
            initial_stats = AccumulatedNetworkStats()
            doc = initial_stats.model_dump()
            doc["_id"] = self.STATS_DOC_ID

            await self.stats_collection.insert_one(doc)
            logger.info("Created initial accumulated statistics document")
        else:
            logger.info("Accumulated statistics document already exists")

        # Create indexes
        await self.flows_collection.create_index([("event_time", -1)])
        await self.flows_collection.create_index([("flow_id", 1)])
        await self.tls_sessions_collection.create_index([("event_time", -1)])
        await self.tls_sessions_collection.create_index([("flow_id", 1)])
        await self.alerts_collection.create_index([("event_time", -1)])

        logger.info("Accumulated statistics service initialized")

    async def update_from_kafka_message(self, message: dict):
        """
        Update accumulated statistics from a Kafka message

        Args:
            message: Raw Kafka message from Suricata
        """
        try:
            event_type = message.get("event_type", "unknown")

            # Extract common fields
            flow_id = message.get("flow_id", 0)

            # Parse timestamp with proper timezone format handling
            timestamp_str = message.get("timestamp", datetime.utcnow().isoformat())
            # Replace 'Z' with '+00:00' for UTC
            timestamp_str = timestamp_str.replace("Z", "+00:00")
            # Fix timezone format: +0530 -> +05:30
            timestamp_str = re.sub(r"([+-])(\d{2})(\d{2})$", r"\1\2:\3", timestamp_str)

            event_time = datetime.fromisoformat(timestamp_str)

            # Update based on event type
            if event_type == "flow":
                await self._update_from_flow(message, flow_id, event_time)
            elif event_type == "tls":
                await self._update_from_tls(message, flow_id, event_time)
            elif event_type == "alert":
                await self._update_from_alert(message, flow_id, event_time)

        except Exception as e:
            logger.error(f"Error updating accumulated stats: {e}", exc_info=True)

    async def _update_from_flow(self, message: dict, flow_id: int, event_time: datetime):
        """Update statistics from a flow event"""
        # Extract flow data
        proto = message.get("proto", "unknown").upper()
        app_proto = message.get("app_proto", "unknown")
        flow_state = message.get("flow", {}).get("state", "unknown")

        bytes_to_server = message.get("flow", {}).get("bytes_toserver", 0)
        bytes_to_client = message.get("flow", {}).get("bytes_toclient", 0)

        # Store flow record
        flow_record = NetworkFlowRecord(
            flow_id=flow_id,
            event_time=event_time,
            src_ip=message.get("src_ip", "unknown"),
            src_port=message.get("src_port"),
            dest_ip=message.get("dest_ip", "unknown"),
            dest_port=message.get("dest_port"),
            protocol=proto,
            app_proto=app_proto,
            bytes_to_server=bytes_to_server,
            bytes_to_client=bytes_to_client,
            flow_state=flow_state,
            alerted=message.get("alert", {}).get("action") is not None,
        )

        await self.flows_collection.insert_one(flow_record.model_dump())

        # Update accumulated stats
        update_ops = {
            "$inc": {
                "total_flows": 1,
                "total_bytes_to_server": bytes_to_server,
                "total_bytes_to_client": bytes_to_client,
                "total_bytes": bytes_to_server + bytes_to_client,
                f"protocol_distribution.{app_proto}": 1,
                f"flow_state_distribution.{flow_state}": 1,
            },
            "$set": {"last_updated": datetime.utcnow()},
        }

        # Increment protocol-specific counters
        if proto == "TCP":
            update_ops["$inc"]["total_tcp_flows"] = 1
        elif proto == "UDP":
            update_ops["$inc"]["total_udp_flows"] = 1
        else:
            update_ops["$inc"]["total_other_flows"] = 1

        # Increment TLS counter if applicable
        if app_proto.lower() in ["tls", "ssl", "https"]:
            update_ops["$inc"]["total_tls_flows"] = 1

        await self.stats_collection.update_one({"_id": self.STATS_DOC_ID}, update_ops)

        logger.debug(f"Updated stats from flow event: {flow_id}")

    async def _update_from_tls(self, message: dict, flow_id: int, event_time: datetime):
        """Update statistics from a TLS event"""
        tls_data = message.get("tls", {})

        # Get byte counts for heuristic detection
        flow_data = message.get("flow", {})
        bytes_to_server = flow_data.get("bytes_toserver", 0)
        bytes_to_client = flow_data.get("bytes_toclient", 0)
        total_bytes = bytes_to_server + bytes_to_client

        # Determine PQC status
        pqc_data = tls_data.get("pqc", {})
        is_pqc = pqc_data.get("is_pqc", False)
        has_ech = pqc_data.get("has_ech", False)
        pqc_posture = pqc_data.get("posture", "UNKNOWN").upper()

        # Primary: Use metadata if available
        if is_pqc or has_ech or pqc_posture in ["PQC", "PQC_SAFE", "HYBRID"]:
            pqc_status = "SAFE"
            pqc_reason = f"Post-quantum cryptography detected (posture: {pqc_posture})"
        elif pqc_posture in ["CLASSICAL", "VULNERABLE"]:
            pqc_status = "VULNERABLE"
            pqc_reason = f"Classical cryptography only (posture: {pqc_posture})"
        # Fallback: Use byte-based heuristic if metadata unavailable
        elif total_bytes > 0:
            if total_bytes > 8000:
                pqc_status = "SAFE"
                pqc_reason = f"Byte heuristic: {total_bytes} bytes suggests PQC (ML-KEM-768)"
            elif total_bytes >= 5000:
                pqc_status = "VULNERABLE"
                pqc_reason = f"Byte heuristic: {total_bytes} bytes suggests classical TLS 1.3"
            else:
                pqc_status = "VULNERABLE"
                pqc_reason = f"Byte heuristic: {total_bytes} bytes suggests legacy TLS"
        else:
            pqc_status = "UNKNOWN"
            pqc_reason = "Unable to determine PQC status"

        # Extract TLS details
        tls_version = tls_data.get("version", "unknown")
        cipher_suite = tls_data.get("cipher_suite_name", "unknown")

        # Try to extract key exchange (may not always be available)
        key_exchange = "unknown"
        if pqc_data.get("key_share_groups_names"):
            key_exchange = ", ".join(pqc_data["key_share_groups_names"][:2])

        # Store TLS session record
        tls_record = TLSSessionRecord(
            flow_id=flow_id,
            event_time=event_time,
            tls_version=tls_version,
            key_exchange=key_exchange,
            cipher_suite=cipher_suite,
            pqc_status=pqc_status,
            pqc_reason=pqc_reason,
        )

        await self.tls_sessions_collection.insert_one(tls_record.model_dump())

        # Update accumulated stats
        # Use safe keys (replace spaces and special characters)
        safe_tls_version = tls_version.replace(" ", "_").replace(".", "_")
        safe_cipher_suite = cipher_suite.replace(" ", "_").replace("-", "_")

        update_ops = {
            "$inc": {
                f"tls_version_distribution.{safe_tls_version}": 1,
                f"cipher_suite_distribution.{safe_cipher_suite}": 1,
                f"posture_distribution.{pqc_posture}": 1,
            },
            "$set": {"last_updated": datetime.utcnow()},
        }

        # Increment PQC status counters
        if pqc_status == "SAFE":
            update_ops["$inc"]["total_pqc_safe"] = 1
        elif pqc_status == "VULNERABLE":
            update_ops["$inc"]["total_pqc_vulnerable"] = 1
        else:
            update_ops["$inc"]["total_pqc_unknown"] = 1

        # Update key exchange distribution
        if key_exchange != "unknown":
            safe_key_exchange = key_exchange.replace(" ", "_").replace(",", "_").replace("-", "_")
            update_ops["$inc"][f"key_exchange_distribution.{safe_key_exchange}"] = 1

        await self.stats_collection.update_one({"_id": self.STATS_DOC_ID}, update_ops)

        logger.debug(f"Updated stats from TLS event: {flow_id}, PQC status: {pqc_status}")

    async def _update_from_alert(self, message: dict, flow_id: int, event_time: datetime):
        """Update statistics from an alert event"""
        alert_data = message.get("alert", {})

        alert_type = alert_data.get("category", "unknown")
        severity_num = alert_data.get("severity", 3)

        # Map severity number to text
        severity_map = {1: "critical", 2: "high", 3: "medium", 4: "low"}
        severity = severity_map.get(severity_num, "unknown")

        # Store alert record
        alert_record = AlertRecord(
            event_time=event_time,
            flow_id=flow_id,
            alert_type=alert_type,
            severity=severity,
            message=alert_data.get("signature", "Unknown alert"),
            acknowledged=False,
        )

        await self.alerts_collection.insert_one(alert_record.model_dump())

        # Update accumulated stats
        update_ops = {
            "$inc": {
                "total_alerts": 1,
            },
            "$set": {"last_updated": datetime.utcnow()},
        }

        # Increment severity-specific counter
        if severity == "critical":
            update_ops["$inc"]["total_critical_alerts"] = 1
        elif severity == "high":
            update_ops["$inc"]["total_high_alerts"] = 1
        elif severity == "medium":
            update_ops["$inc"]["total_medium_alerts"] = 1
        elif severity == "low":
            update_ops["$inc"]["total_low_alerts"] = 1

        await self.stats_collection.update_one({"_id": self.STATS_DOC_ID}, update_ops)

        logger.debug(f"Updated stats from alert event: {alert_type}, severity: {severity}")

    async def get_accumulated_stats(self) -> Optional[AccumulatedNetworkStats]:
        """Get current accumulated statistics"""
        doc = await self.stats_collection.find_one({"_id": self.STATS_DOC_ID})

        if doc:
            doc.pop("_id", None)
            return AccumulatedNetworkStats(**doc)

        return None

    async def reset_statistics(self):
        """Reset all accumulated statistics (use with caution)"""
        initial_stats = AccumulatedNetworkStats()
        doc = initial_stats.model_dump()
        doc["_id"] = self.STATS_DOC_ID

        await self.stats_collection.replace_one({"_id": self.STATS_DOC_ID}, doc, upsert=True)

        logger.warning("Accumulated statistics have been reset")

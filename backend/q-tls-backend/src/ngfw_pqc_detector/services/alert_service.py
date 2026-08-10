"""
Alert Service for managing security alerts
"""

import logging
from datetime import datetime
from typing import Optional, List, Callable
from motor.motor_asyncio import AsyncIOMotorCollection

from ngfw_pqc_detector.models.alert import Alert, AlertSeverity, AlertType

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing security alerts"""

    def __init__(
        self,
        alerts_collection: AsyncIOMotorCollection,
        websocket_broadcast_callback: Optional[Callable] = None,
    ):
        self.alerts_collection = alerts_collection
        self.websocket_broadcast_callback = websocket_broadcast_callback

    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        source_ip: str,
        source_port: int,
        destination_ip: str,
        destination_port: int,
        server_name: Optional[str] = None,
        tls_version: Optional[str] = None,
        cipher_suite: Optional[str] = None,
        crypto_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Create and store a new alert

        Args:
            alert_type: Type of alert
            severity: Severity level
            title: Alert title
            description: Alert description
            source_ip: Source IP address
            source_port: Source port
            destination_ip: Destination IP address
            destination_port: Destination port
            server_name: Server name (optional)
            tls_version: TLS version (optional)
            cipher_suite: Cipher suite (optional)
            crypto_type: Crypto type (optional)
            metadata: Additional metadata (optional)

        Returns:
            Alert ID
        """
        alert = Alert(
            timestamp=datetime.utcnow(),
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            source_ip=source_ip,
            source_port=source_port,
            destination_ip=destination_ip,
            destination_port=destination_port,
            server_name=server_name,
            tls_version=tls_version,
            cipher_suite=cipher_suite,
            crypto_type=crypto_type,
            metadata=metadata or {},
        )

        # Store in database
        document = alert.model_dump(exclude={"id"})
        result = await self.alerts_collection.insert_one(document)
        alert_id = str(result.inserted_id)
        alert.id = alert_id

        logger.info(
            f"🚨 ALERT CREATED: {alert_type.value} | {severity.value.upper()} | "
            f"{source_ip}:{source_port} → {destination_ip}:{destination_port} | {title}"
        )

        # Broadcast to WebSocket clients
        if self.websocket_broadcast_callback:
            try:
                await self.websocket_broadcast_callback(alert.model_dump())
            except Exception as e:
                logger.error(f"Error broadcasting alert to WebSocket: {e}")

        return alert_id

    async def check_tls_version_alert(
        self,
        tls_version: str,
        source_ip: str,
        source_port: int,
        destination_ip: str,
        destination_port: int,
        server_name: Optional[str] = None,
        cipher_suite: Optional[str] = None,
        crypto_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Check if TLS version is insecure and create alert if needed

        Args:
            tls_version: TLS version string
            source_ip: Source IP address
            source_port: Source port
            destination_ip: Destination IP address
            destination_port: Destination port
            server_name: Server name (optional)
            cipher_suite: Cipher suite (optional)
            crypto_type: Crypto type (optional)

        Returns:
            Alert ID if alert was created, None otherwise
        """
        # Check if TLS version is less than 1.3
        insecure_versions = ["TLS 1.0", "TLS 1.1", "TLS 1.2", "SSL 3.0", "SSL 2.0"]

        if tls_version in insecure_versions:
            # Determine severity based on version
            if tls_version in ["SSL 2.0", "SSL 3.0", "TLS 1.0"]:
                severity = AlertSeverity.CRITICAL
            elif tls_version == "TLS 1.1":
                severity = AlertSeverity.HIGH
            else:  # TLS 1.2
                severity = AlertSeverity.MEDIUM

            title = f"Insecure TLS Version Detected: {tls_version}"
            description = (
                f"Connection using {tls_version} detected from {source_ip}:{source_port} "
                f"to {destination_ip}:{destination_port}"
            )

            if server_name:
                description += f" (Server: {server_name})"

            description += ". TLS 1.3 or higher is strongly recommended for security."

            metadata = {
                "tls_version": tls_version,
                "cipher_suite": cipher_suite,
                "crypto_type": crypto_type,
                "server_name": server_name,
            }

            return await self.create_alert(
                alert_type=AlertType.INSECURE_TLS_VERSION,
                severity=severity,
                title=title,
                description=description,
                source_ip=source_ip,
                source_port=source_port,
                destination_ip=destination_ip,
                destination_port=destination_port,
                server_name=server_name,
                tls_version=tls_version,
                cipher_suite=cipher_suite,
                crypto_type=crypto_type,
                metadata=metadata,
            )

        return None

    async def check_vulnerable_crypto_alert(
        self,
        crypto_type: str,
        pqc_status: str,
        source_ip: str,
        source_port: int,
        destination_ip: str,
        destination_port: int,
        tls_version: Optional[str] = None,
        server_name: Optional[str] = None,
        cipher_suite: Optional[str] = None,
    ) -> Optional[str]:
        """
        Check if connection uses vulnerable (non-PQC) cryptography and create alert

        Args:
            crypto_type: Crypto type (classical/post-quantum/hybrid/unknown)
            pqc_status: PQC status (safe/vulnerable/unknown)
            source_ip: Source IP address
            source_port: Source port
            destination_ip: Destination IP address
            destination_port: Destination port
            tls_version: TLS version (optional)
            server_name: Server name (optional)
            cipher_suite: Cipher suite (optional)

        Returns:
            Alert ID if alert was created, None otherwise
        """
        # Check if connection is vulnerable (classical crypto, not PQC-safe)
        if pqc_status == "vulnerable" and crypto_type == "classical":
            severity = AlertSeverity.HIGH
            title = "Vulnerable Connection: No Post-Quantum Cryptography"
            description = (
                f"Connection from {source_ip}:{source_port} to {destination_ip}:{destination_port} "
                f"uses classical cryptography without post-quantum protection"
            )

            if server_name:
                description += f" (Server: {server_name})"

            if tls_version:
                description += f". TLS Version: {tls_version}"

            description += ". This connection is vulnerable to future quantum computer attacks. Consider upgrading to PQC-enabled protocols."

            metadata = {
                "crypto_type": crypto_type,
                "pqc_status": pqc_status,
                "tls_version": tls_version,
                "cipher_suite": cipher_suite,
                "server_name": server_name,
            }

            return await self.create_alert(
                alert_type=AlertType.NO_PQC,
                severity=severity,
                title=title,
                description=description,
                source_ip=source_ip,
                source_port=source_port,
                destination_ip=destination_ip,
                destination_port=destination_port,
                server_name=server_name,
                tls_version=tls_version,
                cipher_suite=cipher_suite,
                crypto_type=crypto_type,
                metadata=metadata,
            )

        return None

    async def get_recent_alerts(self, limit: int = 100) -> List[dict]:
        """
        Get recent alerts

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alerts
        """
        cursor = self.alerts_collection.find().sort("timestamp", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["timestamp"] = alert["timestamp"].isoformat()
            if alert.get("acknowledged_at"):
                alert["acknowledged_at"] = alert["acknowledged_at"].isoformat()

        return alerts

    async def get_alerts_by_severity(self, severity: AlertSeverity, limit: int = 100) -> List[dict]:
        """
        Get alerts by severity level

        Args:
            severity: Alert severity level
            limit: Maximum number of alerts to return

        Returns:
            List of alerts
        """
        cursor = (
            self.alerts_collection.find({"severity": severity.value})
            .sort("timestamp", -1)
            .limit(limit)
        )
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["timestamp"] = alert["timestamp"].isoformat()
            if alert.get("acknowledged_at"):
                alert["acknowledged_at"] = alert["acknowledged_at"].isoformat()

        return alerts

    async def get_unacknowledged_alerts(self, limit: int = 100) -> List[dict]:
        """
        Get unacknowledged alerts

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of unacknowledged alerts
        """
        cursor = (
            self.alerts_collection.find({"acknowledged": False}).sort("timestamp", -1).limit(limit)
        )
        alerts = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for alert in alerts:
            alert["id"] = str(alert.pop("_id"))
            alert["timestamp"] = alert["timestamp"].isoformat()

        return alerts

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: Optional[str] = None) -> bool:
        """
        Acknowledge an alert

        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged the alert

        Returns:
            True if successful, False otherwise
        """
        from bson import ObjectId

        try:
            result = await self.alerts_collection.update_one(
                {"_id": ObjectId(alert_id)},
                {
                    "$set": {
                        "acknowledged": True,
                        "acknowledged_at": datetime.utcnow(),
                        "acknowledged_by": acknowledged_by,
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False

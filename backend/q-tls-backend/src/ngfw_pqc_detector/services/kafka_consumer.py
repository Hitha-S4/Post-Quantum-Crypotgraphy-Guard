"""
Kafka Consumer Service for TLS Log Processing
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Callable

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ngfw_pqc_detector.core.config import settings
from ngfw_pqc_detector.services.pqc_detector import PQCDetector
from ngfw_pqc_detector.services.database import DatabaseService

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """
    Consumes TLS logs from Kafka and processes them for PQC detection
    """

    def __init__(
        self,
        websocket_broadcast_callback: Optional[Callable] = None,
        accumulated_stats_service=None,
        topology_service=None,
        alert_service=None,
    ):
        self.consumer: Optional[KafkaConsumer] = None
        self.pqc_detector = PQCDetector()
        self.db_service = DatabaseService()
        self.running = False
        self.websocket_broadcast_callback = websocket_broadcast_callback
        self.accumulated_stats_service = accumulated_stats_service
        self.topology_service = topology_service
        self.alert_service = alert_service
        self.message_count = 0
        self.pqc_count = 0
        self.classical_count = 0
        self.hybrid_count = 0

    def _create_consumer(self) -> KafkaConsumer:
        """Create and configure Kafka consumer"""
        def deserialize_message(m):
            """Deserialize Kafka message and unwrap Filebeat wrapper if present"""
            data = json.loads(m.decode("utf-8"))
            
            # Check if this is a Filebeat-wrapped message
            if "message" in data and isinstance(data["message"], str):
                try:
                    # Parse the nested JSON string
                    suricata_event = json.loads(data["message"])
                    logger.debug(f"Unwrapped Filebeat message: event_type={suricata_event.get('event_type')}")
                    return suricata_event
                except json.JSONDecodeError:
                    logger.warning("Failed to parse nested message JSON, using outer message")
                    return data
            
            # Return as-is if not wrapped
            return data
        
        return KafkaConsumer(
            settings.KAFKA_TOPIC_TLS_LOGS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=True,
            value_deserializer=deserialize_message,
        )

    async def start(self):
        """Start consuming messages from Kafka"""
        logger.info("=" * 80)
        logger.info("Starting Kafka consumer...")
        logger.info(f"Kafka Bootstrap Servers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"Kafka Topic: {settings.KAFKA_TOPIC_TLS_LOGS}")
        logger.info(f"Consumer Group: {settings.KAFKA_CONSUMER_GROUP}")
        logger.info(f"Auto Offset Reset: {settings.KAFKA_AUTO_OFFSET_RESET}")
        logger.info("=" * 80)
        self.running = True

        try:
            self.consumer = self._create_consumer()
            logger.info(
                f"✓ Successfully connected to Kafka broker: {settings.KAFKA_BOOTSTRAP_SERVERS}"
            )
            logger.info(f"✓ Subscribed to topic: '{settings.KAFKA_TOPIC_TLS_LOGS}'")
            logger.info(f"✓ Consumer group: '{settings.KAFKA_CONSUMER_GROUP}'")
            logger.info("Waiting for messages...")

            # Process messages in a loop
            while self.running:
                # Poll for messages in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                messages = await loop.run_in_executor(
                    None,
                    lambda: self.consumer.poll(timeout_ms=1000)
                )

                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            await self._process_message(record.value)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)

                # Allow other tasks to run
                await asyncio.sleep(0.01)

        except KafkaError as e:
            logger.error(f"Kafka error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error in Kafka consumer: {e}", exc_info=True)
        finally:
            if self.consumer:
                self.consumer.close()
                logger.info("Kafka consumer closed")

    async def _process_message(self, message: dict):
        """
        Process a single TLS log message

        Args:
            message: TLS log data from Suricata/Kafka
        """
        try:
            # Increment message counter
            self.message_count += 1

            # Log incoming Kafka message
            timestamp = message.get("timestamp", "N/A")
            event_type = message.get("event_type", "unknown")
            src_ip = message.get("src_ip", "N/A")
            src_port = message.get("src_port", "N/A")
            dest_ip = message.get("dest_ip", "N/A")
            dest_port = message.get("dest_port", "N/A")

            # Filter out non-network events (stats, engine events, etc.)
            # Only process actual network flow events
            excluded_event_types = ["stats", "engine"]
            if event_type in excluded_event_types:
                logger.debug(f"⏭️  Skipping {event_type} event (not a network flow)")
                return

            logger.info("=" * 80)
            logger.info(f"📨 INCOMING KAFKA MESSAGE #{self.message_count}")
            logger.info(f"   Timestamp: {timestamp}")
            logger.info(f"   Event Type: {event_type}")
            logger.info(f"   Connection: {src_ip}:{src_port} → {dest_ip}:{dest_port}")

            # Update accumulated statistics
            if self.accumulated_stats_service:
                try:
                    await self.accumulated_stats_service.update_from_kafka_message(message)
                    logger.debug("   ✓ Updated accumulated statistics")
                except Exception as e:
                    logger.error(f"   ✗ Error updating accumulated stats: {e}")

            # Extract TLS information from Suricata log format
            tls_data = message.get("tls", {})
            app_proto = message.get("app_proto", "unknown").lower()

            # Get byte counts early for heuristic detection
            flow_data = message.get("flow", {})
            bytes_to_server = flow_data.get("bytes_toserver", 0)
            bytes_to_client = flow_data.get("bytes_toclient", 0)
            total_bytes = bytes_to_server + bytes_to_client

            # Handle TLS connections without handshake data (flow events)
            if not tls_data and app_proto in ["tls", "ssl", "https"]:
                logger.info(
                    f"   ⚠️  TLS flow event (no handshake data) - using byte-based heuristic"
                )
                logger.info(
                    f"   Bytes: {bytes_to_server} → server, {bytes_to_client} ← client (total: {total_bytes})"
                )

                # Use byte-based heuristic detection for TLS without handshake data
                if total_bytes > 0:
                    crypto_type, confidence = self.pqc_detector._detect_by_bytes(total_bytes)
                    is_pqc_safe = crypto_type in ["post-quantum", "hybrid"]
                    pqc_status = "safe" if is_pqc_safe else "vulnerable"

                    pqc_indicator = "🔐" if is_pqc_safe else "🔓"
                    logger.info(
                        f"   {pqc_indicator} Crypto Type (heuristic): {crypto_type.value.upper()}"
                    )
                    logger.info(f"   Confidence: {confidence:.2%}")
                    logger.info(f"   PQC Status: {pqc_status.upper()}")
                    logger.info(f"   Detection Method: byte-based heuristic (no handshake data)")
                else:
                    crypto_type = "unknown"
                    pqc_status = "unknown"
                    confidence = 0.0
                    logger.info(f"   ⚠️  No byte data available for heuristic detection")

                # Create enriched message with heuristic results
                enriched_message = self._create_enriched_message(
                    message=message,
                    crypto_type=crypto_type if isinstance(crypto_type, str) else crypto_type.value,
                    pqc_status=pqc_status,
                    confidence=confidence,
                    bytes_to_server=bytes_to_server,
                    bytes_to_client=bytes_to_client,
                    total_bytes=total_bytes,
                    algorithms=None,
                    tls_info=None,
                )

                # Broadcast to WebSocket clients
                if self.websocket_broadcast_callback:
                    try:
                        await self.websocket_broadcast_callback(enriched_message)
                        logger.debug("   ✓ Broadcasted flow event to WebSocket clients")
                    except Exception as e:
                        logger.error(f"   ✗ Error broadcasting to WebSocket: {e}")

                # Store flow event in MongoDB with heuristic detection
                try:
                    await self._store_flow_event(
                        message=message,
                        crypto_type=crypto_type if isinstance(crypto_type, str) else crypto_type.value,
                        pqc_status=pqc_status,
                        confidence=confidence,
                        bytes_to_server=bytes_to_server,
                        bytes_to_client=bytes_to_client,
                        total_bytes=total_bytes,
                    )
                    logger.info("   ✓ Stored flow event in MongoDB")
                except Exception as e:
                    logger.error(f"   ✗ Error storing flow event: {e}")

                # Update network topology for flow events too
                if self.topology_service:
                    try:
                        await self.topology_service.update_topology_from_connection(
                            source_ip=message.get("src_ip", "unknown"),
                            source_port=message.get("src_port", 0),
                            dest_ip=message.get("dest_ip", "unknown"),
                            dest_port=message.get("dest_port", 0),
                            protocol=message.get("proto", "TCP"),
                            crypto_type=(
                                crypto_type if isinstance(crypto_type, str) else crypto_type.value
                            ),
                            pqc_status=pqc_status,
                            confidence=confidence,
                            tls_version=None,
                            server_name=None,
                            cipher_suite=None,
                            bytes_to_server=bytes_to_server,
                            bytes_to_client=bytes_to_client,
                            has_ech=False,
                            posture="unknown",
                        )
                        logger.debug("   ✓ Updated network topology for flow event")
                    except Exception as e:
                        logger.error(f"   ✗ Error updating topology: {e}")

                logger.info("=" * 80)
                return

            # Handle non-TLS protocols (DNS, HTTP, UDP, etc.)
            # BUT: if tls_data exists, process it even if app_proto is "unknown"
            if not tls_data:
                logger.info(
                    f"   ⚠️  Non-TLS protocol ({app_proto}) - creating unknown status message"
                )

                # Extract TLS info directly from message if available
                tls_info = self._extract_tls_info_from_message(message)

                # Extract algorithms from TLS info if available
                algorithms = None
                if tls_info and any(
                    k in tls_info
                    for k in ["supported_groups", "key_share_groups", "signature_algorithms"]
                ):
                    algorithms = {
                        "supported_groups": tls_info.get("supported_groups", []),
                        "key_share_groups": tls_info.get("key_share_groups", []),
                        "signature_algorithms": tls_info.get("signature_algorithms", []),
                        "cipher_suites": [],
                    }

                # Create enriched message with unknown status
                enriched_message = self._create_enriched_message(
                    message=message,
                    crypto_type="unknown",
                    pqc_status="unknown",
                    confidence=0.0,
                    bytes_to_server=bytes_to_server,
                    bytes_to_client=bytes_to_client,
                    total_bytes=total_bytes,
                    algorithms=algorithms,
                    tls_info=tls_info,
                )

                # Broadcast to WebSocket clients
                if self.websocket_broadcast_callback:
                    try:
                        await self.websocket_broadcast_callback(enriched_message)
                        logger.debug("   ✓ Broadcasted non-TLS message to WebSocket clients")
                    except Exception as e:
                        logger.error(f"   ✗ Error broadcasting to WebSocket: {e}")

                # Store non-TLS event in MongoDB
                try:
                    await self._store_flow_event(
                        message=message,
                        crypto_type="unknown",
                        pqc_status="unknown",
                        confidence=0.0,
                        bytes_to_server=bytes_to_server,
                        bytes_to_client=bytes_to_client,
                        total_bytes=total_bytes,
                    )
                    logger.info("   ✓ Stored non-TLS event in MongoDB")
                except Exception as e:
                    logger.error(f"   ✗ Error storing non-TLS event: {e}")

                # Update network topology for non-TLS protocols too
                if self.topology_service:
                    try:
                        await self.topology_service.update_topology_from_connection(
                            source_ip=message.get("src_ip", "unknown"),
                            source_port=message.get("src_port", 0),
                            dest_ip=message.get("dest_ip", "unknown"),
                            dest_port=message.get("dest_port", 0),
                            protocol=message.get("proto", "TCP"),
                            crypto_type="unknown",
                            pqc_status="unknown",
                            confidence=0.0,
                            tls_version=None,
                            server_name=None,
                            cipher_suite=None,
                            bytes_to_server=bytes_to_server,
                            bytes_to_client=bytes_to_client,
                            has_ech=False,
                            posture="unknown",
                        )
                        logger.debug("   ✓ Updated network topology for non-TLS protocol")
                    except Exception as e:
                        logger.error(f"   ✗ Error updating topology: {e}")

                logger.info("=" * 80)
                return

            # Log TLS details
            tls_version = tls_data.get("version", "unknown")
            sni = tls_data.get("sni", "none")
            cipher_suite = tls_data.get("cipher_suite_name", "unknown")

            logger.info(f"   TLS Version: {tls_version}")
            logger.info(f"   SNI: {sni}")
            logger.info(f"   Cipher Suite: {cipher_suite}")

            # Extract Suricata's PQC posture and ECH status
            pqc_data = tls_data.get("pqc", {})
            suricata_posture = pqc_data.get("posture", "unknown")
            has_ech = pqc_data.get("has_ech", False)
            is_pqc_from_suricata = pqc_data.get("is_pqc", False)

            # Parse ClientHello data
            client_hello_data = self._parse_client_hello(tls_data)

            if not client_hello_data:
                logger.info("   ⚠️  No ClientHello data found - skipping")
                logger.info("=" * 80)
                return

            # Log byte information (already extracted earlier)
            if total_bytes > 0:
                logger.info(
                    f"   Bytes: {bytes_to_server} → server, {bytes_to_client} ← client (total: {total_bytes})"
                )

            # Detect PQC usage (with byte-based heuristic)
            crypto_type, confidence = self.pqc_detector.detect_crypto_type(
                client_hello_data, total_bytes
            )

            # Classify exchange groups with Suricata's PQC flag
            exchange_groups_classification = self.pqc_detector.classify_exchange_groups(
                client_hello_data.supported_groups,
                client_hello_data.key_share_groups,
                is_pqc_from_suricata,
            )

            # Determine PQC status - consider Suricata's is_pqc flag for unknown algorithms
            from ngfw_pqc_detector.models import CryptoType

            is_pqc_safe = crypto_type in [CryptoType.PQC, CryptoType.HYBRID]

            # If we have unknown algorithms but Suricata detected PQC, trust Suricata
            if (
                crypto_type == CryptoType.UNKNOWN
                and is_pqc_from_suricata
                and suricata_posture == "UNKNOWN_PQC"
            ):
                is_pqc_safe = True
                crypto_type = CryptoType.PQC
                confidence = (
                    0.7  # Medium confidence since algorithm is unknown but Suricata detected PQC
                )
                logger.info(
                    "   ℹ️  Unknown algorithm detected as PQC by Suricata - treating as PQC-safe"
                )

            pqc_status = "safe" if is_pqc_safe else "vulnerable"

            # Get algorithm details
            algorithm_details = self.pqc_detector.get_algorithm_details(client_hello_data)

            # Log detection results
            pqc_indicator = "🔐" if is_pqc_safe else "🔓"
            logger.info(f"   {pqc_indicator} Crypto Type: {crypto_type.value.upper()}")
            logger.info(f"   Confidence: {confidence:.2%}")
            logger.info(f"   PQC Status: {pqc_status.upper()}")

            # Log exchange groups classification
            if exchange_groups_classification["has_pqc"]:
                logger.info(f"   PQC Groups: {exchange_groups_classification['pqc_groups']}")
                logger.info(f"   Hybrid Groups: {exchange_groups_classification['hybrid_groups']}")

            # Create enriched message for WebSocket broadcast
            enriched_message = self._create_enriched_message(
                message=message,
                crypto_type=crypto_type.value,
                pqc_status=pqc_status,
                confidence=confidence,
                bytes_to_server=bytes_to_server,
                bytes_to_client=bytes_to_client,
                total_bytes=total_bytes,
                exchange_groups=exchange_groups_classification,
                algorithms=algorithm_details,
                posture=suricata_posture,
                has_ech=has_ech,
            )

            # Broadcast enriched message to WebSocket clients
            if self.websocket_broadcast_callback:
                try:
                    await self.websocket_broadcast_callback(enriched_message)
                    logger.debug("   ✓ Broadcasted enriched message to WebSocket clients")
                except Exception as e:
                    logger.error(f"   ✗ Error broadcasting to WebSocket: {e}")

            # Update counters
            if crypto_type == CryptoType.PQC:
                self.pqc_count += 1
            elif crypto_type == CryptoType.HYBRID:
                self.hybrid_count += 1
            else:
                self.classical_count += 1

            # Log supported groups if available
            if tls_data.get("supported_groups"):
                groups = tls_data.get("supported_groups", [])
                logger.info(f"   Supported Groups: {groups}")

            # Log key share groups if available
            if tls_data.get("key_share"):
                key_shares = tls_data.get("key_share", [])
                logger.info(f"   Key Share Groups: {key_shares}")

            # Store in database (only if we have client_hello data)
            if client_hello_data:
                # crypto_type is already a CryptoType enum
                await self.db_service.store_tls_connection(
                    message=message,
                    client_hello=client_hello_data,
                    crypto_type=crypto_type,
                    confidence=confidence,
                    bytes_to_server=bytes_to_server,
                    bytes_to_client=bytes_to_client,
                    total_bytes=total_bytes,
                )

            logger.info("   ✓ Stored in MongoDB")

            # Check for TLS version alerts
            if self.alert_service and tls_version:
                try:
                    alert_id = await self.alert_service.check_tls_version_alert(
                        tls_version=tls_version,
                        source_ip=message.get("src_ip", "unknown"),
                        source_port=message.get("src_port", 0),
                        destination_ip=message.get("dest_ip", "unknown"),
                        destination_port=message.get("dest_port", 0),
                        server_name=sni,
                        cipher_suite=cipher_suite,
                        crypto_type=crypto_type.value,
                    )
                    if alert_id:
                        logger.info(f"   🚨 TLS version alert created: {alert_id}")
                except Exception as e:
                    logger.error(f"   ✗ Error creating TLS version alert: {e}")

            # Check for vulnerable crypto alerts (no PQC)
            if self.alert_service:
                try:
                    alert_id = await self.alert_service.check_vulnerable_crypto_alert(
                        crypto_type=crypto_type.value,
                        pqc_status=pqc_status,
                        source_ip=message.get("src_ip", "unknown"),
                        source_port=message.get("src_port", 0),
                        destination_ip=message.get("dest_ip", "unknown"),
                        destination_port=message.get("dest_port", 0),
                        tls_version=tls_version,
                        server_name=sni,
                        cipher_suite=cipher_suite,
                    )
                    if alert_id:
                        logger.info(f"   🚨 Vulnerable crypto alert created: {alert_id}")
                except Exception as e:
                    logger.error(f"   ✗ Error creating vulnerable crypto alert: {e}")

            # Update network topology
            if self.topology_service:
                try:
                    await self.topology_service.update_topology_from_connection(
                        source_ip=message.get("src_ip", "unknown"),
                        source_port=message.get("src_port", 0),
                        dest_ip=message.get("dest_ip", "unknown"),
                        dest_port=message.get("dest_port", 0),
                        protocol=message.get("proto", "TCP"),
                        crypto_type=crypto_type.value,
                        pqc_status=pqc_status,
                        confidence=confidence,
                        tls_version=tls_version,
                        server_name=sni,
                        cipher_suite=cipher_suite,
                        bytes_to_server=bytes_to_server,
                        bytes_to_client=bytes_to_client,
                        has_ech=has_ech,
                        posture=suricata_posture,
                    )
                    logger.debug("   ✓ Updated network topology")
                except Exception as e:
                    logger.error(f"   ✗ Error updating topology: {e}")

            # Log running statistics every 10 messages
            if self.message_count % 10 == 0:
                pqc_percentage = (
                    (self.pqc_count / self.message_count * 100) if self.message_count > 0 else 0
                )
                logger.info("")
                logger.info(f"   📊 RUNNING STATISTICS (Total: {self.message_count} messages)")
                logger.info(f"      PQC: {self.pqc_count} ({pqc_percentage:.1f}%)")
                logger.info(f"      Hybrid: {self.hybrid_count}")
                logger.info(f"      Classical: {self.classical_count}")

            logger.info("=" * 80)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ ERROR processing TLS message: {e}", exc_info=True)
            logger.error("=" * 80)

    def _parse_client_hello(self, tls_data: dict):
        """
        Parse ClientHello from Suricata TLS log

        Args:
            tls_data: TLS section from Suricata log

        Returns:
            TLSClientHello object or None
        """
        from ngfw_pqc_detector.models import TLSClientHello, TLSVersion

        try:
            version_str = tls_data.get("version", "unknown")
            version = TLSVersion.TLS_1_3 if "1.3" in version_str else TLSVersion.UNKNOWN

            # Check for new PQC structure (tls.pqc)
            pqc_data = tls_data.get("pqc", {})

            # Extract supported groups
            supported_groups = []
            if pqc_data.get("supported_groups_names"):
                # Use human-readable names if available
                supported_groups = pqc_data.get("supported_groups_names", [])
            elif pqc_data.get("supported_groups"):
                # Fallback to numeric codes
                supported_groups = [str(g) for g in pqc_data.get("supported_groups", [])]
            else:
                # Legacy format
                supported_groups = tls_data.get("supported_groups", [])

            # Extract key share groups
            key_share_groups = []
            if pqc_data.get("key_share_groups_names"):
                # Use human-readable names if available
                key_share_groups = pqc_data.get("key_share_groups_names", [])
            elif pqc_data.get("key_share_groups"):
                # Fallback to numeric codes
                key_share_groups = [str(g) for g in pqc_data.get("key_share_groups", [])]
            else:
                # Legacy format
                key_share_groups = tls_data.get("key_share", [])

            # Extract signature algorithms (if available)
            signature_algorithms = tls_data.get("signature_algorithms", [])

            # Parse cipher suites
            cipher_suites = []
            for cipher_hex in tls_data.get("ja3s", {}).get("cipher_suites", []):
                cipher_suite = self.pqc_detector.classify_cipher_suite(
                    cipher_code=cipher_hex, cipher_name=tls_data.get("cipher_suite_name", "unknown")
                )
                cipher_suites.append(cipher_suite)

            return TLSClientHello(
                version=version,
                cipher_suites=cipher_suites,
                extensions=tls_data.get("extensions", {}),
                supported_groups=supported_groups,
                signature_algorithms=signature_algorithms,
                key_share_groups=key_share_groups,
            )

        except Exception as e:
            logger.error(f"Error parsing ClientHello: {e}", exc_info=True)
            return None

    def _create_enriched_message(
        self,
        message: dict,
        crypto_type: str,
        pqc_status: str,
        confidence: float,
        bytes_to_server: int,
        bytes_to_client: int,
        total_bytes: int,
        exchange_groups: Optional[dict] = None,
        algorithms: Optional[dict] = None,
        tls_info: Optional[dict] = None,
        posture: Optional[str] = None,
        has_ech: Optional[bool] = None,
    ) -> dict:
        """
        Create enriched message with PQC detection results

        Args:
            message: Original Kafka message
            crypto_type: Detected crypto type (classical/post-quantum/hybrid/unknown)
            pqc_status: PQC safety status (safe/vulnerable/unknown)
            confidence: Detection confidence score
            bytes_to_server: Bytes sent to server
            bytes_to_client: Bytes sent to client
            total_bytes: Total bytes transferred
            exchange_groups: Exchange groups classification (optional)
            algorithms: Algorithm details (optional)
            tls_info: TLS information (optional)
            posture: Suricata's PQC posture (optional)
            has_ech: Encrypted Client Hello support (optional)

        Returns:
            Enriched message in standardized format
        """
        # Extract flow data
        flow_data = message.get("flow", {})
        tls_data = message.get("tls", {})
        http_data = message.get("http", {})

        # Determine detection method
        detection_method = "algorithm_based"
        if total_bytes > 0:
            detection_method = "hybrid_algorithm_and_bytes"

        # Extract hostname from HTTP data or TLS SNI
        hostname = None
        if http_data and http_data.get("hostname"):
            hostname = http_data.get("hostname")
        elif tls_data and tls_data.get("sni"):
            hostname = tls_data.get("sni")

        # Build enriched message
        enriched = {
            "type": "kafka_message",
            "timestamp": message.get("timestamp", datetime.utcnow().isoformat()),
            "data": {
                # Network information
                "src_ip": message.get("src_ip", "unknown"),
                "src_port": message.get("src_port", 0),
                "dest_ip": message.get("dest_ip", "unknown"),
                "dest_port": message.get("dest_port", 0),
                "proto": message.get("proto", "unknown"),
                "flow_id": message.get("flow_id", 0),
                "event_type": message.get("event_type", "unknown"),
                "ip_v": message.get("ip_version", 4),
                "in_iface": message.get("in_iface", "unknown"),
                "app_proto": message.get("app_proto", "unknown"),
                "hostname": hostname,  # Add hostname field
                # Flow information
                "flow": {
                    "bytes_toserver": bytes_to_server,
                    "bytes_toclient": bytes_to_client,
                    "total_bytes": total_bytes,
                    "state": flow_data.get("state", "unknown"),
                },
                # PQC Detection Results
                "pqc_detection": {
                    "status": pqc_status,  # safe/vulnerable/unknown
                    "crypto_type": crypto_type,  # classical/post-quantum/hybrid/unknown
                    "confidence": round(confidence, 4),
                    "detection_method": detection_method,
                    "is_pqc_safe": pqc_status == "safe",
                    "posture": posture if posture else "unknown",  # Suricata's PQC posture
                    "has_ech": (
                        has_ech if has_ech is not None else False
                    ),  # Encrypted Client Hello support
                    # Exchange Groups Classification
                    "exchange_groups": (
                        exchange_groups
                        if exchange_groups
                        else {
                            "pqc_groups": [],
                            "hybrid_groups": [],
                            "classical_groups": [],
                            "total_groups": 0,
                            "has_pqc": False,
                        }
                    ),
                    # Algorithm Details
                    "algorithms": (
                        algorithms
                        if algorithms
                        else {
                            "supported_groups": [],
                            "key_share_groups": [],
                            "signature_algorithms": [],
                            "cipher_suites": [],
                        }
                    ),
                },
            },
        }

        # Add TLS-specific information if available
        if tls_data:
            enriched["data"]["tls"] = {
                "version": tls_data.get("version", "unknown"),
                "sni": tls_data.get("sni", None),
                "cipher_suite": tls_data.get("cipher_suite_name", "unknown"),
                "ja3": tls_data.get("ja3", {}).get("hash", None) if tls_data.get("ja3") else None,
            }
        elif tls_info:
            # Use extracted TLS info if no tls_data but tls_info provided
            enriched["data"]["tls"] = tls_info

        # Add HTTP-specific information if available
        if http_data:
            enriched["data"]["http"] = {
                "hostname": http_data.get("hostname", None),
                "url": http_data.get("url", None),
                "http_method": http_data.get("http_method", None),
                "status": http_data.get("status", None),
                "protocol": http_data.get("protocol", None),
                "http_user_agent": http_data.get("http_user_agent", None),
                "http_content_type": http_data.get("http_content_type", None),
                "length": http_data.get("length", None),
                "redirect": http_data.get("redirect", None),
            }

        # Add raw Kafka message for debugging/analysis
        enriched["data"]["raw"] = message

        return enriched

    def _extract_tls_info_from_message(self, message: dict) -> Optional[dict]:
        """
        Extract TLS information directly from Kafka message

        Args:
            message: Original Kafka message

        Returns:
            Dictionary with TLS information or None
        """
        tls_data = message.get("tls", {})

        if not tls_data:
            return None

        tls_info = {
            "version": tls_data.get("version", "unknown"),
            "sni": tls_data.get("sni", None),
            "cipher_suite": tls_data.get("cipher_suite_name", "unknown"),
            "ja3": tls_data.get("ja3", {}).get("hash", None) if tls_data.get("ja3") else None,
        }

        # Extract supported groups if available
        supported_groups = tls_data.get("supported_groups", [])
        key_share_groups = tls_data.get("key_share", [])
        signature_algorithms = tls_data.get("signature_algorithms", [])

        if supported_groups or key_share_groups or signature_algorithms:
            tls_info["supported_groups"] = supported_groups
            tls_info["key_share_groups"] = key_share_groups
            tls_info["signature_algorithms"] = signature_algorithms

        return tls_info

    async def _store_flow_event(
        self,
        message: dict,
        crypto_type: str,
        pqc_status: str,
        confidence: float,
        bytes_to_server: int,
        bytes_to_client: int,
        total_bytes: int,
    ):
        """
        Store flow event (TLS without handshake or non-TLS) in MongoDB
        
        Args:
            message: Raw Kafka message
            crypto_type: Detected crypto type
            pqc_status: PQC status
            confidence: Detection confidence
            bytes_to_server: Bytes to server
            bytes_to_client: Bytes to client
            total_bytes: Total bytes
        """
        from ngfw_pqc_detector.models import CryptoType
        
        # Convert string crypto_type to enum if needed
        if isinstance(crypto_type, str):
            try:
                crypto_type_enum = CryptoType(crypto_type)
            except ValueError:
                crypto_type_enum = CryptoType.UNKNOWN
        else:
            crypto_type_enum = crypto_type
        
        document = {
            "timestamp": datetime.fromisoformat(
                message.get("timestamp", datetime.utcnow().isoformat())
            ),
            "source_ip": message.get("src_ip", "unknown"),
            "source_port": message.get("src_port", 0),
            "destination_ip": message.get("dest_ip", "unknown"),
            "destination_port": message.get("dest_port", 0),
            "server_name": message.get("tls", {}).get("sni", None),
            "tls_version": message.get("tls", {}).get("version", "unknown"),
            "cipher_suite_code": None,
            "cipher_suite_name": message.get("tls", {}).get("cipher_suite_name", None),
            "crypto_type": crypto_type if isinstance(crypto_type, str) else crypto_type.value,
            "is_pqc": pqc_status == "safe",
            "is_hybrid": crypto_type == "hybrid" or (isinstance(crypto_type, CryptoType) and crypto_type == CryptoType.HYBRID),
            "bytes_to_server": bytes_to_server,
            "bytes_to_client": bytes_to_client,
            "total_bytes": total_bytes,
            "detection_confidence": confidence,
            "detection_method": "byte_based_heuristic" if total_bytes > 0 else "unknown",
            "client_hello_data": None,
            "raw_log_data": message,
            "event_type": message.get("event_type", "unknown"),
            "app_proto": message.get("app_proto", "unknown"),
        }
        
        result = await self.db_service.collection.insert_one(document)
        logger.debug(f"Stored flow event: ID={result.inserted_id}")

    async def stop(self):
        """Stop the Kafka consumer"""
        logger.info("Stopping Kafka consumer...")
        self.running = False

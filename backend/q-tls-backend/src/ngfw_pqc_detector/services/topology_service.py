"""
Network Topology Service for building and managing network graphs
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, IndexModel

from ngfw_pqc_detector.models.network_topology import (
    NetworkNode,
    NetworkEdge,
    NetworkTopology,
    ConnectionSecurity,
    TopologyStats,
)

logger = logging.getLogger(__name__)


class TopologyService:
    """Service for managing network topology data"""

    def __init__(
        self,
        nodes_collection: AsyncIOMotorCollection,
        edges_collection: AsyncIOMotorCollection,
    ):
        self.nodes_collection = nodes_collection
        self.edges_collection = edges_collection

    async def initialize_indexes(self):
        """Create indexes for topology collections"""
        try:
            # Node indexes
            node_indexes = [
                IndexModel([("node_id", ASCENDING)], unique=True),
                IndexModel([("last_seen", DESCENDING)]),
                IndexModel([("node_type", ASCENDING)]),
            ]
            await self.nodes_collection.create_indexes(node_indexes)

            # Edge indexes
            edge_indexes = [
                IndexModel([("edge_id", ASCENDING)], unique=True),
                IndexModel([("source_ip", ASCENDING)]),
                IndexModel([("destination_ip", ASCENDING)]),
                IndexModel([("last_seen", DESCENDING)]),
                IndexModel([("security.pqc_status", ASCENDING)]),
                IndexModel([("source_ip", ASCENDING), ("destination_ip", ASCENDING)]),
            ]
            await self.edges_collection.create_indexes(edge_indexes)

            logger.info("Topology indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating topology indexes: {e}", exc_info=True)

    def _generate_edge_id(
        self, source_ip: str, dest_ip: str, source_port: int, dest_port: int
    ) -> str:
        """Generate unique edge ID"""
        return f"{source_ip}:{source_port}->{dest_ip}:{dest_port}"

    def _classify_node_type(self, ip: str) -> str:
        """Classify node as internal or external based on IP"""
        # Simple classification - can be enhanced
        if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
            return "internal"
        return "external"

    async def update_topology_from_connection(
        self,
        source_ip: str,
        source_port: int,
        dest_ip: str,
        dest_port: int,
        protocol: str,
        crypto_type: str,
        pqc_status: str,
        confidence: float,
        tls_version: Optional[str] = None,
        server_name: Optional[str] = None,
        cipher_suite: Optional[str] = None,
        bytes_to_server: int = 0,
        bytes_to_client: int = 0,
        has_ech: bool = False,
        posture: str = "unknown",
    ):
        """
        Update topology with a new connection

        Args:
            source_ip: Source IP address
            source_port: Source port
            dest_ip: Destination IP address
            dest_port: Destination port
            protocol: Protocol (TCP, UDP, etc.)
            crypto_type: Cryptography type (classical, post-quantum, hybrid, unknown)
            pqc_status: PQC status (safe, vulnerable, unknown)
            confidence: Detection confidence
            tls_version: TLS version if applicable
            server_name: Server name (SNI) if applicable
            cipher_suite: Cipher suite if applicable
            bytes_to_server: Bytes sent to server
            bytes_to_client: Bytes sent from server
            has_ech: Whether ECH is used
            posture: Suricata PQC posture
        """
        try:
            now = datetime.utcnow()

            # Update or create source node
            await self._update_node(
                node_id=source_ip,
                node_type="source",
                port=source_port,
                protocol=protocol,
                is_secure=(pqc_status == "safe"),
                timestamp=now,
            )

            # Update or create destination node
            await self._update_node(
                node_id=dest_ip,
                node_type="destination",
                port=dest_port,
                protocol=protocol,
                is_secure=(pqc_status == "safe"),
                timestamp=now,
                hostname=server_name,
            )

            # Update or create edge
            await self._update_edge(
                source_ip=source_ip,
                source_port=source_port,
                dest_ip=dest_ip,
                dest_port=dest_port,
                protocol=protocol,
                crypto_type=crypto_type,
                pqc_status=pqc_status,
                confidence=confidence,
                tls_version=tls_version,
                server_name=server_name,
                cipher_suite=cipher_suite,
                bytes_to_server=bytes_to_server,
                bytes_to_client=bytes_to_client,
                has_ech=has_ech,
                posture=posture,
                timestamp=now,
            )

            logger.debug(f"Updated topology: {source_ip}:{source_port} -> {dest_ip}:{dest_port}")

        except Exception as e:
            logger.error(f"Error updating topology: {e}", exc_info=True)

    async def _update_node(
        self,
        node_id: str,
        node_type: str,
        port: int,
        protocol: str,
        is_secure: bool,
        timestamp: datetime,
        hostname: Optional[str] = None,
    ):
        """Update or create a network node"""
        classified_type = self._classify_node_type(node_id)

        update_doc = {
            "$set": {
                "last_seen": timestamp,
                "node_type": classified_type,
            },
            "$setOnInsert": {
                "node_id": node_id,
                "first_seen": timestamp,
            },
            "$inc": {
                "connection_count": 1,
                "secure_connections": 1 if is_secure else 0,
                "insecure_connections": 0 if is_secure else 1,
            },
            "$addToSet": {
                "ports": port,
                "protocols": protocol,
            },
        }

        if hostname:
            update_doc["$set"]["hostname"] = hostname

        await self.nodes_collection.update_one({"node_id": node_id}, update_doc, upsert=True)

    async def _update_edge(
        self,
        source_ip: str,
        source_port: int,
        dest_ip: str,
        dest_port: int,
        protocol: str,
        crypto_type: str,
        pqc_status: str,
        confidence: float,
        tls_version: Optional[str],
        server_name: Optional[str],
        cipher_suite: Optional[str],
        bytes_to_server: int,
        bytes_to_client: int,
        has_ech: bool,
        posture: str,
        timestamp: datetime,
    ):
        """Update or create a network edge (connection)"""
        edge_id = self._generate_edge_id(source_ip, dest_ip, source_port, dest_port)

        security = {
            "is_secure": pqc_status == "safe",
            "crypto_type": crypto_type,
            "pqc_status": pqc_status,
            "confidence": confidence,
            "has_ech": has_ech,
            "posture": posture,
        }

        update_doc = {
            "$set": {
                "last_seen": timestamp,
                "security": security,
            },
            "$setOnInsert": {
                "edge_id": edge_id,
                "source_ip": source_ip,
                "source_port": source_port,
                "destination_ip": dest_ip,
                "destination_port": dest_port,
                "protocol": protocol,
                "first_seen": timestamp,
            },
            "$inc": {
                "connection_count": 1,
                "bytes_to_server": bytes_to_server,
                "bytes_to_client": bytes_to_client,
                "total_bytes": bytes_to_server + bytes_to_client,
            },
        }

        if tls_version:
            update_doc["$set"]["tls_version"] = tls_version
        if server_name:
            update_doc["$set"]["server_name"] = server_name
        if cipher_suite:
            update_doc["$set"]["cipher_suite"] = cipher_suite

        await self.edges_collection.update_one({"edge_id": edge_id}, update_doc, upsert=True)

    async def get_topology(
        self, time_window_minutes: int = 60, include_inactive: bool = False
    ) -> NetworkTopology:
        """
        Get current network topology

        Args:
            time_window_minutes: Time window to consider (default: 60 minutes)
            include_inactive: Include nodes/edges not seen in time window

        Returns:
            NetworkTopology object with nodes and edges
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

            # Build query
            query = {} if include_inactive else {"last_seen": {"$gte": cutoff_time}}

            # Fetch nodes
            nodes_cursor = self.nodes_collection.find(query)
            nodes_list = await nodes_cursor.to_list(length=None)

            # Fetch edges
            edges_cursor = self.edges_collection.find(query)
            edges_list = await edges_cursor.to_list(length=None)

            # Build topology
            nodes = {}
            for node_doc in nodes_list:
                node_doc.pop("_id", None)
                nodes[node_doc["node_id"]] = NetworkNode(**node_doc)

            edges = {}
            secure_count = 0
            insecure_count = 0
            unknown_count = 0

            for edge_doc in edges_list:
                edge_doc.pop("_id", None)
                edge_id = edge_doc["edge_id"]

                # Convert security dict to ConnectionSecurity model
                if "security" in edge_doc:
                    edge_doc["security"] = ConnectionSecurity(**edge_doc["security"])

                edge = NetworkEdge(**edge_doc)
                edges[edge_id] = edge

                # Count security status
                if edge.security.pqc_status == "safe":
                    secure_count += 1
                elif edge.security.pqc_status == "vulnerable":
                    insecure_count += 1
                else:
                    unknown_count += 1

            topology = NetworkTopology(
                timestamp=datetime.utcnow(),
                nodes=nodes,
                edges=edges,
                total_nodes=len(nodes),
                total_edges=len(edges),
                secure_connections=secure_count,
                insecure_connections=insecure_count,
                unknown_connections=unknown_count,
                time_window_minutes=time_window_minutes,
            )

            return topology

        except Exception as e:
            logger.error(f"Error getting topology: {e}", exc_info=True)
            return NetworkTopology()

    async def get_topology_stats(self, time_window_minutes: int = 60) -> TopologyStats:
        """
        Get topology statistics

        Args:
            time_window_minutes: Time window to consider

        Returns:
            TopologyStats object
        """
        try:
            topology = await self.get_topology(time_window_minutes)

            # Calculate statistics
            internal_nodes = sum(
                1 for node in topology.nodes.values() if node.node_type == "internal"
            )
            external_nodes = sum(
                1 for node in topology.nodes.values() if node.node_type == "external"
            )

            # Protocol distribution
            protocol_dist = {}
            for edge in topology.edges.values():
                protocol_dist[edge.protocol] = protocol_dist.get(edge.protocol, 0) + 1

            # Top sources and destinations
            source_counts = {}
            dest_counts = {}
            for edge in topology.edges.values():
                source_counts[edge.source_ip] = (
                    source_counts.get(edge.source_ip, 0) + edge.connection_count
                )
                dest_counts[edge.destination_ip] = (
                    dest_counts.get(edge.destination_ip, 0) + edge.connection_count
                )

            top_sources = [
                {"ip": ip, "connections": count}
                for ip, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            ]

            top_destinations = [
                {"ip": ip, "connections": count}
                for ip, count in sorted(dest_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]

            # Security percentages
            total_conns = topology.total_edges
            pqc_safe_pct = (
                (topology.secure_connections / total_conns * 100) if total_conns > 0 else 0
            )

            # Count crypto types
            classical_count = sum(
                1 for edge in topology.edges.values() if edge.security.crypto_type == "classical"
            )
            hybrid_count = sum(
                1 for edge in topology.edges.values() if edge.security.crypto_type == "hybrid"
            )

            classical_pct = (classical_count / total_conns * 100) if total_conns > 0 else 0
            hybrid_pct = (hybrid_count / total_conns * 100) if total_conns > 0 else 0

            return TopologyStats(
                total_nodes=topology.total_nodes,
                total_connections=topology.total_edges,
                secure_connections=topology.secure_connections,
                insecure_connections=topology.insecure_connections,
                unknown_connections=topology.unknown_connections,
                internal_nodes=internal_nodes,
                external_nodes=external_nodes,
                protocol_distribution=protocol_dist,
                top_sources=top_sources,
                top_destinations=top_destinations,
                pqc_safe_percentage=round(pqc_safe_pct, 2),
                classical_percentage=round(classical_pct, 2),
                hybrid_percentage=round(hybrid_pct, 2),
            )

        except Exception as e:
            logger.error(f"Error getting topology stats: {e}", exc_info=True)
            return TopologyStats()

    async def cleanup_old_data(self, days: int = 7):
        """
        Clean up old topology data

        Args:
            days: Remove data older than this many days
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            nodes_result = await self.nodes_collection.delete_many(
                {"last_seen": {"$lt": cutoff_time}}
            )
            edges_result = await self.edges_collection.delete_many(
                {"last_seen": {"$lt": cutoff_time}}
            )

            logger.info(
                f"Cleaned up topology data: {nodes_result.deleted_count} nodes, "
                f"{edges_result.deleted_count} edges older than {days} days"
            )

        except Exception as e:
            logger.error(f"Error cleaning up topology data: {e}", exc_info=True)

"""
Network Topology Models for Graph Visualization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConnectionSecurity(BaseModel):
    """Security status of a connection"""

    is_secure: bool = False
    crypto_type: str = "unknown"  # classical, post-quantum, hybrid, unknown
    pqc_status: str = "unknown"  # safe, vulnerable, unknown
    confidence: float = 0.0
    has_ech: bool = False
    posture: str = "unknown"


class NetworkNode(BaseModel):
    """Represents a node (IP address) in the network topology"""

    node_id: str  # IP address
    node_type: str = "unknown"  # source, destination, internal, external
    hostname: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    connection_count: int = 0
    secure_connections: int = 0
    insecure_connections: int = 0
    ports: List[int] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list)


class NetworkEdge(BaseModel):
    """Represents a connection (edge) between two nodes"""

    edge_id: str  # Unique identifier for this edge
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str = "TCP"

    # Connection metadata
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    connection_count: int = 1

    # Security information
    security: ConnectionSecurity

    # TLS information (if applicable)
    tls_version: Optional[str] = None
    server_name: Optional[str] = None
    cipher_suite: Optional[str] = None

    # Traffic statistics
    bytes_to_server: int = 0
    bytes_to_client: int = 0
    total_bytes: int = 0


class NetworkTopology(BaseModel):
    """Complete network topology graph"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    nodes: Dict[str, NetworkNode] = Field(default_factory=dict)
    edges: Dict[str, NetworkEdge] = Field(default_factory=dict)

    # Summary statistics
    total_nodes: int = 0
    total_edges: int = 0
    secure_connections: int = 0
    insecure_connections: int = 0
    unknown_connections: int = 0

    # Time window for this topology snapshot
    time_window_minutes: int = 60


class TopologyStats(BaseModel):
    """Statistics about the network topology"""

    total_nodes: int = 0
    total_connections: int = 0
    secure_connections: int = 0
    insecure_connections: int = 0
    unknown_connections: int = 0

    # Node statistics
    internal_nodes: int = 0
    external_nodes: int = 0

    # Protocol distribution
    protocol_distribution: Dict[str, int] = Field(default_factory=dict)

    # Top talkers
    top_sources: List[Dict[str, Any]] = Field(default_factory=list)
    top_destinations: List[Dict[str, Any]] = Field(default_factory=list)

    # Security summary
    pqc_safe_percentage: float = 0.0
    classical_percentage: float = 0.0
    hybrid_percentage: float = 0.0

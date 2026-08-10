"""
Accumulated Statistics Models
Real-time accumulated counters that are continuously updated
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class AccumulatedNetworkStats(BaseModel):
    """Accumulated network flow statistics"""

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Total counters
    total_flows: int = 0
    total_tls_flows: int = 0
    total_tcp_flows: int = 0
    total_udp_flows: int = 0
    total_other_flows: int = 0

    # TLS/PQC counters
    total_pqc_safe: int = 0
    total_pqc_vulnerable: int = 0
    total_pqc_unknown: int = 0

    # Bytes transferred
    total_bytes_to_server: int = 0
    total_bytes_to_client: int = 0
    total_bytes: int = 0

    # Alert counters
    total_alerts: int = 0
    total_critical_alerts: int = 0
    total_high_alerts: int = 0
    total_medium_alerts: int = 0
    total_low_alerts: int = 0

    # Protocol distribution (app_proto counts)
    protocol_distribution: Dict[str, int] = Field(default_factory=dict)

    # TLS version distribution
    tls_version_distribution: Dict[str, int] = Field(default_factory=dict)

    # Cipher suite distribution (top 20)
    cipher_suite_distribution: Dict[str, int] = Field(default_factory=dict)

    # Key exchange distribution
    key_exchange_distribution: Dict[str, int] = Field(default_factory=dict)

    # Flow state distribution
    flow_state_distribution: Dict[str, int] = Field(default_factory=dict)

    # PQC Posture distribution (CLASSICAL, PQC, HYBRID, UNKNOWN)
    posture_distribution: Dict[str, int] = Field(default_factory=dict)


class NetworkFlowRecord(BaseModel):
    """Individual network flow record"""

    flow_id: int
    event_time: datetime

    src_ip: str
    src_port: Optional[int] = None
    dest_ip: str
    dest_port: Optional[int] = None

    protocol: Optional[str] = None
    app_proto: Optional[str] = None

    bytes_to_server: int = 0
    bytes_to_client: int = 0

    flow_state: Optional[str] = None
    alerted: bool = False


class TLSSessionRecord(BaseModel):
    """Individual TLS session record"""

    flow_id: int
    event_time: datetime

    tls_version: Optional[str] = None
    key_exchange: Optional[str] = None
    cipher_suite: Optional[str] = None

    pqc_status: str  # SAFE / VULNERABLE / UNKNOWN
    pqc_reason: Optional[str] = None


class AlertRecord(BaseModel):
    """Individual alert record"""

    event_time: datetime
    flow_id: Optional[int] = None

    alert_type: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None

    acknowledged: bool = False

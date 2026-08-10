"""
Alert Models for Security Alerts
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, Enum):
    """Types of security alerts"""

    INSECURE_TLS_VERSION = "insecure_tls_version"
    WEAK_CIPHER = "weak_cipher"
    NO_PQC = "no_pqc"
    SUSPICIOUS_CONNECTION = "suspicious_connection"
    PROTOCOL_VIOLATION = "protocol_violation"


class Alert(BaseModel):
    """Security Alert Model"""

    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str

    # Connection details
    source_ip: str
    source_port: int
    destination_ip: str
    destination_port: int
    server_name: Optional[str] = None

    # TLS details
    tls_version: Optional[str] = None
    cipher_suite: Optional[str] = None
    crypto_type: Optional[str] = None

    # Additional metadata
    metadata: dict = Field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "alert_type": "insecure_tls_version",
                "severity": "high",
                "title": "Insecure TLS Version Detected",
                "description": "Connection using TLS 1.2 detected. TLS 1.3 or higher is recommended.",
                "source_ip": "192.168.1.100",
                "source_port": 54321,
                "destination_ip": "93.184.216.34",
                "destination_port": 443,
                "server_name": "example.com",
                "tls_version": "TLS 1.2",
                "cipher_suite": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                "crypto_type": "classical",
            }
        }

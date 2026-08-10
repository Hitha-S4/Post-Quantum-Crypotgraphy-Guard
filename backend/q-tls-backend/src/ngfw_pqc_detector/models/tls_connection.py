"""
TLS Connection Models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class CryptoType(str, Enum):
    """Cryptography type classification"""
    CLASSICAL = "classical"
    PQC = "post-quantum"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class TLSVersion(str, Enum):
    """TLS protocol versions"""
    TLS_1_0 = "TLS 1.0"
    TLS_1_1 = "TLS 1.1"
    TLS_1_2 = "TLS 1.2"
    TLS_1_3 = "TLS 1.3"
    UNKNOWN = "unknown"


class CipherSuite(BaseModel):
    """TLS Cipher Suite information"""
    code: str
    name: str
    crypto_type: CryptoType
    key_exchange: Optional[str] = None
    authentication: Optional[str] = None
    encryption: Optional[str] = None
    mac: Optional[str] = None


class TLSClientHello(BaseModel):
    """TLS ClientHello message data"""
    version: TLSVersion
    cipher_suites: List[CipherSuite]
    extensions: dict = Field(default_factory=dict)
    supported_groups: List[str] = Field(default_factory=list)
    signature_algorithms: List[str] = Field(default_factory=list)
    key_share_groups: List[str] = Field(default_factory=list)


class TLSConnection(BaseModel):
    """TLS Connection record"""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: str
    source_port: int
    destination_ip: str
    destination_port: int
    server_name: Optional[str] = None

    # TLS Information
    tls_version: TLSVersion
    selected_cipher_suite: Optional[CipherSuite] = None
    client_hello: TLSClientHello

    # Classification
    crypto_type: CryptoType
    is_pqc: bool = False
    is_hybrid: bool = False

    # Byte counts for heuristic detection
    bytes_to_server: int = 0
    bytes_to_client: int = 0
    total_bytes: int = 0

    # Detection metadata
    detection_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    detection_method: str = "client_hello_inspection"

    class Config:
        json_schema_extra = {
            "example": {
                "source_ip": "192.168.1.100",
                "source_port": 54321,
                "destination_ip": "93.184.216.34",
                "destination_port": 443,
                "server_name": "example.com",
                "tls_version": "TLS 1.3",
                "crypto_type": "post-quantum",
                "is_pqc": True,
                "is_hybrid": False,
            }
        }

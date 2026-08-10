"""
Statistics Models for TLS Connection Analytics
"""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConnectionStats(BaseModel):
    """Real-time connection statistics"""
    total_connections: int = 0
    pqc_connections: int = 0
    hybrid_connections: int = 0
    classical_connections: int = 0
    unknown_connections: int = 0
    pqc_percentage: float = 0.0
    hybrid_percentage: float = 0.0
    classical_percentage: float = 0.0


class CipherSuiteStats(BaseModel):
    """Cipher suite usage statistics"""
    cipher_suite_name: str
    count: int
    percentage: float
    crypto_type: str
    is_pqc: bool


class ServerStats(BaseModel):
    """Per-server statistics"""
    server_name: str
    total_connections: int
    pqc_connections: int
    classical_connections: int
    pqc_percentage: float
    last_seen: datetime


class TimeSeriesDataPoint(BaseModel):
    """Time series data point for trending"""
    timestamp: datetime
    total_connections: int
    pqc_connections: int
    classical_connections: int
    hybrid_connections: int


class AggregatedStats(BaseModel):
    """Aggregated statistics document stored in MongoDB"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    time_window_minutes: int
    
    # Connection statistics
    connection_stats: ConnectionStats
    
    # Top cipher suites
    top_cipher_suites: List[CipherSuiteStats] = Field(default_factory=list)
    
    # Top servers
    top_servers: List[ServerStats] = Field(default_factory=list)
    
    # TLS version distribution
    tls_version_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Geographic distribution (if available)
    source_ip_countries: Dict[str, int] = Field(default_factory=dict)
    destination_ip_countries: Dict[str, int] = Field(default_factory=dict)
    
    # Time series data for the window
    time_series: List[TimeSeriesDataPoint] = Field(default_factory=list)
    
    # Detection confidence statistics
    avg_detection_confidence: float = 0.0
    min_detection_confidence: float = 0.0
    max_detection_confidence: float = 0.0
    
    # Processing metadata
    events_processed: int = 0
    processing_duration_seconds: float = 0.0


class LiveStats(BaseModel):
    """Live statistics for real-time display"""
    current_timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: int = 0
    
    # Current rates
    events_per_second: float = 0.0
    pqc_events_per_second: float = 0.0
    
    # Cumulative counters
    total_events_processed: int = 0
    total_pqc_detected: int = 0
    total_classical_detected: int = 0
    total_hybrid_detected: int = 0
    
    # Recent statistics (last N minutes)
    recent_stats: Optional[AggregatedStats] = None
    
    # System health
    kafka_connected: bool = False
    mongodb_connected: bool = False
    last_event_timestamp: Optional[datetime] = None
"""
Application Configuration
"""

from typing import List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Settings
    APP_NAME: str = "NGFW PQC Detector"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_LOG_LEVEL: str = "INFO"
    APP_WORKERS: int = 4

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_TLS_LOGS: str = "suricata-events"
    KAFKA_CONSUMER_GROUP: str = "ngfw-pqc-detector"
    KAFKA_AUTO_OFFSET_RESET: str = "latest"

    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "ngfw_pqc"
    MONGODB_COLLECTION: str = "tls_connections"
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10

    # TLS/PQC Detection Settings
    PQC_DETECTION_ENABLED: bool = True
    CLASSICAL_CRYPTO_DETECTION_ENABLED: bool = True
    HYBRID_CRYPTO_DETECTION_ENABLED: bool = True

    # Suricata Integration
    SURICATA_LOG_PATH: str = "/var/log/suricata/eve.json"
    SURICATA_ENABLED: bool = True

    # API Settings
    API_ENABLE_CORS: bool = True
    API_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:8081",
    ]

    # Analytics Settings
    ANALYTICS_ENABLED: bool = True
    ANALYTICS_BATCH_INTERVAL: int = 60  # seconds
    ANALYTICS_TIME_WINDOW: int = 60  # minutes

    # Monitoring & Metrics
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    # AI Agent Settings
    AGENT_ENABLED: bool = True
    AGENT_PROVIDER: Literal["openai", "anthropic", "local"] = "openai"
    AGENT_MODEL: str = "gpt-4o-mini"
    AGENT_API_KEY: Optional[str] = None
    AGENT_OPENAI_API_KEY: Optional[str] = None
    AGENT_ANTHROPIC_API_KEY: Optional[str] = None
    AGENT_LOCAL_BASE_URL: Optional[str] = "http://localhost:11434"
    AGENT_MEMORY_TTL_MINUTES: int = 180
    AGENT_MEMORY_MAX_MESSAGES: int = 20
    AGENT_TEMPERATURE: float = 0.2
    AGENT_MAX_OUTPUT_TOKENS: int = 1200
    AGENT_LLM_TIMEOUT_SECONDS: float = 30.0

    # Agent behavior controls
    AGENT_REQUIRE_GROUNDED_RESPONSES: bool = True
    AGENT_ENABLE_CLARIFICATION: bool = True


settings = Settings()



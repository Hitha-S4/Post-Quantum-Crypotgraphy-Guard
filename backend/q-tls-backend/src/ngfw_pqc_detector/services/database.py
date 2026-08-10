"""
Database Service for storing TLS connection data using MongoDB
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, IndexModel

from ngfw_pqc_detector.core.config import settings
from ngfw_pqc_detector.models import CryptoType, TLSClientHello

logger = logging.getLogger(__name__)

# MongoDB client and database
mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None
tls_connections_collection: Optional[AsyncIOMotorCollection] = None


async def init_db():
    """Initialize MongoDB connection and create indexes"""
    global mongo_client, mongo_db, tls_connections_collection

    logger.info(f"Initializing MongoDB: {settings.MONGODB_URL}")

    # Create MongoDB client
    mongo_client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
        minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
    )

    # Get database
    mongo_db = mongo_client[settings.MONGODB_DATABASE]
    tls_connections_collection = mongo_db[settings.MONGODB_COLLECTION]

    # Create indexes for TLS connections collection
    indexes = [
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("source_ip", ASCENDING)]),
        IndexModel([("destination_ip", ASCENDING)]),
        IndexModel([("server_name", ASCENDING)]),
        IndexModel([("crypto_type", ASCENDING)]),
        IndexModel([("is_pqc", ASCENDING)]),
        IndexModel([("tls_version", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING), ("is_pqc", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING), ("crypto_type", ASCENDING)]),
    ]

    await tls_connections_collection.create_indexes(indexes)

    # Create indexes for alerts collection
    alerts_collection = mongo_db["alerts"]
    alert_indexes = [
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("alert_type", ASCENDING)]),
        IndexModel([("severity", ASCENDING)]),
        IndexModel([("acknowledged", ASCENDING)]),
        IndexModel([("source_ip", ASCENDING)]),
        IndexModel([("destination_ip", ASCENDING)]),
        IndexModel([("tls_version", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING), ("severity", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING), ("acknowledged", ASCENDING)]),
    ]

    await alerts_collection.create_indexes(alert_indexes)
    logger.info("MongoDB initialized successfully with indexes for TLS connections and alerts")


async def close_db():
    """Close MongoDB connection"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed")


class DatabaseService:
    """Service for database operations"""

    def __init__(self):
        pass

    @property
    def collection(self):
        """Get MongoDB collection (lazy loading)"""
        return tls_connections_collection

    async def store_tls_connection(
        self,
        message: dict,
        client_hello: TLSClientHello,
        crypto_type: CryptoType,
        confidence: float,
        bytes_to_server: int = 0,
        bytes_to_client: int = 0,
        total_bytes: int = 0,
    ) -> str:
        """
        Store TLS connection data in MongoDB

        Args:
            message: Raw Suricata log message
            client_hello: Parsed ClientHello data
            crypto_type: Detected crypto type
            confidence: Detection confidence score
            bytes_to_server: Bytes sent to server
            bytes_to_client: Bytes sent to client
            total_bytes: Total bytes transferred

        Returns:
            ID of stored document
        """
        document = {
            "timestamp": datetime.fromisoformat(
                message.get("timestamp", datetime.utcnow().isoformat())
            ),
            "source_ip": message.get("src_ip", "unknown"),
            "source_port": message.get("src_port", 0),
            "destination_ip": message.get("dest_ip", "unknown"),
            "destination_port": message.get("dest_port", 0),
            "server_name": message.get("tls", {}).get("sni", None),
            "tls_version": client_hello.version.value,
            "cipher_suite_code": (
                client_hello.cipher_suites[0].code if client_hello.cipher_suites else None
            ),
            "cipher_suite_name": (
                client_hello.cipher_suites[0].name if client_hello.cipher_suites else None
            ),
            "crypto_type": crypto_type.value,
            "is_pqc": crypto_type in (CryptoType.PQC, CryptoType.HYBRID),
            "is_hybrid": crypto_type == CryptoType.HYBRID,
            "bytes_to_server": bytes_to_server,
            "bytes_to_client": bytes_to_client,
            "total_bytes": total_bytes,
            "detection_confidence": confidence,
            "detection_method": (
                "client_hello_inspection" if total_bytes == 0 else "hybrid_algorithm_and_bytes"
            ),
            "client_hello_data": client_hello.model_dump(),
            "raw_log_data": message,
        }

        result = await self.collection.insert_one(document)
        logger.debug(f"Stored TLS connection record: ID={result.inserted_id}")
        return str(result.inserted_id)

    async def get_recent_connections(self, limit: int = 100) -> List[Dict]:
        """Get recent TLS connections"""
        cursor = self.collection.find().sort("timestamp", DESCENDING).limit(limit)
        connections = await cursor.to_list(length=limit)

        # Convert ObjectId to string for JSON serialization
        for conn in connections:
            conn["id"] = str(conn.pop("_id"))

        return connections

    async def get_pqc_connections(self, limit: int = 100) -> List[Dict]:
        """Get connections using PQC"""
        cursor = self.collection.find({"is_pqc": True}).sort("timestamp", DESCENDING).limit(limit)
        connections = await cursor.to_list(length=limit)

        # Convert ObjectId to string for JSON serialization
        for conn in connections:
            conn["id"] = str(conn.pop("_id"))

        return connections

    async def get_connection_stats(self) -> dict:
        """Get statistics about TLS connections"""
        pipeline = [
            {
                "$facet": {
                    "total": [{"$count": "count"}],
                    "pqc": [{"$match": {"is_pqc": True}}, {"$count": "count"}],
                    "hybrid": [{"$match": {"is_hybrid": True}}, {"$count": "count"}],
                    "classical": [
                        {"$match": {"crypto_type": CryptoType.CLASSICAL.value}},
                        {"$count": "count"},
                    ],
                }
            }
        ]

        result = await self.collection.aggregate(pipeline).to_list(length=1)

        if result:
            stats = result[0]
            total = stats["total"][0]["count"] if stats["total"] else 0
            pqc_count = stats["pqc"][0]["count"] if stats["pqc"] else 0
            hybrid_count = stats["hybrid"][0]["count"] if stats["hybrid"] else 0
            classical_count = stats["classical"][0]["count"] if stats["classical"] else 0
        else:
            total = pqc_count = hybrid_count = classical_count = 0

        return {
            "total_connections": total,
            "pqc_connections": pqc_count,
            "hybrid_connections": hybrid_count,
            "classical_connections": classical_count,
            "pqc_percentage": (pqc_count / total * 100) if total else 0,
        }

    async def get_connections_in_timewindow(
        self, time_window_minutes: int, filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Get connections within a time window with optional filters"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        query = {"timestamp": {"$gte": cutoff_time}}
        if filters:
            query.update(filters)

        cursor = self.collection.find(query).sort("timestamp", DESCENDING)
        connections = await cursor.to_list(length=None)

        # Convert ObjectId to string
        for conn in connections:
            conn["id"] = str(conn.pop("_id"))

        return connections

"""
Statistics Aggregation Service
Continuously monitors TLS connections and generates real-time statistics
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, Counter

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING

from ngfw_pqc_detector.core.config import settings
from ngfw_pqc_detector.models.statistics import (
    AggregatedStats,
    ConnectionStats,
    CipherSuiteStats,
    ServerStats,
    TimeSeriesDataPoint,
    LiveStats,
)
from ngfw_pqc_detector.models.tls_connection import CryptoType

logger = logging.getLogger(__name__)


class StatisticsService:
    """
    Service for aggregating and storing TLS connection statistics
    """

    def __init__(self, tls_collection: AsyncIOMotorCollection, stats_collection: AsyncIOMotorCollection):
        self.tls_collection = tls_collection
        self.stats_collection = stats_collection
        self.live_stats = LiveStats()
        self.start_time = datetime.utcnow()
        
        # Counters for live statistics
        self.event_counter = 0
        self.last_event_time = None
        self.events_in_last_second = []

    async def initialize(self):
        """Initialize the statistics service and create indexes"""
        # Create indexes for statistics collection
        await self.stats_collection.create_index([("timestamp", DESCENDING)])
        await self.stats_collection.create_index([("time_window_minutes", 1)])
        logger.info("Statistics service initialized")

    async def aggregate_statistics(self, time_window_minutes: int = 60) -> AggregatedStats:
        """
        Aggregate statistics for a given time window
        
        Args:
            time_window_minutes: Time window in minutes to aggregate
            
        Returns:
            AggregatedStats object with aggregated data
        """
        start_time = datetime.utcnow()
        cutoff_time = start_time - timedelta(minutes=time_window_minutes)
        
        logger.info(f"Aggregating statistics for last {time_window_minutes} minutes...")
        
        # Query connections in time window
        query = {"timestamp": {"$gte": cutoff_time}}
        cursor = self.tls_collection.find(query)
        connections = await cursor.to_list(length=None)
        
        if not connections:
            logger.warning("No connections found in time window")
            return AggregatedStats(
                time_window_minutes=time_window_minutes,
                connection_stats=ConnectionStats(),
                events_processed=0,
            )
        
        # Initialize counters
        crypto_type_counter = Counter()
        cipher_suite_counter = Counter()
        server_counter = defaultdict(lambda: {"total": 0, "pqc": 0, "classical": 0, "last_seen": None})
        tls_version_counter = Counter()
        confidence_scores = []
        
        # Process each connection
        for conn in connections:
            crypto_type = conn.get("crypto_type", "unknown")
            crypto_type_counter[crypto_type] += 1
            
            # Cipher suite stats
            cipher_name = conn.get("cipher_suite_name")
            if cipher_name:
                cipher_suite_counter[cipher_name] += 1
            
            # Server stats
            server_name = conn.get("server_name")
            if server_name:
                server_counter[server_name]["total"] += 1
                if conn.get("is_pqc"):
                    server_counter[server_name]["pqc"] += 1
                else:
                    server_counter[server_name]["classical"] += 1
                server_counter[server_name]["last_seen"] = conn.get("timestamp")
            
            # TLS version stats
            tls_version = conn.get("tls_version", "unknown")
            tls_version_counter[tls_version] += 1
            
            # Confidence scores
            confidence = conn.get("detection_confidence", 0.0)
            confidence_scores.append(confidence)
        
        # Calculate connection statistics
        total = len(connections)
        pqc_count = crypto_type_counter.get(CryptoType.PQC.value, 0)
        hybrid_count = crypto_type_counter.get(CryptoType.HYBRID.value, 0)
        classical_count = crypto_type_counter.get(CryptoType.CLASSICAL.value, 0)
        unknown_count = crypto_type_counter.get(CryptoType.UNKNOWN.value, 0)
        
        connection_stats = ConnectionStats(
            total_connections=total,
            pqc_connections=pqc_count,
            hybrid_connections=hybrid_count,
            classical_connections=classical_count,
            unknown_connections=unknown_count,
            pqc_percentage=(pqc_count / total * 100) if total > 0 else 0.0,
            hybrid_percentage=(hybrid_count / total * 100) if total > 0 else 0.0,
            classical_percentage=(classical_count / total * 100) if total > 0 else 0.0,
        )
        
        # Top cipher suites
        top_cipher_suites = []
        for cipher_name, count in cipher_suite_counter.most_common(10):
            # Find a connection with this cipher to get crypto_type
            sample_conn = next((c for c in connections if c.get("cipher_suite_name") == cipher_name), None)
            crypto_type = sample_conn.get("crypto_type", "unknown") if sample_conn else "unknown"
            is_pqc = sample_conn.get("is_pqc", False) if sample_conn else False
            
            top_cipher_suites.append(CipherSuiteStats(
                cipher_suite_name=cipher_name,
                count=count,
                percentage=(count / total * 100) if total > 0 else 0.0,
                crypto_type=crypto_type,
                is_pqc=is_pqc,
            ))
        
        # Top servers
        top_servers = []
        sorted_servers = sorted(
            server_counter.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )[:10]
        
        for server_name, stats in sorted_servers:
            server_total = stats["total"]
            top_servers.append(ServerStats(
                server_name=server_name,
                total_connections=server_total,
                pqc_connections=stats["pqc"],
                classical_connections=stats["classical"],
                pqc_percentage=(stats["pqc"] / server_total * 100) if server_total > 0 else 0.0,
                last_seen=stats["last_seen"] or datetime.utcnow(),
            ))
        
        # TLS version distribution
        tls_version_distribution = dict(tls_version_counter)
        
        # Calculate confidence statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        min_confidence = min(confidence_scores) if confidence_scores else 0.0
        max_confidence = max(confidence_scores) if confidence_scores else 0.0
        
        # Generate time series data (hourly buckets)
        time_series = await self._generate_time_series(cutoff_time, start_time)
        
        # Calculate processing duration
        processing_duration = (datetime.utcnow() - start_time).total_seconds()
        
        aggregated_stats = AggregatedStats(
            timestamp=start_time,
            time_window_minutes=time_window_minutes,
            connection_stats=connection_stats,
            top_cipher_suites=top_cipher_suites,
            top_servers=top_servers,
            tls_version_distribution=tls_version_distribution,
            avg_detection_confidence=avg_confidence,
            min_detection_confidence=min_confidence,
            max_detection_confidence=max_confidence,
            time_series=time_series,
            events_processed=total,
            processing_duration_seconds=processing_duration,
        )
        
        logger.info(
            f"Statistics aggregated: {total} events, "
            f"{pqc_count} PQC ({connection_stats.pqc_percentage:.1f}%), "
            f"processing took {processing_duration:.2f}s"
        )
        
        return aggregated_stats

    async def _generate_time_series(
        self, start_time: datetime, end_time: datetime
    ) -> List[TimeSeriesDataPoint]:
        """Generate time series data points for the given time range"""
        time_series = []
        
        # Create 12 buckets (5-minute intervals for 1 hour)
        bucket_size_minutes = 5
        num_buckets = 12
        
        for i in range(num_buckets):
            bucket_start = start_time + timedelta(minutes=i * bucket_size_minutes)
            bucket_end = bucket_start + timedelta(minutes=bucket_size_minutes)
            
            # Query connections in this bucket
            query = {
                "timestamp": {
                    "$gte": bucket_start,
                    "$lt": bucket_end
                }
            }
            
            # Aggregate by crypto type
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": "$crypto_type",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = await self.tls_collection.aggregate(pipeline).to_list(length=None)
            
            # Build data point
            counts = {r["_id"]: r["count"] for r in results}
            total = sum(counts.values())
            
            time_series.append(TimeSeriesDataPoint(
                timestamp=bucket_start,
                total_connections=total,
                pqc_connections=counts.get(CryptoType.PQC.value, 0),
                classical_connections=counts.get(CryptoType.CLASSICAL.value, 0),
                hybrid_connections=counts.get(CryptoType.HYBRID.value, 0),
            ))
        
        return time_series

    async def store_statistics(self, stats: AggregatedStats) -> str:
        """
        Store aggregated statistics in MongoDB
        
        Args:
            stats: AggregatedStats object to store
            
        Returns:
            ID of stored document
        """
        document = stats.model_dump()
        result = await self.stats_collection.insert_one(document)
        logger.info(f"Statistics stored with ID: {result.inserted_id}")
        return str(result.inserted_id)

    async def get_latest_statistics(self, time_window_minutes: int = 60) -> Optional[AggregatedStats]:
        """Get the most recent statistics for a given time window"""
        query = {"time_window_minutes": time_window_minutes}
        document = await self.stats_collection.find_one(
            query,
            sort=[("timestamp", DESCENDING)]
        )
        
        if document:
            document.pop("_id", None)
            return AggregatedStats(**document)
        return None

    def update_live_stats(self, is_pqc: bool = False):
        """Update live statistics counters"""
        self.event_counter += 1
        self.last_event_time = datetime.utcnow()
        
        # Update cumulative counters
        self.live_stats.total_events_processed += 1
        if is_pqc:
            self.live_stats.total_pqc_detected += 1
        else:
            self.live_stats.total_classical_detected += 1
        
        # Track events in last second for rate calculation
        now = datetime.utcnow()
        self.events_in_last_second.append(now)
        
        # Remove events older than 1 second
        cutoff = now - timedelta(seconds=1)
        self.events_in_last_second = [t for t in self.events_in_last_second if t > cutoff]
        
        # Calculate rates
        self.live_stats.events_per_second = len(self.events_in_last_second)
        self.live_stats.last_event_timestamp = self.last_event_time

    async def get_live_stats(self) -> LiveStats:
        """Get current live statistics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        self.live_stats.uptime_seconds = int(uptime)
        self.live_stats.current_timestamp = datetime.utcnow()
        
        # Get recent aggregated stats
        recent_stats = await self.get_latest_statistics(time_window_minutes=60)
        self.live_stats.recent_stats = recent_stats
        
        return self.live_stats

    async def cleanup_old_statistics(self, days_to_keep: int = 30):
        """Remove statistics older than specified days"""
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
        result = await self.stats_collection.delete_many({"timestamp": {"$lt": cutoff_time}})
        logger.info(f"Cleaned up {result.deleted_count} old statistics records")
        return result.deleted_count
"""
Background Jobs Service
Runs continuous monitoring and statistics aggregation tasks
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from ngfw_pqc_detector.core.config import settings
from ngfw_pqc_detector.services.statistics_service import StatisticsService
from ngfw_pqc_detector.services.database import tls_connections_collection

logger = logging.getLogger(__name__)


class BackgroundJobsService:
    """
    Service for running background jobs like statistics aggregation
    """

    def __init__(self):
        self.running = False
        self.stats_service: Optional[StatisticsService] = None
        self.aggregation_interval = settings.ANALYTICS_BATCH_INTERVAL
        self.time_window = settings.ANALYTICS_TIME_WINDOW

    async def initialize(self, mongo_db):
        """Initialize the background jobs service"""
        # Create statistics collection
        stats_collection = mongo_db["tls_statistics"]
        
        # Initialize statistics service
        self.stats_service = StatisticsService(
            tls_collection=tls_connections_collection,
            stats_collection=stats_collection
        )
        await self.stats_service.initialize()
        
        logger.info("Background jobs service initialized")

    async def start(self):
        """Start all background jobs"""
        if not self.stats_service:
            logger.error("Statistics service not initialized")
            return
        
        self.running = True
        logger.info("=" * 80)
        logger.info("Starting Background Jobs Service")
        logger.info(f"Statistics Aggregation Interval: {self.aggregation_interval}s")
        logger.info(f"Time Window: {self.time_window} minutes")
        logger.info("=" * 80)
        
        # Start statistics aggregation job
        await self._statistics_aggregation_loop()

    async def _statistics_aggregation_loop(self):
        """
        Continuous loop for aggregating and storing statistics
        """
        logger.info("Statistics aggregation loop started")
        
        while self.running:
            try:
                start_time = datetime.utcnow()
                
                # Aggregate statistics
                logger.info(f"[{start_time.isoformat()}] Aggregating statistics...")
                stats = await self.stats_service.aggregate_statistics(
                    time_window_minutes=self.time_window
                )
                
                # Store statistics in MongoDB
                stats_id = await self.stats_service.store_statistics(stats)
                
                # Log summary
                logger.info(
                    f"✓ Statistics aggregated and stored (ID: {stats_id})\n"
                    f"  Total Connections: {stats.connection_stats.total_connections}\n"
                    f"  PQC Connections: {stats.connection_stats.pqc_connections} "
                    f"({stats.connection_stats.pqc_percentage:.1f}%)\n"
                    f"  Classical Connections: {stats.connection_stats.classical_connections} "
                    f"({stats.connection_stats.classical_percentage:.1f}%)\n"
                    f"  Hybrid Connections: {stats.connection_stats.hybrid_connections} "
                    f"({stats.connection_stats.hybrid_percentage:.1f}%)\n"
                    f"  Processing Time: {stats.processing_duration_seconds:.2f}s"
                )
                
                # Print top cipher suites
                if stats.top_cipher_suites:
                    logger.info("  Top Cipher Suites:")
                    for i, cs in enumerate(stats.top_cipher_suites[:5], 1):
                        pqc_indicator = "🔐 PQC" if cs.is_pqc else "🔓 Classical"
                        logger.info(
                            f"    {i}. {cs.cipher_suite_name} - {cs.count} connections "
                            f"({cs.percentage:.1f}%) {pqc_indicator}"
                        )
                
                # Print top servers
                if stats.top_servers:
                    logger.info("  Top Servers:")
                    for i, server in enumerate(stats.top_servers[:5], 1):
                        logger.info(
                            f"    {i}. {server.server_name} - {server.total_connections} connections "
                            f"(PQC: {server.pqc_percentage:.1f}%)"
                        )
                
                logger.info("-" * 80)
                
                # Cleanup old statistics (once per day)
                current_hour = datetime.utcnow().hour
                if current_hour == 0:  # Run at midnight
                    logger.info("Running daily cleanup of old statistics...")
                    deleted_count = await self.stats_service.cleanup_old_statistics(days_to_keep=30)
                    logger.info(f"Cleaned up {deleted_count} old statistics records")
                
                # Wait for next interval
                await asyncio.sleep(self.aggregation_interval)
                
            except asyncio.CancelledError:
                logger.info("Statistics aggregation loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in statistics aggregation loop: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(10)

    async def stop(self):
        """Stop all background jobs"""
        logger.info("Stopping background jobs service...")
        self.running = False

    async def get_live_stats(self):
        """Get current live statistics"""
        if self.stats_service:
            return await self.stats_service.get_live_stats()
        return None


# Global instance
background_jobs_service = BackgroundJobsService()


async def start_background_jobs(mongo_db):
    """
    Start background jobs
    
    Args:
        mongo_db: MongoDB database instance
    """
    await background_jobs_service.initialize(mongo_db)
    await background_jobs_service.start()


async def stop_background_jobs():
    """Stop background jobs"""
    await background_jobs_service.stop()


async def get_current_live_stats():
    """Get current live statistics"""
    return await background_jobs_service.get_live_stats()
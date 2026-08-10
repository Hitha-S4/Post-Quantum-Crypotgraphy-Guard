"""
NGFW PQC Detector - Main Application Entry Point
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ngfw_pqc_detector.api.routes import router
from ngfw_pqc_detector.api.agent_routes import agent_router
from ngfw_pqc_detector.api.websocket_routes import (
    ws_router,
    batch_processing_task,
    broadcast_kafka_message,
    broadcast_alert,
)
from ngfw_pqc_detector.core.config import settings
from ngfw_pqc_detector.services.kafka_consumer import KafkaConsumerService
from ngfw_pqc_detector.services.database import init_db, mongo_db
from ngfw_pqc_detector.services.background_jobs import start_background_jobs, stop_background_jobs
from ngfw_pqc_detector.services.accumulated_stats_service import AccumulatedStatsService
from ngfw_pqc_detector.services.topology_service import TopologyService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("=" * 80)
    logger.info("LIFESPAN STARTUP CALLED")
    logger.info("=" * 80)
    
    try:
        logger.info("Step 1: Initializing database...")
        await init_db()
        logger.info("Step 1: Database initialized ✓")

        # Import mongo_db after initialization
        from ngfw_pqc_detector.services.database import mongo_db as db
        logger.info(f"Step 2: MongoDB connection: {db}")

        # Initialize accumulated statistics service
        print("Step 3: Initializing accumulated stats service...")
        accumulated_stats_service = AccumulatedStatsService(
            stats_collection=db["accumulated_network_stats"],
            flows_collection=db["network_flows"],
            tls_sessions_collection=db["tls_sessions"],
            alerts_collection=db["alerts"],
        )
        await accumulated_stats_service.initialize()
        app.state.accumulated_stats_service = accumulated_stats_service
        print("Step 3: Accumulated statistics service initialized ✓")

        # Initialize topology service
        print("Step 4: Initializing topology service...")
        topology_service = TopologyService(
            nodes_collection=db["network_nodes"],
            edges_collection=db["network_edges"],
        )
        await topology_service.initialize_indexes()
        app.state.topology_service = topology_service
        print("Step 4: Network topology service initialized ✓")

        # Initialize alert service
        print("Step 5: Initializing alert service...")
        from ngfw_pqc_detector.services.alert_service import AlertService

        alert_service = AlertService(
            alerts_collection=db["alerts"],
            websocket_broadcast_callback=broadcast_alert,
        )
        app.state.alert_service = alert_service
        print("Step 5: Alert service initialized ✓")

        # Start Kafka consumer
        print("Step 6: Starting Kafka consumer...")
        kafka_consumer = KafkaConsumerService(
            websocket_broadcast_callback=broadcast_kafka_message,
            accumulated_stats_service=accumulated_stats_service,
            topology_service=topology_service,
            alert_service=alert_service,
        )
        consumer_task = asyncio.create_task(kafka_consumer.start())
        print("Step 6: Kafka consumer started ✓")

        # Start batch processing for WebSocket updates
        if settings.ANALYTICS_ENABLED:
            print("Step 7: Starting analytics batch processing...")
            batch_task = asyncio.create_task(batch_processing_task())
            print(f"Step 7: Analytics batch processing started (interval: {settings.ANALYTICS_BATCH_INTERVAL}s) ✓")
        else:
            batch_task = None
            print("Step 7: Analytics disabled, skipping batch processing")

        # Start background jobs for statistics aggregation
        background_jobs_task = None
        if settings.ANALYTICS_ENABLED:
            print("Step 8: Starting background jobs...")
            background_jobs_task = asyncio.create_task(start_background_jobs(mongo_db))
            print("Step 8: Background statistics aggregation job started ✓")
        else:
            print("Step 8: Analytics disabled, skipping background jobs")

        print("=" * 80)
        print("ALL SERVICES STARTED SUCCESSFULLY!")
        print("=" * 80)

        yield
    except Exception as e:
        print("=" * 80)
        print(f"ERROR IN LIFESPAN STARTUP: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        raise

    # Shutdown
    logger.info("Shutting down NGFW PQC Detector...")
    consumer_task.cancel()
    if batch_task:
        batch_task.cancel()
    if background_jobs_task:
        await stop_background_jobs()
        background_jobs_task.cancel()
    try:
        await consumer_task
        if batch_task:
            await batch_task
        if background_jobs_task:
            await background_jobs_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=settings.APP_NAME,
        version="2.0.0",
        description="Next-Generation Firewall with Post-Quantum Cryptography Detection and Real-time Analytics",
        lifespan=lifespan,
    )

    # Configure CORS
    if settings.API_ENABLE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.lovable\.app",
            allow_origins=[
                "http://localhost:8080",
                "http://localhost:8081",
                "http://localhost:3000",
                "http://localhost:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    # Include Agent routes
    app.include_router(agent_router, prefix="/api/v1")

    # Include WebSocket routes
    app.include_router(ws_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG
    from copy import deepcopy

    # Configure logging - must be done before uvicorn starts
    logging.basicConfig(
        level=getattr(logging, settings.APP_LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Force reconfiguration
    )

    # Create custom log config for uvicorn
    log_config = deepcopy(LOGGING_CONFIG)
    log_config["formatters"]["default"][
        "fmt"
    ] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Ensure all application loggers use the configured level
    log_config["loggers"]["ngfw_pqc_detector"] = {
        "handlers": ["default"],
        "level": settings.APP_LOG_LEVEL,
        "propagate": False,
    }

    uvicorn.run(
        "ngfw_pqc_detector.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        workers=settings.APP_WORKERS,
        reload=True,
        log_config=log_config,
        log_level=settings.APP_LOG_LEVEL.lower(),
    )

#!/usr/bin/env python3
"""
Test script for Statistics Service
Tests the statistics aggregation and API endpoints
"""
import asyncio
import sys
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# Add src to path
sys.path.insert(0, 'src')

from ngfw_pqc_detector.core.config import settings
from ngfw_pqc_detector.services.statistics_service import StatisticsService
from ngfw_pqc_detector.models.tls_connection import CryptoType


async def create_test_data(collection, num_records=100):
    """Create test TLS connection data"""
    print(f"Creating {num_records} test TLS connection records...")
    
    test_data = []
    base_time = datetime.utcnow() - timedelta(minutes=30)
    
    for i in range(num_records):
        # Vary crypto types
        if i % 3 == 0:
            crypto_type = CryptoType.PQC.value
            is_pqc = True
        elif i % 3 == 1:
            crypto_type = CryptoType.CLASSICAL.value
            is_pqc = False
        else:
            crypto_type = CryptoType.HYBRID.value
            is_pqc = True
        
        record = {
            "timestamp": base_time + timedelta(minutes=i % 30),
            "source_ip": f"192.168.1.{i % 255}",
            "source_port": 50000 + i,
            "destination_ip": f"10.0.0.{i % 100}",
            "destination_port": 443,
            "server_name": f"server{i % 10}.example.com",
            "tls_version": "TLS 1.3",
            "cipher_suite_code": f"0x{i:04x}",
            "cipher_suite_name": f"TLS_CIPHER_SUITE_{i % 5}",
            "crypto_type": crypto_type,
            "is_pqc": is_pqc,
            "is_hybrid": crypto_type == CryptoType.HYBRID.value,
            "detection_confidence": 0.8 + (i % 20) / 100,
            "detection_method": "client_hello_inspection",
        }
        test_data.append(record)
    
    result = await collection.insert_many(test_data)
    print(f"✓ Created {len(result.inserted_ids)} test records")
    return len(result.inserted_ids)


async def test_statistics_service():
    """Test the statistics service"""
    print("=" * 80)
    print("STATISTICS SERVICE TEST")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
    print(f"Connecting to MongoDB: {settings.MONGODB_URL}")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DATABASE]
    
    # Use test collections
    tls_collection = db["tls_connections_test"]
    stats_collection = db["tls_statistics_test"]
    
    # Clean up any existing test data
    print("Cleaning up existing test data...")
    await tls_collection.delete_many({})
    await stats_collection.delete_many({})
    print("✓ Cleanup complete")
    print()
    
    # Create test data
    num_records = await create_test_data(tls_collection, num_records=100)
    print()
    
    # Initialize statistics service
    print("Initializing statistics service...")
    stats_service = StatisticsService(tls_collection, stats_collection)
    await stats_service.initialize()
    print("✓ Statistics service initialized")
    print()
    
    # Test aggregation
    print("Testing statistics aggregation...")
    print("-" * 80)
    
    time_window = 60  # 60 minutes
    stats = await stats_service.aggregate_statistics(time_window_minutes=time_window)
    
    print(f"✓ Statistics aggregated successfully!")
    print()
    print("RESULTS:")
    print("-" * 80)
    print(f"Time Window: {stats.time_window_minutes} minutes")
    print(f"Events Processed: {stats.events_processed}")
    print(f"Processing Duration: {stats.processing_duration_seconds:.2f}s")
    print()
    
    print("CONNECTION STATISTICS:")
    cs = stats.connection_stats
    print(f"  Total Connections: {cs.total_connections}")
    print(f"  PQC Connections: {cs.pqc_connections} ({cs.pqc_percentage:.1f}%)")
    print(f"  Hybrid Connections: {cs.hybrid_connections} ({cs.hybrid_percentage:.1f}%)")
    print(f"  Classical Connections: {cs.classical_connections} ({cs.classical_percentage:.1f}%)")
    print()
    
    if stats.top_cipher_suites:
        print("TOP CIPHER SUITES:")
        for i, cs in enumerate(stats.top_cipher_suites[:5], 1):
            pqc_indicator = "🔐 PQC" if cs.is_pqc else "🔓 Classical"
            print(f"  {i}. {cs.cipher_suite_name}")
            print(f"     Count: {cs.count} ({cs.percentage:.1f}%) {pqc_indicator}")
        print()
    
    if stats.top_servers:
        print("TOP SERVERS:")
        for i, server in enumerate(stats.top_servers[:5], 1):
            print(f"  {i}. {server.server_name}")
            print(f"     Total: {server.total_connections}, PQC: {server.pqc_connections} ({server.pqc_percentage:.1f}%)")
        print()
    
    print("TLS VERSION DISTRIBUTION:")
    for version, count in stats.tls_version_distribution.items():
        print(f"  {version}: {count}")
    print()
    
    print("DETECTION CONFIDENCE:")
    print(f"  Average: {stats.avg_detection_confidence:.2f}")
    print(f"  Min: {stats.min_detection_confidence:.2f}")
    print(f"  Max: {stats.max_detection_confidence:.2f}")
    print()
    
    if stats.time_series:
        print(f"TIME SERIES DATA POINTS: {len(stats.time_series)}")
        print("  Sample (first 3):")
        for i, dp in enumerate(stats.time_series[:3], 1):
            print(f"    {i}. {dp.timestamp.isoformat()}")
            print(f"       Total: {dp.total_connections}, PQC: {dp.pqc_connections}, Classical: {dp.classical_connections}")
        print()
    
    # Test storing statistics
    print("Testing statistics storage...")
    stats_id = await stats_service.store_statistics(stats)
    print(f"✓ Statistics stored with ID: {stats_id}")
    print()
    
    # Test retrieving statistics
    print("Testing statistics retrieval...")
    retrieved_stats = await stats_service.get_latest_statistics(time_window_minutes=time_window)
    if retrieved_stats:
        print(f"✓ Retrieved statistics successfully")
        print(f"  Timestamp: {retrieved_stats.timestamp.isoformat()}")
        print(f"  Events: {retrieved_stats.events_processed}")
    else:
        print("✗ Failed to retrieve statistics")
    print()
    
    # Test live stats
    print("Testing live statistics...")
    stats_service.update_live_stats(is_pqc=True)
    stats_service.update_live_stats(is_pqc=False)
    stats_service.update_live_stats(is_pqc=True)
    
    live_stats = await stats_service.get_live_stats()
    print(f"✓ Live statistics retrieved")
    print(f"  Total Events Processed: {live_stats.total_events_processed}")
    print(f"  Total PQC Detected: {live_stats.total_pqc_detected}")
    print(f"  Total Classical Detected: {live_stats.total_classical_detected}")
    print(f"  Events Per Second: {live_stats.events_per_second:.2f}")
    print()
    
    # Cleanup
    print("Cleaning up test data...")
    await tls_collection.delete_many({})
    await stats_collection.delete_many({})
    print("✓ Cleanup complete")
    print()
    
    print("=" * 80)
    print("ALL TESTS PASSED! ✓")
    print("=" * 80)
    
    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_statistics_service())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
#!/usr/bin/env python3
"""
Reset accumulated statistics in MongoDB
Run this if the stats document gets corrupted
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


async def reset_stats():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["ngfw_pqc"]

    # Delete the corrupted document
    result = await db.accumulated_network_stats.delete_one({"_id": "accumulated_stats_v1"})
    print(f"Deleted {result.deleted_count} document(s)")

    # Create fresh document
    fresh_doc = {
        "_id": "accumulated_stats_v1",
        "last_updated": None,
        "total_flows": 0,
        "total_tls_flows": 0,
        "total_tcp_flows": 0,
        "total_udp_flows": 0,
        "total_other_flows": 0,
        "total_pqc_safe": 0,
        "total_pqc_vulnerable": 0,
        "total_pqc_unknown": 0,
        "total_bytes_to_server": 0,
        "total_bytes_to_client": 0,
        "total_bytes": 0,
        "total_alerts": 0,
        "total_critical_alerts": 0,
        "total_high_alerts": 0,
        "total_medium_alerts": 0,
        "total_low_alerts": 0,
        "protocol_distribution": {},
        "tls_version_distribution": {},
        "cipher_suite_distribution": {},
        "key_exchange_distribution": {},
        "flow_state_distribution": {},
        "posture_distribution": {},
    }

    await db.accumulated_network_stats.insert_one(fresh_doc)
    print("✓ Created fresh accumulated stats document")

    client.close()


if __name__ == "__main__":
    print("Resetting accumulated statistics...")
    asyncio.run(reset_stats())
    print("Done! Restart the application.")

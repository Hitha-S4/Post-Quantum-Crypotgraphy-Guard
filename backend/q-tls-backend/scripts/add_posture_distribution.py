#!/usr/bin/env python3
"""
Add posture_distribution field to existing accumulated stats document
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


async def add_posture_field():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["ngfw_pqc"]

    # Update the document to add posture_distribution if it doesn't exist
    result = await db.accumulated_network_stats.update_one(
        {"_id": "accumulated_stats_v1"}, {"$set": {"posture_distribution": {}}}
    )

    if result.matched_count > 0:
        print(
            f"✓ Updated document (matched: {result.matched_count}, modified: {result.modified_count})"
        )
        print("✓ Added posture_distribution field")
    else:
        print("✗ Document not found")

    client.close()


if __name__ == "__main__":
    print("Adding posture_distribution field to accumulated stats...")
    asyncio.run(add_posture_field())
    print("Done! The field will populate as new TLS events are processed.")

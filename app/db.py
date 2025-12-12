import os
import re

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MASTER_DB_NAME = os.getenv("MASTER_DB_NAME", "master_db")

_client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def get_master_db() -> AsyncIOMotorDatabase:
    return get_client()[MASTER_DB_NAME]


def sanitize_org_name(name: str) -> str:
    # Lowercase, keep alphanumerics and underscores
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    return f"org_{name}"


async def ensure_org_collection(db: AsyncIOMotorDatabase, collection_name: str):
    existing = await db.list_collection_names()
    if collection_name not in existing:
        await db.create_collection(collection_name)

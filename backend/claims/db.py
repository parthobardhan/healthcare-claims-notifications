import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_mongo_uri() -> str:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("MONGODB_URI environment variable is required")
    return uri


def get_db_name() -> str:
    name = os.getenv("CLAIMS_DB_NAME") or os.getenv("DB_NAME")
    if not name:
        raise ValueError("CLAIMS_DB_NAME environment variable is required")
    return name


async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(
            get_mongo_uri(),
            maxPoolSize=1,
            minPoolSize=0,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        _db = _client[get_db_name()]
    return _db


async def close_db():
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None

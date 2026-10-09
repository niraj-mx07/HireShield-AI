"""MongoDB async connection management via Motor.

Provides a singleton ``AsyncIOMotorClient`` and a ``get_database`` helper
that can be used as a FastAPI dependency.
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

# Module-level references — initialised by ``connect()`` at app startup.
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect() -> None:
    """Create the Motor client and select the database.

    Call this during FastAPI's lifespan *startup* phase.
    """
    global _client, _database
    settings = get_settings()
    import certifi

    client_kwargs = {
        "serverSelectionTimeoutMS": 5000,
        "connectTimeoutMS": 5000,
        "socketTimeoutMS": 5000,
    }
    # Enable certifi CA bundle for Atlas SRV / TLS connections on Windows
    if "mongodb+srv" in settings.database_url or "ssl=true" in settings.database_url.lower() or "tls=true" in settings.database_url.lower():
        client_kwargs["tlsCAFile"] = certifi.where()

    _client = AsyncIOMotorClient(
        settings.database_url,
        **client_kwargs,
    )
    _database = _client[settings.database_name]


async def disconnect() -> None:
    """Close the Motor client.

    Call this during FastAPI's lifespan *shutdown* phase.
    """
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the current database handle.

    Raises:
        RuntimeError: If called before ``connect()`` has been awaited.
    """
    if _database is None:
        raise RuntimeError(
            "Database not initialised. Ensure connect() is called at startup."
        )
    return _database

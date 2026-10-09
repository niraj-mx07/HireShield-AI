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

    The connection is lazy and must never crash startup: when MongoDB is
    unreachable (wrong credentials, network block, local mongod stopped)
    we keep the client handle and log a warning.  The assessment pipeline
    treats every DB write as best-effort so scans still return reports.
    """
    global _client, _database
    import logging

    _logger = logging.getLogger(__name__)
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.database_url, serverSelectionTimeoutMS=3000)
    _database = _client[settings.database_name]
    try:
        await _client.admin.command("ping")
    except Exception as exc:
        _logger.warning(
            "MongoDB ping failed (%s) — assessments will run without persistence. "
            "Fix DATABASE_URL in backend/.env (local default: mongodb://localhost:27017).",
            exc,
        )


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

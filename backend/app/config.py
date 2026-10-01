"""Centralised application settings loaded from environment variables.

Uses pydantic-settings to read from a .env file (or real env vars) and
expose typed, validated configuration to the rest of the application.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Values are read from environment variables or a ``.env`` file located
    in the ``backend/`` directory.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Database ---
    database_url: str = "mongodb://localhost:27017"
    database_name: str = "hireshield"

    # --- Application ---
    secret_key: str = "change-me-to-a-random-secret"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Logging ---
    log_level: str = "INFO"

    # --- Verification provider keys (optional) ---
    google_safe_browsing_api_key: str = ""
    whois_api_key: str = ""
    linkedin_api_key: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Using ``lru_cache`` ensures the ``.env`` file is read only once.
    """
    return Settings()

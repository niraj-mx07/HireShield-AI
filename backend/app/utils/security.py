"""Security and authentication utilities for HireShield-AI.

Provides standard RFC-7519 compliant JSON Web Token (JWT) generation and verification,
password hashing with legacy compatibility, and authentication middleware helpers.
Pure Python with zero external C-dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _b64url_encode(data: bytes) -> str:
    """Encode bytes using URL-safe Base64 without trailing '=' padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    """Decode URL-safe Base64 string with automatic padding restoration."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with project secret salting."""
    settings = get_settings()
    salt = settings.secret_key[:16]
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash, supporting both salted and legacy SHA-256 hashes."""
    if not password or not stored_hash:
        return False

    # Check salted hash
    if hash_password(password) == stored_hash:
        return True

    # Check legacy raw SHA-256 hash (backward compatibility)
    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if legacy_hash == stored_hash:
        return True

    return False


def create_access_token(
    payload: Dict[str, Any],
    expires_in_seconds: int = 86400 * 7,  # 7 days
) -> str:
    """Create a signed RFC 7519 HS256 JWT access token.

    Args:
        payload: Dictionary of claims (e.g. sub, email, role).
        expires_in_seconds: Token lifetime in seconds (default: 7 days).

    Returns:
        Encoded signed JWT string (header.payload.signature).
    """
    settings = get_settings()
    secret = settings.secret_key.encode("utf-8")

    now = int(time.time())
    claims = {
        **payload,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header = {"alg": "HS256", "typ": "JWT"}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed HS256 JWT access token.

    Returns the claims dictionary if valid and non-expired; otherwise None.
    """
    if not token or token.count(".") != 2:
        return None

    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        settings = get_settings()
        secret = settings.secret_key.encode("utf-8")

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            logger.warning("JWT signature verification failed.")
            return None

        # Verify expiration
        payload_bytes = _b64url_decode(payload_b64)
        claims = json.loads(payload_bytes.decode("utf-8"))

        exp = claims.get("exp")
        if exp and int(time.time()) > exp:
            logger.info("JWT token has expired.")
            return None

        return claims
    except Exception as exc:
        logger.debug("Failed to decode token: %s", exc)
        return None

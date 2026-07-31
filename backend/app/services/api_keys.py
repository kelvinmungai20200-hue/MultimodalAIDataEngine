import os
import hashlib
import hmac
import secrets
from typing import Tuple

# Simple API key generation and hashing utilities.
# Note: For production, consider using a stronger KDF (bcrypt/argon2) and secure key storage.

HASH_ALGO = "sha256"


def generate_api_key(name: str | None = None) -> Tuple[str, str]:
    """Generate a new API key and return (plaintext, hashed).

    The hashed value is HMAC-SHA256 with a server-side pepper (ADMIN_API_PEPPER env var) if present.
    """
    plaintext = secrets.token_urlsafe(32)
    pepper = os.environ.get("ADMIN_API_PEPPER", "")
    hashed = _hash_key(plaintext, pepper)
    return plaintext, hashed


def _hash_key(key: str, pepper: str = "") -> str:
    # Use HMAC with a pepper to avoid rainbow table attacks. Not a replacement for bcrypt.
    if pepper:
        dig = hmac.new(pepper.encode("utf-8"), key.encode("utf-8"), hashlib.sha256).hexdigest()
    else:
        dig = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return dig


def verify_key(plaintext: str, stored_hash: str, pepper: str = "") -> bool:
    return hmac.compare_digest(_hash_key(plaintext, pepper), stored_hash)

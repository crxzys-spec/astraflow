"""Password hashing helpers for hub accounts."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, *, iterations: int = 120_000) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algorithm, iterations, salt, digest_hex = hashed.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations_int = int(iterations)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations_int,
    )
    return hmac.compare_digest(candidate.hex(), digest_hex)

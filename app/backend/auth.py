from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from dataclasses import dataclass

from app.backend.sqlite_store import get_conn, init_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERATIONS = 260_000


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    name: str
    email: str


class AuthError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_registration(name: str, email: str, password: str) -> tuple[str, str]:
    clean_name = name.strip()
    clean_email = normalize_email(email)

    if not clean_name:
        raise AuthError("Name is required.")
    if not EMAIL_RE.match(clean_email):
        raise AuthError("Enter a valid email address.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")

    return clean_name, clean_email


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(actual, expected)


def create_user(name: str, email: str, password: str) -> AuthUser:
    init_db()
    clean_name, clean_email = validate_registration(name, email, password)
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)

    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users(user_id, name, email, password_hash, profile_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, clean_name, clean_email, password_hash, "{}"),
            )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise AuthError("An account with this email already exists.") from exc
        raise

    return AuthUser(user_id=user_id, name=clean_name, email=clean_email)


def authenticate_user(email: str, password: str) -> AuthUser | None:
    init_db()
    clean_email = normalize_email(email)

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT user_id, name, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (clean_email,),
        ).fetchone()

    if row is None or not row["password_hash"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None

    return AuthUser(
        user_id=row["user_id"],
        name=row["name"] or row["email"],
        email=row["email"],
    )


def get_user(user_id: str) -> AuthUser | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id, name, email FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return AuthUser(
        user_id=row["user_id"],
        name=row["name"] or row["email"],
        email=row["email"],
    )

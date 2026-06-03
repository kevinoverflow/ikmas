from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.backend.sqlite_store import get_conn, init_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERATIONS = 260_000
REMEMBER_ME_TTL_DAYS = 30


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


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_dt(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


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


def create_auth_session(user_id: str, ttl_days: int = REMEMBER_ME_TTL_DAYS) -> str:
    init_db()
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(raw_token)
    now = _utc_now()
    expires_at = now + timedelta(days=ttl_days)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions(token_hash, user_id, created_at, expires_at, last_used_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                token_hash,
                user_id,
                _format_dt(now),
                _format_dt(expires_at),
                _format_dt(now),
            ),
        )

    return raw_token


def authenticate_session_token(raw_token: str | None) -> AuthUser | None:
    if not raw_token:
        return None

    init_db()
    token_hash = hash_session_token(raw_token)

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT s.expires_at, s.revoked_at, u.user_id, u.name, u.email
            FROM auth_sessions s
            JOIN users u ON u.user_id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if row is None or row["revoked_at"]:
            return None

        if _parse_dt(row["expires_at"]) <= _utc_now():
            conn.execute(
                "UPDATE auth_sessions SET revoked_at = ? WHERE token_hash = ?",
                (_format_dt(_utc_now()), token_hash),
            )
            return None

        conn.execute(
            "UPDATE auth_sessions SET last_used_at = ? WHERE token_hash = ?",
            (_format_dt(_utc_now()), token_hash),
        )

    return AuthUser(
        user_id=row["user_id"],
        name=row["name"] or row["email"],
        email=row["email"],
    )


def revoke_auth_session(raw_token: str | None) -> None:
    if not raw_token:
        return

    init_db()
    token_hash = hash_session_token(raw_token)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE token_hash = ?
            """,
            (_format_dt(_utc_now()), token_hash),
        )

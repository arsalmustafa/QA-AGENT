from datetime import datetime, timedelta, timezone

import jwt

from auth.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_REFRESH_EXPIRE_DAYS,
    JWT_SECRET,
)

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _require_secret() -> None:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is missing. Add it to your .env file.")


def create_access_token(payload: dict) -> str:
    _require_secret()
    data = dict(payload)
    data["token_type"] = TOKEN_TYPE_ACCESS
    data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(payload: dict) -> str:
    _require_secret()
    data = dict(payload)
    data["token_type"] = TOKEN_TYPE_REFRESH
    data["exp"] = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_EXPIRE_DAYS)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_token_pair(payload: dict) -> tuple[str, str]:
    """Return (access_token, refresh_token) for the same user claims."""
    claims = {
        "sub": payload["sub"],
        "login": payload.get("login"),
        "name": payload.get("name"),
        "avatar_url": payload.get("avatar_url"),
        "github_token": payload.get("github_token"),
    }
    return create_access_token(claims), create_refresh_token(claims)


def decode_access_token(token: str) -> dict:
    _require_secret()
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def decode_refresh_token(token: str) -> dict:
    _require_secret()
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("token_type") != TOKEN_TYPE_REFRESH:
        raise jwt.InvalidTokenError("Not a refresh token")
    return payload

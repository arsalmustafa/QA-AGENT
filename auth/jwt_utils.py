from datetime import datetime, timedelta, timezone

import jwt

from auth.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET


def create_access_token(payload: dict) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is missing. Add it to your .env file.")

    data = dict(payload)
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    data["exp"] = expire
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is missing. Add it to your .env file.")

    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

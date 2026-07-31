import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from auth.config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_REDIRECT_URI,
    github_oauth_configured,
)
from auth.deps import get_current_user
from auth.jwt_utils import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# Simple in-memory state store for CSRF protection (fine for local/dev)
_pending_states: set[str] = set()


def _require_oauth_config() -> None:
    if not github_oauth_configured():
        raise HTTPException(
            status_code=500,
            detail=(
                "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID, "
                "GITHUB_CLIENT_SECRET, and JWT_SECRET in .env"
            ),
        )


@router.get("/github")
def github_login():
    """Redirect the user to GitHub to authorize the app."""
    _require_oauth_config()

    state = secrets.token_urlsafe(24)
    _pending_states.add(state)

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email repo",
        "state": state,
    }
    return RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/github/callback")
async def github_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    """
    GitHub redirects here after login.
    Exchange code → access_token → user → JWT.
    """
    _require_oauth_config()

    if error:
        raise HTTPException(
            status_code=400,
            detail=error_description or error,
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    _pending_states.discard(state)

    async with httpx.AsyncClient(timeout=30.0) as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=token_data.get("error_description")
                or "Failed to get GitHub access token",
            )

        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        user_response.raise_for_status()
        user = user_response.json()

    jwt_token = create_access_token(
        {
            "sub": str(user.get("id")),
            "login": user.get("login"),
            "name": user.get("name") or user.get("login"),
            "avatar_url": user.get("avatar_url"),
            "github_token": access_token,
        }
    )

    return {
        "message": "GitHub login successful",
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.get("id"),
            "login": user.get("login"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
        },
    }


@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)):
    """Return the current authenticated user."""
    return user

import secrets
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from auth.config import (
    FRONTEND_URL,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_REDIRECT_URI,
    github_oauth_configured,
)
from auth.deps import get_current_user
from auth.jwt_utils import create_token_pair, decode_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# Simple in-memory state store for CSRF protection (fine for local/dev)
_pending_states: set[str] = set()


class RefreshRequest(BaseModel):
    refresh_token: str


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
    """Redirect the user to GitHub to authorize the app (browser)."""
    _require_oauth_config()
    authorize_url, _state = _build_authorize_url()
    return RedirectResponse(authorize_url)


@router.get("/github/start")
def github_login_start():
    """
    Postman-friendly OAuth start (no redirect).
    Returns authorize_url + state. Open authorize_url in a browser,
    then call /auth/github/callback with code & state (or copy token from browser JSON).
    """
    _require_oauth_config()
    authorize_url, state = _build_authorize_url()
    return {
        "message": "Open authorize_url in your browser to continue GitHub login",
        "authorize_url": authorize_url,
        "state": state,
        "callback_hint": (
            f"{GITHUB_REDIRECT_URI}?code=FROM_REDIRECT&state={state}&format=json"
        ),
        "next_steps": [
            "1. Open authorize_url in a browser and approve the app",
            "2. Browser login redirects to the React app with ?token= & refresh_token=",
            "3. For Postman: call callback with format=json and copy access_token",
            "4. SPA auto-refreshes via POST /auth/refresh before access token expires",
        ],
    }


def _build_authorize_url() -> tuple[str, str]:
    state = secrets.token_urlsafe(24)
    _pending_states.add(state)
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email repo",
        "state": state,
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}", state


@router.get("/github/callback")
async def github_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    format: str | None = Query(default=None),
):
    """
    GitHub redirects here after login.
    Exchange code → access_token → user → JWT pair.
    By default redirects to the React app with ?token=&refresh_token=.
    Pass format=json for Postman / API clients.
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

    jwt_access, jwt_refresh = create_token_pair(
        {
            "sub": str(user.get("id")),
            "login": user.get("login"),
            "name": user.get("name") or user.get("login"),
            "avatar_url": user.get("avatar_url"),
            "github_token": access_token,
        }
    )

    payload = {
        "message": "GitHub login successful",
        "access_token": jwt_access,
        "refresh_token": jwt_refresh,
        "token_type": "bearer",
        "user": {
            "id": user.get("id"),
            "login": user.get("login"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
        },
    }

    if (format or "").lower() == "json":
        return payload

    redirect = (
        f"{FRONTEND_URL}/auth/callback?"
        f"{urlencode({'token': jwt_access, 'refresh_token': jwt_refresh})}"
    )
    return RedirectResponse(url=redirect, status_code=302)


@router.post("/refresh")
def refresh_tokens(body: RefreshRequest):
    """
    Exchange a valid refresh token for a new access + refresh pair.
    Called automatically by the SPA before the access token expires.
    """
    _require_oauth_config()
    try:
        payload = decode_refresh_token(body.refresh_token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Refresh token expired. Login again via GET /auth/github",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    access, refresh = create_token_pair(
        {
            "sub": str(payload.get("sub")),
            "login": payload.get("login"),
            "name": payload.get("name"),
            "avatar_url": payload.get("avatar_url"),
            "github_token": payload.get("github_token"),
        }
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)):
    """Return the current authenticated user (no GitHub token)."""
    return {
        "id": user.get("id"),
        "login": user.get("login"),
        "name": user.get("name"),
        "avatar_url": user.get("avatar_url"),
    }

"""Authentication endpoints for chat service."""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from slack_sdk import WebClient as SlackSDKWebClient
from slack_sdk.errors import SlackApiError

from slack_impl.token_store import SQLiteTokenStore, TokenBundle

logger = logging.getLogger(__name__)


def _is_https_enabled() -> bool:
    """Check if HTTPS is enabled by looking for SSL certificates."""
    cert_path = Path("/app/certs/server.crt")
    key_path = Path("/app/certs/server.key")
    return cert_path.exists() and key_path.exists()


def _get_redirect_uri(request: Request) -> str:
    """Get the OAuth redirect URI, ensuring it uses HTTPS if SSL is enabled."""
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI")
    
    # If HTTPS is enabled (SSL certs exist), ensure redirect URI uses HTTPS and correct port
    if _is_https_enabled():
        if redirect_uri:
            # Replace http:// with https://
            if redirect_uri.startswith("http://"):
                redirect_uri = redirect_uri.replace("http://", "https://", 1)
            # Fix port if it's 8000 (should be 8080)
            if ":8000" in redirect_uri:
                redirect_uri = redirect_uri.replace(":8000", ":8080", 1)
            logger.info("Forcing HTTPS in redirect URI: %s", redirect_uri)
        else:
            # Construct from request with HTTPS
            scheme = "https"
            hostname = request.url.hostname or "localhost"
            # Use port 8080 (the actual service port) instead of request port
            port = 8080
            redirect_uri = f"{scheme}://{hostname}:{port}/auth/callback"
            logger.info("Constructed HTTPS redirect URI from request: %s", redirect_uri)
    elif not redirect_uri:
        # Construct from request URL
        scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
        hostname = request.url.hostname or "localhost"
        port = request.url.port or 8080
        redirect_uri = f"{scheme}://{hostname}:{port}/auth/callback"
        logger.info("Constructed redirect URI from request: %s", redirect_uri)
    
    if not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="OAUTH_REDIRECT_URI not set and could not be determined from request"
        )
    
    return redirect_uri

router = APIRouter(prefix="/auth", tags=["auth"])

# Token store initialization
_DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./var/chat_tokens.db")
if _DB_PATH.startswith("sqlite:///"):
    _DB_PATH = _DB_PATH.replace("sqlite:///", "", 1)
Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

_store: SQLiteTokenStore | None = None


def _get_store() -> SQLiteTokenStore:
    """Return the process-wide SQLiteTokenStore."""
    global _store
    if _store is None:
        _store = SQLiteTokenStore(_DB_PATH)
    return _store


def _require_oauth_env() -> None:
    """Check that required OAuth environment variables are set.
    
    Note: OAUTH_REDIRECT_URI is optional if it can be constructed from the request.
    """
    for k in ("OAUTH_CLIENT_ID", "OAUTH_CLIENT_SECRET"):
        if not os.environ.get(k):
            raise HTTPException(status_code=500, detail=f"Missing env: {k}")


# State management for OAuth security
def _sign(msg: str, key: str) -> str:
    """Sign a message with HMAC."""
    mac = hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode("utf-8").rstrip("=")


def _make_state(secret: str, ttl_sec: int = 600) -> str:
    """Create a signed state token for OAuth."""
    raw = f"{secrets.token_urlsafe(24)}.{int(time.time())}"
    sig = _sign(raw, secret)
    return f"{raw}.{sig}"


def _check_state(state: str, secret: str, ttl_sec: int = 600) -> bool:
    """Verify and check expiration of OAuth state token."""
    try:
        token, ts_str, sig = state.rsplit(".", 2)
        expected = _sign(f"{token}.{ts_str}", secret)
        if not hmac.compare_digest(expected, sig):
            return False
        ts = int(ts_str)
        return (time.time() - ts) <= ttl_sec
    except Exception:
        return False


# OAuth scopes
_USER_SCOPES = ",".join(
    [
        "channels:read",
        "groups:read",
        "users:read",
        "chat:write",
        "channels:history",
        "groups:history",
        "im:history",
        "mpim:history",
    ]
)

_BOT_SCOPES = ",".join(
    [
        "channels:manage",
        "groups:write",
        "chat:write",
        "users:read",
        "channels:read",
        "groups:read",
        "channels:join",
        "channels:history",
        "groups:history",
        "mpim:history",
        "im:history",
    ]
)


def _build_slack_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    user_scope_csv: str,
    bot_scope_csv: str,
) -> str:
    """Construct Slack OAuth v2 authorize URL requesting both user and bot tokens."""
    base = "https://slack.com/oauth/v2/authorize"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "user_scope": user_scope_csv,
        "scope": bot_scope_csv,
    }
    return f"{base}?{urllib.parse.urlencode(params)}"


class LoginRequest(BaseModel):
    """Request model for login (kept for backward compatibility)."""

    user_id: str


@router.get("/login", tags=["auth"])
def login(request: Request) -> RedirectResponse:
    """Redirect to Slack OAuth login page.

    This endpoint redirects users to Slack's OAuth authorization page.
    After authorization, Slack will redirect back to /auth/callback.
    """
    _require_oauth_env()
    secret = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    state = _make_state(secret)
    redirect_uri = _get_redirect_uri(request)
    
    url = _build_slack_authorize_url(
        client_id=os.environ["OAUTH_CLIENT_ID"],
        redirect_uri=redirect_uri,
        state=state,
        user_scope_csv=_USER_SCOPES,
        bot_scope_csv=_BOT_SCOPES,
    )
    logger.info("OAuth login redirect URI: %s", redirect_uri)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/callback", tags=["auth"])
def callback(
    request: Request,
    code: str,
    state: str,
    store: SQLiteTokenStore = Depends(_get_store),
) -> RedirectResponse:
    """Handle Slack OAuth callback.

    This endpoint is called by Slack after the user authorizes the app.
    It exchanges the authorization code for tokens and stores them.
    """
    secret = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    if not _check_state(state, secret):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    _require_oauth_env()
    client_id = os.environ["OAUTH_CLIENT_ID"]
    client_secret = os.environ["OAUTH_CLIENT_SECRET"]
    redirect_uri = _get_redirect_uri(request)

    try:
        # Exchange code for tokens
        oauth_client = SlackSDKWebClient(token=None)
        data = oauth_client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        ).data
    except SlackApiError as exc:
        logger.exception("OAuth exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail="OAuth exchange failed") from exc

    authed = data.get("authed_user") or {}
    user_id = authed.get("id") or data.get("user_id")
    user_access_token = authed.get("access_token")
    user_refresh_token = authed.get("refresh_token")
    user_scope = authed.get("scope")

    # Bot token (app-level)
    bot_access_token = data.get("access_token")
    bot_scope = data.get("scope")
    token_type = str(data.get("token_type", "Bearer"))

    # Expiration (if present)
    expires_at: float | None = None
    if isinstance(data.get("expires_in"), int):
        expires_at = time.time() + int(data["expires_in"])

    if not user_id or not user_access_token:
        logger.error("OAuth exchange missing user fields: %s", data)
        raise HTTPException(status_code=400, detail="Token exchange failed")

    # Persist user token
    store.save(
        str(user_id),
        TokenBundle(
            access_token=str(user_access_token),
            refresh_token=str(user_refresh_token) if user_refresh_token else None,
            token_type=token_type,
            scope=str(user_scope) if user_scope else None,
            expires_at=float(expires_at) if expires_at else None,
        ),
    )

    # Persist bot token
    if bot_access_token:
        store.save(
            f"bot:{user_id}",
            TokenBundle(
                access_token=str(bot_access_token),
                refresh_token=None,
                token_type=token_type,
                scope=str(bot_scope) if bot_scope else None,
                expires_at=float(expires_at) if expires_at else None,
            ),
        )

    # Set session
    request.session["user_id"] = str(user_id)
    if user_scope:
        request.session["scope"] = str(user_scope)

    logger.info("User %s authenticated via Slack OAuth", user_id)
    return RedirectResponse("/docs", status_code=status.HTTP_302_FOUND)


@router.post("/login", status_code=200)
def login_legacy(request: Request, login_data: LoginRequest) -> dict[str, str]:
    """Legacy login endpoint (kept for backward compatibility).

    This is a simple authentication endpoint for development/testing.
    For production, use GET /auth/login to redirect to Slack OAuth.

    Args:
        request: FastAPI request object.
        login_data: Login request with user_id.

    Returns:
        Success message with user_id.

    """
    user_id = login_data.user_id.strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id cannot be empty",
        )

    # Set user_id in session
    request.session["user_id"] = user_id
    logger.info("User %s logged in (session-based)", user_id)

    return {
        "message": "Authentication successful",
        "user_id": user_id,
        "note": "You can now make authenticated requests. The session will persist for this browser session.",
    }


@router.get("/status", status_code=200)
def auth_status(
    request: Request,
    store: SQLiteTokenStore = Depends(_get_store),
) -> dict[str, object]:
    """Check authentication status.

    Args:
        request: FastAPI request object.
        store: Token store dependency.

    Returns:
        Authentication status information.

    """
    user_id = request.session.get("user_id")
    has_token = False
    has_bot_token = False
    
    if user_id:
        user_token = store.load(str(user_id))
        bot_token = store.load(f"bot:{user_id}")
        has_token = user_token is not None
        has_bot_token = bot_token is not None
    
    return {
        "authenticated": user_id is not None and has_token,
        "user_id": user_id,
        "has_token": has_token,
        "has_bot_token": has_bot_token,
        "message": (
            "Authenticated" if (user_id and has_token) else "Not authenticated. Use GET /auth/login to authenticate via Slack."
        ),
    }


@router.post("/logout", status_code=200)
def logout(
    request: Request,
    store: SQLiteTokenStore = Depends(_get_store),
) -> dict[str, str]:
    """Log out the current user by clearing the session and optionally tokens.

    Args:
        request: FastAPI request object.
        store: Token store dependency.

    Returns:
        Success message.

    """
    user_id = request.session.get("user_id")
    
    # Optionally delete tokens (comment out if you want to keep them)
    # if user_id:
    #     store.delete(str(user_id))
    #     store.delete(f"bot:{user_id}")
    
    request.session.clear()
    logger.info("User %s logged out", user_id)
    return {"message": "Logged out successfully"}


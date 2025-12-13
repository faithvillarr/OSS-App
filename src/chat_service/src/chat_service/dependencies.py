"""Authentication dependencies for chat service."""

import logging
import os
from pathlib import Path

from fastapi import Depends, Header, HTTPException, Request, status

from slack_impl.token_store import SQLiteTokenStore, TokenBundle

logger = logging.getLogger(__name__)

# Token store initialization (shared with auth.py)
_DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./var/chat_tokens.db")
if _DB_PATH.startswith("sqlite:///"):
    _DB_PATH = _DB_PATH.replace("sqlite:///", "", 1)
Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

_store: SQLiteTokenStore | None = None


def get_token_store() -> SQLiteTokenStore:
    """Return the process-wide SQLiteTokenStore."""
    global _store
    if _store is None:
        _store = SQLiteTokenStore(_DB_PATH)
    return _store


def get_bot_token(user_id: str) -> str | None:
    """Get bot token for a user.
    
    Args:
        user_id: The user ID to get bot token for.
        
    Returns:
        Bot token string if found, None otherwise.
    """
    store = get_token_store()
    bot_key = f"bot:{user_id}"
    token_bundle = store.load(bot_key)
    if token_bundle and token_bundle.access_token:
        return token_bundle.access_token
    return None


def require_user_id(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> str:
    """Resolve a user identifier from session or header.

    For local development and tests, we fall back to a synthetic user id
    instead of failing with 401.
    """
    uid = request.session.get("user_id") or x_user_id
    if uid:
        logger.debug("User ID resolved: %s", uid)
        return str(uid)

    # Fallback used by tests and unauthenticated local calls
    logger.warning("No user ID found in session or header, using anonymous user")
    return "debug-anonymous"


def require_authentication(
    user_id: str = Depends(require_user_id),
) -> str:
    """Require authentication for protected endpoints.

    Raises:
        HTTPException: 401 if user is not authenticated (not in session).

    Returns:
        User ID if authenticated.
    """
    # Check if user is actually authenticated (not anonymous)
    if user_id == "debug-anonymous":
        logger.warning("Authentication required but user is anonymous")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authentication required. To authenticate:\n"
                "1. POST to /auth/login with {\"user_id\": \"your-user-id\"} to set a session, OR\n"
                "2. Include X-User-Id header in your request.\n\n"
                "Example: curl -X POST http://localhost:8080/auth/login "
                '-H "Content-Type: application/json" -d \'{"user_id": "my-user-id"}\''
            ),
        )

    logger.debug("User authenticated: %s", user_id)
    return user_id


def require_bot_token(
    user_id: str = Depends(require_authentication),
) -> str:
    """Require bot token for Slack operations.
    
    Args:
        user_id: Authenticated user ID.
        
    Returns:
        Bot token string.
        
    Raises:
        HTTPException: 401 if not authenticated or bot token not found.
    """
    bot_token = get_bot_token(user_id)
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Bot token not found. Please authenticate via Slack OAuth "
                "by visiting /auth/login to authorize the bot."
            ),
        )
    return bot_token


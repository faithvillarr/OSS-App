"""FastAPI application for Chat Service with Tickets Integration."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from chat_service.message_poller import start_polling, stop_polling
from chat_service.routers import auth_router, chat_router, tickets_router

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _is_https_enabled() -> bool:
    """Check if HTTPS is enabled by looking for SSL certificates."""
    cert_path = Path("/app/certs/server.crt")
    key_path = Path("/app/certs/server.key")
    return cert_path.exists() and key_path.exists()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI app.

    Handles startup and shutdown events.

    """
    logger.info("Starting Chat Service...")
    if _is_https_enabled():
        logger.info("HTTPS enabled - will set secure cookie flags")
    # Verify required environment variables are set
    required_vars = ["TASKS_CLIENT_ID", "TASKS_CLIENT_SECRET", "TASKS_REFRESH_TOKEN"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.warning(
            "Missing environment variables: %s. Ticket operations may fail.",
            ", ".join(missing_vars),
        )
    else:
        logger.info("All required environment variables are set.")

    # Check for monitored channels configuration
    monitored_channels = os.environ.get("MONITORED_CHANNELS", "")
    if monitored_channels:
        logger.info("Message polling enabled for channels: %s", monitored_channels)
        # Start background polling task
        start_polling()
    else:
        logger.info(
            "MONITORED_CHANNELS not set - message polling disabled. "
            "Set MONITORED_CHANNELS to enable automatic message processing."
        )

    yield

    # Shutdown
    logger.info("Shutting down Chat Service...")
    stop_polling()


app = FastAPI(
    title="Chat Service",
    description="Chat service with tickets integration via command parsing",
    version="0.1.0",
    lifespan=lifespan,
)

# Add session middleware
# Note: SessionMiddleware will automatically use secure cookies when the request
# is made over HTTPS (detected via the request scheme)
SESSION_SECRET = os.environ.get("SESSION_SECRET")

if not SESSION_SECRET:
    err_msg = "SESSION_SECRET must be set in non-dev environments"
    raise RuntimeError(err_msg)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(tickets_router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, bool]:
    """Health check endpoint.

    Returns:
        Health status.

    """
    return {"ok": True}


@app.get("/", tags=["infra"])
def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        API information.

    """
    return {
        "service": "Chat Service with Tickets Integration",
        "version": "0.1.0",
        "docs": "/docs",
    }

"""Routers for the chat service."""

from main_service.routers.auth import router as auth_router
from main_service.routers.chat import router as chat_router
from main_service.routers.tickets import router as tickets_router

__all__ = ["auth_router", "chat_router", "tickets_router"]


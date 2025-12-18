"""Public exports for the OpenAI implementation package."""

from openai_impl.openai_impl import OpenAIClient, get_client_impl, register

__all__ = [
    "OpenAIClient",
    "get_client_impl",
    "register",
]

# Dependency injection happens at import time
register()

"""Custom exceptions for chat client API operations."""


class ChatClientError(Exception):
    """Base exception for all chat client errors."""


class AuthenticationError(ChatClientError):
    """Raised when authentication fails or credentials are invalid."""


class MessageNotFoundError(ChatClientError):
    """Raised when a requested message cannot be found."""


class ChannelNotFoundError(ChatClientError):
    """Raised when a requested channel cannot be found."""


class MessageSendError(ChatClientError):
    """Raised when sending a message fails."""


class MessageDeleteError(ChatClientError):
    """Raised when deleting a message fails."""


class PermissionDeniedError(ChatClientError):
    """Raised when the client lacks permission for an operation."""

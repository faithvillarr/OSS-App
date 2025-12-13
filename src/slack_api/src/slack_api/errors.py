from __future__ import annotations


class ValidationError(ValueError):
    """Raised when data fails semantic validation."""


class InvalidIdError(ValidationError):
    """Raised when an identifier does not match the required shape."""

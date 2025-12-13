from __future__ import annotations

from typing import Protocol


class TokenStore(Protocol):
    """Abstract token store keyed by user_id."""

    def get(self, user_id: str) -> str | None:  # pragma: no cover - protocol
        ...

    def put(
        self, user_id: str, access_token: str
    ) -> None:  # pragma: no cover - protocol
        ...

    def delete(self, user_id: str) -> None:  # pragma: no cover - protocol
        ...

    def has(self, user_id: str) -> bool:  # pragma: no cover - protocol
        ...

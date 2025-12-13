from abc import ABC, abstractmethod


class Message(ABC):
    """Abstract wrapper around a platform-specific message."""

    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def sender_id(self) -> str:
        raise NotImplementedError

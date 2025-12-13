from abc import ABC, abstractmethod
from .message import Message


class ChatInterface(ABC):
    """Minimal interface for sending and receiving messages."""

    @abstractmethod
    def send_message(self, channel_id: str, content: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, channel_id: str, message_id: str) -> bool:
        raise NotImplementedError

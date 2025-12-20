"""Chat Client API - Abstract contract for chat service implementations.

This module provides abstract base classes and factory functions that define
the contract for chat client implementations (Discord, Slack, etc.).

Public API:
    - ChatInterface: Abstract base class for chat clients
    - Message: Abstract base class for chat messages
    - Channel: Abstract base class for channels
    - get_client: Factory function to get a client implementation
    - get_message: Factory function to create message instances
    - get_channel: Factory function to create channel instances
    - Exceptions: Custom exceptions for error handling

"""

from discord_api.client import ChatInterface as ChatInterface
from discord_api.client import get_client as get_client
from discord_api.exceptions import (
    AuthenticationError as AuthenticationError,
)
from discord_api.exceptions import (
    ChannelNotFoundError as ChannelNotFoundError,
)
from discord_api.exceptions import (
    ChatClientError as ChatClientError,
)
from discord_api.exceptions import (
    MessageDeleteError as MessageDeleteError,
)
from discord_api.exceptions import (
    MessageNotFoundError as MessageNotFoundError,
)
from discord_api.exceptions import (
    MessageSendError as MessageSendError,
)
from discord_api.exceptions import (
    PermissionDeniedError as PermissionDeniedError,
)
from discord_api.message import (
    Channel as Channel,
)
from discord_api.message import (
    Message as Message,
)
from discord_api.message import (
    get_channel as get_channel,
)
from discord_api.message import (
    get_message as get_message,
)

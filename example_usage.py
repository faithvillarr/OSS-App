"""Example usage of ChatInterface with Slack implementation.

This example demonstrates how to use the ChatInterface to interact with
the Slack service. Note that authentication is required - you must first
complete the OAuth flow to connect to a Slack workspace.

When run without authentication, operations will fail as expected.
"""

import httpx
from slack_adapter import SlackServiceBackedClient

from chat_api import ChatInterface, Message


class SlackChatAdapter(ChatInterface):
    """Adapter that implements ChatInterface using SlackServiceBackedClient."""

    def __init__(self, base_url: str = "http://localhost:8000", access_token: str | None = None) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the Slack service
            access_token: Optional access token for authentication.
                         If not provided, will attempt to use session-based auth.

        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self._client: SlackServiceBackedClient | None = None

    def _get_client(self) -> SlackServiceBackedClient:
        """Get or create the underlying SlackServiceBackedClient."""
        if self._client is None:
            # Create an httpx client with authentication headers if token is provided
            http_client = None
            if self.access_token:
                http_client = httpx.Client(
                    base_url=self.base_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
            else:
                # Without token, rely on session-based auth (requires cookies)
                http_client = httpx.Client(base_url=self.base_url)

            self._client = SlackServiceBackedClient(
                base_url=self.base_url,
                http=http_client,
            )
        return self._client

    def _make_request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Make an HTTP request to the service."""
        client = self._get_client()
        resp = client._do_request(  # noqa: SLF001
            method=method,
            path=path,
            params=params,
            json=json,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {}
        return data

    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a channel.

        Args:
            channel_id: The channel ID to send the message to
            content: The message content

        Returns:
            True if the message was sent successfully, False otherwise

        """
        try:
            client = self._get_client()
            # Use the adapter's post_message method
            result = client.post_message(channel_id=channel_id, text=content)
        except (ValueError, AttributeError, OSError) as e:
            print(f"Failed to send message: {e}")  # noqa: T201
            return False
        else:
            return result is not None

    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        """Get messages from a channel.

        Args:
            channel_id: The channel ID to get messages from
            limit: Maximum number of messages to retrieve (default: 10)

        Returns:
            List of Message objects

        """
        try:
            data = self._make_request(
                method="GET",
                path=f"/channels/{channel_id}/messages",
                params={"limit": str(limit)},
            )

            # Extract messages from response
            messages_data = data.get("messages", [])
            if not isinstance(messages_data, list):
                return []

            # Convert service messages to ChatInterface messages
            result: list[Message] = []
            for msg_data in messages_data:
                if not isinstance(msg_data, dict):
                    continue

                # Create a concrete Message implementation
                msg_id = str(msg_data.get("id", ""))
                content = str(msg_data.get("text", ""))
                sender_id = str(msg_data.get("user", ""))

                # Create a simple Message implementation
                class ChatMessage(Message):
                    def __init__(self, msg_id: str, content: str, sender_id: str) -> None:
                        self._id = msg_id
                        self._content = content
                        self._sender_id = sender_id

                    @property
                    def id(self) -> str:
                        return self._id

                    @property
                    def content(self) -> str:
                        return self._content

                    @property
                    def sender_id(self) -> str:
                        return self._sender_id

                result.append(ChatMessage(msg_id, content, sender_id))
        except (ValueError, AttributeError, OSError) as e:
            print(f"Failed to get messages: {e}")  # noqa: T201
            return []
        else:
            return result

    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message from a channel.

        Args:
            channel_id: The channel ID containing the message
            message_id: The message ID to delete

        Returns:
            True if the message was deleted successfully, False otherwise

        """
        http_no_content = 204
        try:
            resp = self._get_client()._do_request(  # noqa: SLF001
                method="DELETE",
                path=f"/channels/{channel_id}/messages/{message_id}",
            )
            # 204 No Content indicates success
        except (ValueError, AttributeError, OSError) as e:
            print(f"Failed to delete message: {e}")  # noqa: T201
            return False
        else:
            return resp.status_code == http_no_content

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None


def main() -> None:
    """Demonstrate usage of the ChatInterface with Slack."""
    print("=" * 60)  # noqa: T201
    print("ChatInterface Example with Slack Implementation")  # noqa: T201
    print("=" * 60)  # noqa: T201
    print()  # noqa: T201

    # Create the adapter
    # Note: Without authentication, this will fail as expected
    adapter = SlackChatAdapter(base_url="http://localhost:8000")

    try:
        # Check if the service is healthy
        client = adapter._get_client()  # noqa: SLF001
        is_healthy = client.health()
        print(f"Service health check: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")  # noqa: T201
        print()  # noqa: T201

        # Try to list channels (this requires authentication)
        print("Attempting to list channels...")  # noqa: T201
        channels = client.list_channels()
        print(f"Found {len(channels)} channels")  # noqa: T201
        if channels:
            print(f"First channel: {channels[0].name} (ID: {channels[0].id})")  # noqa: T201
        print()  # noqa: T201

        # Try to get messages from a channel
        # This will fail if not authenticated or if channel doesn't exist
        if channels:
            channel_id = channels[0].id
            print(f"Attempting to get messages from channel {channel_id}...")  # noqa: T201
            messages = adapter.get_messages(channel_id, limit=5)
            print(f"Retrieved {len(messages)} messages")  # noqa: T201
            for msg in messages:
                print(f"  - [{msg.id}] {msg.sender_id}: {msg.content[:50]}...")  # noqa: T201
            print()  # noqa: T201

            # Try to send a message
            print(f"Attempting to send a message to channel {channel_id}...")  # noqa: T201
            success = adapter.send_message(channel_id, "Hello from ChatInterface!")
            print(f"Message sent: {'✓ Success' if success else '✗ Failed'}")  # noqa: T201
            print()  # noqa: T201
        else:
            print("No channels available. You may need to:")  # noqa: T201
            print("  1. Complete the OAuth flow at http://localhost:8000/auth/login")  # noqa: T201
            print("  2. Ensure your Slack workspace has accessible channels")  # noqa: T201
            print()  # noqa: T201

    except (ValueError, AttributeError, OSError) as e:
        print(f"Error: {e}")  # noqa: T201
        print()  # noqa: T201
        print("This is expected if you haven't authenticated yet.")  # noqa: T201
        print("To use this service:")  # noqa: T201
        print("  1. Start the Slack service: python -m slack_service")  # noqa: T201
        print("  2. Visit http://localhost:8000/auth/login to authenticate")  # noqa: T201
        print("  3. Then run this example again")  # noqa: T201
        print()  # noqa: T201
    finally:
        adapter.close()


if __name__ == "__main__":
    main()

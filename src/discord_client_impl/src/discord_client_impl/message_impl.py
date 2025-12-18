"""Discord message and channel implementations."""

from typing import Any

from discord_api.message import Channel, Message


class DiscordMessage(Message):
    """Discord implementation of Message."""

    def __init__(self, raw_data: dict[str, Any]) -> None:
        """Initialize a Discord message from raw API data.

        Args:
            raw_data: Raw message data from Discord API.

        """
        self._raw_data = raw_data

    @property
    def id(self) -> str:
        """Return the unique identifier of the message."""
        return str(self._raw_data.get("id", ""))

    @property
    def channel_id(self) -> str:
        """Return the ID of the channel where the message was sent."""
        return str(self._raw_data.get("channel_id", ""))

    @property
    def sender_id(self) -> str:
        """Return the ID of the message author."""
        author = self._raw_data.get("author", {})
        return str(author.get("id", "")) if isinstance(author, dict) else ""

    @property
    def sender_name(self) -> str:
        """Return the display name of the message author."""
        author = self._raw_data.get("author", {})
        if isinstance(author, dict):
            # Prefer global_name, fallback to username
            return str(author.get("global_name") or author.get("username", "Unknown"))
        return "Unknown"

    @property
    def content(self) -> str:
        """Return the text content of the message."""
        return str(self._raw_data.get("content", ""))

    @property
    def timestamp(self) -> str:
        """Return the timestamp when the message was created (ISO 8601 format)."""
        return str(self._raw_data.get("timestamp", ""))

    @property
    def edited_timestamp(self) -> str | None:
        """Return the timestamp when the message was last edited, or None if never edited."""
        edited = self._raw_data.get("edited_timestamp")
        return str(edited) if edited else None


class DiscordChannel(Channel):
    """Discord implementation of Channel."""

    def __init__(self, raw_data: dict[str, Any]) -> None:
        """Initialize a Discord channel from raw API data.

        Args:
            raw_data: Raw channel data from Discord API.

        """
        self._raw_data = raw_data

    @property
    def channel_id(self) -> str:
        """Return the unique identifier of the channel."""
        return str(self._raw_data.get("id", ""))

    @property
    def name(self) -> str:
        """Return the name of the channel."""
        # DM channels may not have a name
        name = self._raw_data.get("name")
        if name:
            return str(name)
        # For DM channels, construct a name from recipients
        recipients = self._raw_data.get("recipients")
        if isinstance(recipients, list):
            if recipients:  # Non-empty recipient list
                usernames = [
                    r.get("username", "Unknown") for r in recipients if isinstance(r, dict)
                ]
                return f"DM: {', '.join(usernames)}" if usernames else "Direct Message"
            # Empty recipient list for DM
            return "Direct Message"
        return "Unknown Channel"

    @property
    def channel_type(self) -> str:
        """Return the type of channel.

        Discord channel types:
        0 = GUILD_TEXT
        1 = DM
        2 = GUILD_VOICE
        3 = GROUP_DM
        4 = GUILD_CATEGORY
        And more...

        """
        type_code = self._raw_data.get("type", 0)
        type_mapping = {
            0: "text",
            1: "dm",
            2: "voice",
            3: "group_dm",
            4: "category",
            5: "announcement",
            10: "announcement_thread",
            11: "public_thread",
            12: "private_thread",
            13: "stage_voice",
            15: "forum",
            16: "media",
        }
        return type_mapping.get(int(type_code), f"unknown_{type_code}")

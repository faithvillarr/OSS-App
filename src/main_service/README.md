# Discord Polling Service

A continuously running service that polls Discord channels for new messages and responds to them.

## Overview

This service implements the `chat_api.ChatInterface` and continuously polls a Discord channel for new messages. When new messages are detected, the service processes them and sends responses. The service runs in a polling loop, checking for new messages at regular intervals.

## Features

- Continuous polling of Discord channels for new messages
- Automatic filtering of bot's own messages to prevent response loops
- Initialization that marks existing messages as seen to avoid responding to old messages
- Error handling that allows the service to continue polling even if individual cycles fail

## Environment Variables

### Required
- `DISCORD_BOT_TOKEN` - Discord bot token for authentication
- `DISCORD_CHANNEL_ID` - The Discord channel ID to poll for messages

### Optional
- `POLLING_INTERVAL_SECONDS` - Time to wait between polls in seconds (default: `0.5`)
- `MESSAGE_CHECK_LIMIT` - Maximum number of messages to fetch per poll (default: `5`)

## Running with Docker Compose

The service is designed to run using Docker Compose:

1. **Set up your environment variables**: Create a `.env` file in the project root with your Discord credentials:
   ```bash
   DISCORD_BOT_TOKEN=your-bot-token-here
   DISCORD_CHANNEL_ID=your-channel-id-here
   POLLING_INTERVAL_SECONDS=0.5
   MESSAGE_CHECK_LIMIT=5
   ```

2. **Start the service**:
   ```bash
   docker compose up
   ```

   The service will start polling the specified Discord channel for new messages.

3. **View logs**: The service logs will be displayed in the terminal. You can also check logs with:
   ```bash
   docker compose logs -f main_service
   ```

4. **Stop the service**: Press `Ctrl+C` or run:
   ```bash
   docker compose down
   ```

## Adding the Bot to Your Discord Channel

Before the service can poll messages, you need to add your Discord bot to the channel:

1. **Create a Discord Bot** (if you haven't already):
   - Go to https://discord.com/developers/applications
   - Create a new application or select an existing one
   - Navigate to the "Bot" section
   - Create a bot and copy the bot token (this is your `DISCORD_BOT_TOKEN`)

2. **Get the Channel ID**:
   - Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
   - Right-click on the channel you want the bot to monitor
   - Select "Copy Channel ID" (this is your `DISCORD_CHANNEL_ID`)

3. **Invite the Bot to Your Server**:
   - In the Discord Developer Portal, go to OAuth2 → URL Generator
   - Select the `bot` scope
   - Select necessary bot permissions (e.g., "Read Messages", "Send Messages", "Read Message History")
   - Copy the generated URL and open it in your browser
   - Select the server and authorize the bot

4. **Add the Bot to Your Channel**:
   - In Discord, navigate to the channel where you want the bot to operate
   - Make sure the bot has permission to read and send messages in that channel
   - The bot will automatically start polling once the service is running

## How It Works

1. **Initialization**: On startup, the service:
   - Determines the bot's user ID by sending a test message
   - Fetches existing messages and marks them as "seen" to avoid responding to old messages

2. **Polling Loop**: The service continuously:
   - Fetches the most recent messages from the channel
   - Filters out messages that have already been seen
   - Filters out the bot's own messages
   - Processes any new messages by sending responses
   - Updates the seen messages set
   - Waits for the polling interval before the next cycle

3. **Error Handling**: If an error occurs during a polling cycle, the service logs the error and continues polling, ensuring the service remains running even if individual operations fail.


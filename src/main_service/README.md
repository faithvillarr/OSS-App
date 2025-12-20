# Main Service: AI-Powered Discord Ticket Management

The main service is a continuously running Discord polling service that processes user messages, extracts ticket management commands using AI, and executes them through Google Tasks. It provides natural language interaction for ticket operations.

## Overview

The main service:
- Polls a Discord channel for new messages at regular intervals
- Uses AI to extract ticket management commands from natural language
- Executes commands iteratively with AI-powered error correction
- Generates natural language responses to users
- Tracks telemetry metrics for monitoring and observability

## Architecture

The service follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      Discord Channel                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Messages
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    main.py (Polling Loop)                   │
│  - Polls channel for new messages                           │
│  - Filters bot's own messages                               │
│  - Tracks seen messages                                     │
│  - Health check HTTP server                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ New Message
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   routing.py (AI Router)                     │
│  - extract_commands(): AI extracts commands from text       │
│  - execute_commands_iteratively(): Executes with retry       │
│  - generate_response(): Creates natural language response   │
│  - correct_commands(): AI corrects failed commands           │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────────┐            ┌──────────────────────┐
│   prompts.py         │            │   ticketing.py        │
│  - System prompts    │            │  - execute_commands() │
│  - AI instructions   │            │  - Ticket operations │
└──────────────────────┘            └──────────┬─────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────┐
                                   │  tickets_client_impl  │
                                   │  (Google Tasks API)   │
                                   └──────────────────────┘
```

## Modules

### main.py

**Entry point and polling orchestration**

Responsibilities:
- Initializes all clients (chat, ticket, AI)
- Runs the main polling loop
- Manages health check HTTP server for Cloud Run
- Filters and processes new messages
- Handles initialization and error recovery

Key Functions:
- `main()`: Entry point that initializes and starts the polling loop
- `_run_polling_loop()`: Main polling loop that continuously checks for messages
- `_poll_cycle()`: Single polling cycle that fetches and processes messages
- `_process_new_message()`: Processes a single message through the routing system
- `_start_health_check_server()`: Starts HTTP server for Cloud Run health checks

### routing.py

**AI-powered command extraction and execution**

This is the core intelligence of the system. It uses AI to:
1. Extract structured commands from natural language
2. Execute commands with iterative error correction
3. Generate natural language responses

Key Functions:

**`extract_commands(user_message: str) -> list[dict]`**
- Uses AI to extract ticket commands from user's natural language message
- Returns structured command dictionaries with `type` and `params`
- Includes validation and retry logic (up to 3 attempts)
- Command types: `create_ticket`, `get_ticket`, `search_tickets`, `update_ticket`, `delete_ticket`

**`execute_commands_iteratively(user_message, initial_commands, ticket_client, max_iterations=5) -> list[dict]`**
- Executes commands one at a time
- If a command fails, uses AI to correct it based on the error message
- Continues until all commands succeed or max iterations reached
- Returns accumulated results from all command executions

**`generate_response(user_message, ticket_results) -> str`**
- Uses AI to generate a natural language response from ticket operation results
- Provides user-friendly feedback about what was done

**`correct_commands(original_commands, error_message) -> list[dict]`**
- Uses AI to correct failed commands based on error messages
- Includes validation and retry logic

### prompts.py

**System prompts for AI interactions**

Contains all system prompts used for AI interactions:
- `get_command_extraction_prompt()`: Instructions for extracting commands from user messages
- `get_error_correction_prompt()`: Instructions for correcting failed commands
- `get_followup_command_prompt()`: Instructions for generating follow-up commands
- `get_response_generation_prompt()`: Instructions for generating user responses

These prompts are carefully crafted to guide the AI in:
- Understanding ticket management terminology
- Extracting ticket IDs from various formats
- Handling ambiguous requests
- Generating helpful error messages

### ticketing.py

**Ticket command execution**

Executes ticket operations and formats results:
- `execute_commands(commands, ticket_client) -> list[dict]`: Executes a list of commands
- `format_ticket_for_json(ticket) -> dict`: Formats Ticket objects for JSON serialization
- Individual execution functions for each command type

Each command execution:
- Validates required parameters
- Calls the appropriate `ticket_client` method
- Returns standardized result dictionaries with `success`, `command`, `result`, and `error` fields

### telemetry.py

**OpenTelemetry metrics collection**

Tracks metrics for observability:
- Message processing duration
- Message processing success/failure counts
- Poll cycle metrics
- Error categorization

Metrics are exported via OTLP to an OpenTelemetry Collector, which forwards them to Google Cloud Monitoring when deployed.

## Message Processing Flow

1. **Poll Cycle** (`main.py`):
   - Fetches recent messages from Discord channel
   - Filters out bot's own messages
   - Identifies new messages not in `seen_message_ids` set

2. **Command Extraction** (`routing.py`):
   - For each new message, calls `extract_commands()`
   - AI analyzes the message and extracts structured commands
   - Returns list of command dictionaries

3. **Command Execution** (`routing.py` + `ticketing.py`):
   - If commands found: `execute_commands_iteratively()` runs them
     - Executes each command one at a time
     - If a command fails, uses AI to correct it
     - Retries up to `max_iterations` times
   - If no commands found: skips execution

4. **Response Generation** (`routing.py`):
   - `generate_response()` creates natural language response
   - AI summarizes what was done based on results

5. **Response Delivery** (`main.py`):
   - Sends response back to Discord channel
   - Marks message as seen

## Iterative Command Execution

The system uses an iterative execution pattern to handle errors gracefully:

```
User Message → Extract Commands → Execute Command 1
                                      │
                                      ├─ Success → Execute Command 2
                                      │
                                      └─ Failure → AI Corrects Command
                                                      │
                                                      └─ Retry Command 1
```

This allows the AI to:
- Fix missing parameters (e.g., extract ticket ID from context)
- Correct invalid values (e.g., fix status enum values)
- Handle ambiguous requests (e.g., clarify which ticket to update)

## Environment Variables

### Required

- **`DISCORD_BOT_TOKEN`**: Discord bot token for authentication
  - Get from: https://discord.com/developers/applications
  - Required for: Discord API access

- **`DISCORD_CHANNEL_ID`**: Discord channel ID to poll
  - Get by: Right-click channel → Copy Channel ID (Developer Mode must be enabled)
  - Required for: Knowing which channel to monitor

- **`OPENAI_API_KEY`**: OpenAI API key for AI operations
  - Get from: https://platform.openai.com/api-keys
  - Required for: Command extraction, error correction, response generation

### Google Tasks (Required for ticket operations)

One of the following authentication methods:

**Option 1: Environment Variables** (Recommended for production)
- `GTASK_CLIENT_ID`: Google Tasks OAuth Client ID
- `GTASK_CLIENT_SECRET`: Google Tasks OAuth Client Secret
- `GTASK_REFRESH_TOKEN`: Google Tasks OAuth Refresh Token

**Option 2: Credential Files** (For local development)
- `credentials.json`: OAuth 2.0 credentials file from Google Cloud Console
- `token.json`: Auto-generated after first interactive OAuth flow

### Optional

- **`POLLING_INTERVAL_SECONDS`**: Time between polls (default: `0.5`)
- **`MESSAGE_CHECK_LIMIT`**: Max messages to fetch per poll (default: `5`)
- **`PORT`**: Port for health check server (default: `8080`)
- **`OTEL_EXPORTER_OTLP_ENDPOINT`**: OTLP endpoint for telemetry (default: `http://localhost:4317`)

## Local Development

### Using Docker Compose (Recommended)

1. **Create `.env` file** in project root:
   ```bash
   DISCORD_BOT_TOKEN=your-bot-token
   DISCORD_CHANNEL_ID=your-channel-id
   OPENAI_API_KEY=your-openai-key
   GTASK_CLIENT_ID=your-client-id
   GTASK_CLIENT_SECRET=your-client-secret
   GTASK_REFRESH_TOKEN=your-refresh-token
   ```

2. **Start services**:
   ```bash
   docker compose up
   ```

   This starts:
   - `main_service`: The Discord polling service
   - `otel-collector`: OpenTelemetry Collector (local config uses debug exporter)

3. **View logs**:
   ```bash
   docker compose logs -f main_service
   ```

4. **Stop services**:
   ```bash
   docker compose down
   ```

### Running Directly (Without Docker)

1. **Install dependencies**:
   ```bash
   uv sync --all-packages
   ```

2. **Set environment variables** (see above)

3. **Run the service**:
   ```bash
   uv run python -m main_service.main
   ```

## Deployment

The service is designed to run on Google Cloud Run. Deployment is automated via the `deploy.sh` script.

### Prerequisites

1. Google Cloud Project with billing enabled
2. Required APIs enabled (handled by `deploy.sh`):
   - Cloud Run API
   - Secret Manager API
   - Cloud Monitoring API
   - Container Registry API
3. Google Cloud SDK (`gcloud`) installed and authenticated
4. Terraform >= 1.0 installed

### Deployment Steps

1. **Configure Terraform variables**:
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform/terraform.tfvars`** and fill in:
   - `project_id`: Your GCP project ID
   - `region`: GCP region (e.g., `us-central1`)
   - `tasks_client_id`: Google Tasks OAuth Client ID
   - `tasks_client_secret`: Google Tasks OAuth Client Secret
   - `tasks_refresh_token`: Google Tasks OAuth Refresh Token
   - `openai_api_key`: OpenAI API key

3. **Run deployment script**:
   ```bash
   ./deploy.sh
   ```

   The script will:
   - Check prerequisites
   - Enable required GCP APIs
   - Set up Secret Manager secrets (Discord bot token, channel ID)
   - Build and push Docker images
   - Deploy infrastructure with Terraform

4. **Verify deployment**:
   ```bash
   cd terraform
   terraform output service_url
   gcloud run services logs read main-service --region=us-central1
   ```

For detailed Terraform documentation, see [terraform/README.md](../../terraform/README.md).

## Health Checks

The service includes an HTTP health check server for Cloud Run compatibility:
- Listens on port specified by `PORT` environment variable (default: 8080)
- Responds with `200 OK` to GET requests on `/` or `/health`
- Runs in a separate thread to not block the polling loop

Cloud Run uses this endpoint to determine if the container is healthy.

## Telemetry and Monitoring

The service exports OpenTelemetry metrics:

- **`message_processing_duration`**: End-to-end latency from message processing start to response posting
- **`message_processing_total{status="success"}`**: Count of successful message processing calls
- **`message_processing_total{status="failure"}`**: Count of failed message processing calls
- **`poll_cycle_duration`**: Duration of each polling cycle
- **`poll_cycle_total`**: Count of polling cycles

Metrics are exported via OTLP to an OpenTelemetry Collector sidecar container, which forwards them to Google Cloud Monitoring.

### Viewing Metrics

1. Go to: https://console.cloud.google.com/monitoring/metrics-explorer
2. Search for: `custom.googleapis.com/opentelemetry/main_service/message_processing_total`
3. Create dashboards and alerts as needed

## Error Handling

The service includes comprehensive error handling:

1. **Message Processing Errors**:
   - Errors during message processing are caught and logged
   - User receives a generic error message
   - Service continues polling

2. **Command Extraction Errors**:
   - Retries up to 3 times with validation feedback
   - Falls back to generating a helpful response if extraction fails

3. **Command Execution Errors**:
   - Uses AI to correct failed commands
   - Retries up to `max_iterations` times
   - Accumulates all results (successful and failed)

4. **Client Initialization Errors**:
   - Service exits with clear error messages if critical clients fail to initialize
   - Non-critical clients (like telemetry) log warnings but allow service to continue

## Troubleshooting

### Service not responding to messages

1. **Check Discord bot token**:
   ```bash
   echo $DISCORD_BOT_TOKEN
   ```
   Ensure the token is valid and the bot is invited to the server.

2. **Check channel ID**:
   ```bash
   echo $DISCORD_CHANNEL_ID
   ```
   Ensure the channel ID is correct and the bot has permission to read/write.

3. **Check logs**:
   ```bash
   docker compose logs main_service
   ```
   Look for authentication errors or permission issues.

### Commands not being extracted

1. **Check OpenAI API key**:
   ```bash
   echo $OPENAI_API_KEY
   ```
   Ensure the key is valid and has credits.

2. **Check logs for extraction errors**:
   ```bash
   docker compose logs main_service | grep "extract"
   ```
   Look for validation errors or API failures.

### Ticket operations failing

1. **Check Google Tasks credentials**:
   - Verify environment variables are set correctly
   - Or ensure `credentials.json` and `token.json` exist

2. **Check ticket client initialization**:
   ```bash
   docker compose logs main_service | grep "ticket client"
   ```
   Look for initialization errors.

3. **Verify tasklists exist**:
   The service needs at least one Google Tasks tasklist to create tickets.

### Health check failing

1. **Check port configuration**:
   ```bash
   echo $PORT
   ```
   Ensure the port is not conflicting with other services.

2. **Check Cloud Run logs**:
   ```bash
   gcloud run services logs read main-service --region=us-central1
   ```
   Look for HTTP server errors.

## Architecture Decisions

### Why polling instead of webhooks?

- Simpler deployment (no need for public endpoint)
- Works with Cloud Run (no need for ingress)
- More resilient to temporary Discord API outages

### Why iterative command execution?

- Allows AI to correct errors based on actual API responses
- Handles ambiguous user requests gracefully
- Provides better user experience with automatic error recovery

### Why separate modules?

- Clear separation of concerns
- Easy to test individual components
- Allows swapping implementations (e.g., different AI providers)

## Testing

Run tests for the main service:

```bash
# From project root
uv run pytest src/main_service/ -v
```

Note: Some tests may require local credentials or environment variables.

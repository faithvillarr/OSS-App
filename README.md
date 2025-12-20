# OSS-APP: AI-Powered Ticket Management with Discord Integration

[![CircleCI](https://circleci.com/gh/ivanearisty/oss-taapp.svg?style=shield)](https://circleci.com/gh/ivanearisty/oss-taapp)
[![Coverage](https://img.shields.io/badge/coverage-85%2B%25-brightgreen)](https://circleci.com/gh/ivanearisty/oss-taapp)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

This repository is a professional-grade Python application that provides an AI-powered ticket management system integrated with Discord. The system polls Discord channels for messages, uses AI to extract ticket management commands from natural language, and executes them using Google Tasks as the backend.

**Current Status**: The system is fully functional with:
- Discord message polling and response system
- AI-powered natural language command extraction
- Google Tasks-based ticket management
- Cloud Run deployment with Terraform
- OpenTelemetry telemetry and monitoring

The project emphasizes a strict separation of concerns, dependency injection, and a comprehensive, automated toolchain to enforce code quality and best practices.

## Architectural Philosophy

This project is built on the principle of "programming integrated over time." The architecture is designed to combat complexity and ensure the system is maintainable and evolvable.

-   **Component-Based Design:** The system is broken down into distinct, self-contained components. Each component has a single responsibility and can be "forklifted" out of this project to be used in another with minimal effort.
-   **Interface-Implementation Separation:** Every piece of functionality is defined by an abstract **contract** implemented as an ABC (the "what") and fulfilled by a concrete **implementation** (the "how"). This decouples our business logic from specific technologies (like Google Tasks).
-   **Dependency Injection:** Implementations are "injected" into the abstract contracts at runtime. This means consumers of the API only ever depend on the stable interface, not the volatile implementation details.

## Core Components

The project is a `uv` workspace containing the following primary packages:

### Main Service
-   **`main_service`**: The core Discord polling service that processes messages, extracts commands using AI, and manages tickets. See [src/main_service/README.md](src/main_service/README.md) for detailed documentation.

### Chat Components
-   **`chat_api`**: Defines the abstract `ChatInterface` contract for chat operations (send_message, get_messages, delete_message).
-   **`chat_client_impl`**: Adapter that bridges `discord_api` to the minimal `chat_api` contract.
-   **`discord_api`**: Discord-specific API contract with richer message metadata.
-   **`discord_client_impl`**: Concrete Discord API implementation using Discord's HTTP API.

### AI Components
-   **`ai_api`**: Defines the abstract `AIClient` interface for AI operations.
-   **`openai_impl`**: OpenAI implementation of the AI client interface.

### Ticketing Components
-   **`tickets_api`**: Defines the abstract `TicketInterface` and `Ticket` base classes (ABC). This is the contract for ticketing operations (e.g., `create_ticket`, `search_tickets`, `update_ticket`).
-   **`tickets_client_impl`**: Provides the `TicketsClient` class, a concrete implementation that uses Google Tasks as the backend for ticketing operations.
-   **`task_client_api`**: Defines the abstract `Client` base class (ABC) for task and tasklist operations.
-   **`gtask_client_impl`**: Provides the `GTaskClient` class, a concrete implementation that uses the Google Tasks API.

## Project Structure

```
oss-app/
├── src/                          # Source packages (uv workspace members)
│   ├── main_service/             # Discord polling service with AI routing
│   ├── chat_api/                 # Abstract chat interface (ABC)
│   ├── chat_client_impl/         # Discord adapter for chat_api
│   ├── discord_api/              # Discord-specific API contract
│   ├── discord_client_impl/      # Discord API implementation
│   ├── ai_api/                   # Abstract AI client interface (ABC)
│   ├── openai_impl/              # OpenAI implementation
│   ├── tickets_api/              # Abstract ticketing interface (ABC)
│   ├── tickets_client_impl/      # Google Tasks-based ticket implementation
│   ├── task_client_api/          # Abstract task client base class (ABC)
│   └── gtask_client_impl/        # Google Tasks API implementation
├── terraform/                      # Infrastructure as Code
│   ├── main.tf                  # Terraform configuration
│   ├── variables.tf             # Variable definitions
│   ├── outputs.tf               # Output definitions
│   ├── terraform.tfvars.example # Example variables (copy to terraform.tfvars)
│   └── README.md                # Terraform deployment documentation
├── tests/                       # Integration and E2E tests
│   ├── gtask_integration/       # Google Tasks integration tests
│   └── e2e/                     # End-to-end application tests
├── docs/                        # Documentation source files
├── deploy.sh                    # Complete deployment script for Cloud Run
├── docker-compose.yml           # Local development setup
├── Dockerfile                   # Production Docker image for main_service
├── Dockerfile.otel-collector    # OpenTelemetry Collector sidecar image
├── otel-collector-config.yaml   # Production OTel collector config
├── otel-collector-config.local.yaml # Local OTel collector config
├── pyproject.toml               # Root workspace configuration
├── uv.lock                      # Locked dependency versions
├── mkdocs.yml                   # MkDocs configuration
└── README.md                    # This file
```

### Root-Level Files

Files in the project root (outside of `src/` and `terraform/`):

- **`deploy.sh`**: Complete deployment script that automates the entire Cloud Run deployment process. Handles Docker image building, Secret Manager setup, and Terraform deployment. See [Deployment](#deployment) section.

- **`discord_main.py`**: Simple demo script for testing Discord chat API integration. Sends a test message and fetches recent messages from a Discord channel.

- **`tickets_wrapper.py`**: Demo script demonstrating ticket operations (create, search, update, delete) using the TicketsClient.

- **`example_usage.py`**: Example usage of ChatInterface (currently demonstrates Slack adapter pattern).

- **`quickstart_openai.py`**: Quickstart script demonstrating OpenAI AI client integration.

- **`og_tickets.py`**: Legacy demo script for task client operations (original implementation).

- **`docker-compose.yml`**: Local development setup with `main_service` and `otel-collector` containers. Use this for local testing without deploying to Cloud Run.

- **`Dockerfile`**: Production Docker image for the main_service. Multi-stage build optimized for Cloud Run.

- **`Dockerfile.otel-collector`**: Docker image for OpenTelemetry Collector sidecar container used in Cloud Run deployment.

- **`otel-collector-config.yaml`**: Production OpenTelemetry Collector configuration with Google Cloud Monitoring exporter.

- **`otel-collector-config.local.yaml`**: Local development OpenTelemetry Collector configuration with debug exporter (no GCP credentials needed).

- **`pyproject.toml`**: Root workspace configuration defining all workspace members, dependencies, and tool configurations (ruff, mypy, pytest).

- **`.env.example`**: Example environment variables file. Copy to `.env` and fill in your values for local development.

## Project Setup

### 1. Prerequisites

-   Python 3.11 or higher
-   `uv` – A fast, all-in-one Python package manager
-   Docker and Docker Compose (for local development)
-   Google Cloud SDK (`gcloud`) (for deployment)
-   Terraform >= 1.0 (for deployment)

### 2. Initial Setup

1.  **Install `uv`:**
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Windows (PowerShell)
    irm https://astral.sh/uv/install.ps1 | iex
    ```

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd ta-assignment
    ```

3.  **Set Up Google Credentials:**
    -   Follow the [Google Cloud instructions](https://developers.google.com/tasks/api/quickstart/python#authorize_credentials_for_a_desktop_application) to enable the Google Tasks API and download your OAuth 2.0 credentials.
    -   Rename the downloaded file to `credentials.json` and place it in the root of this project.
    -   **Alternative**: For CI/CD environments, you can use environment variables instead:
        ```bash
        export GTASK_CLIENT_ID="your_client_id"
        export GTASK_CLIENT_SECRET="your_client_secret"
        export GTASK_REFRESH_TOKEN="your_refresh_token"
        ```
    -   **Important:** Credential files contain secrets and are ignored by `.gitignore`.

4.  **Create and Sync the Virtual Environment:**
    This single command creates a `.venv` folder and installs all packages (including workspace members and development tools) defined in `uv.lock`.
    ```bash
    uv sync --all-packages --extra dev
    ```

5.  **Activate the Virtual Environment:**
    ```bash
    # macOS / Linux
    source .venv/bin/activate
    # Windows (PowerShell)
    .venv\Scripts\Activate.ps1
    ```

6.  **Perform Initial Authentication:**
    Run the main application once to perform the interactive OAuth flow. This will open a browser window for you to grant permission.
    ```bash
    uv run python tickets_wrapper.py
    ```
    After you approve, a `token.json` file will be created. This file is also ignored by `.gitignore` and will be used for authentication in subsequent runs.

## Local Development

### Running the Main Service Locally

The main service can be run locally using Docker Compose:

1. **Create a `.env` file** from the example:
   ```bash
   cp .env.example .env
   ```

2. **Fill in your environment variables** in `.env`:
   ```bash
   DISCORD_BOT_TOKEN=your-discord-bot-token
   DISCORD_CHANNEL_ID=your-discord-channel-id
   OPENAI_API_KEY=your-openai-api-key
   GTASK_CLIENT_ID=your-google-tasks-client-id
   GTASK_CLIENT_SECRET=your-google-tasks-client-secret
   GTASK_REFRESH_TOKEN=your-google-tasks-refresh-token
   ```

3. **Start the services**:
   ```bash
   docker compose up --build
   ```

   This starts:
   - `main_service`: The Discord polling service
   - `otel-collector`: OpenTelemetry Collector for metrics (local config uses debug exporter)

4. **View logs**:
   ```bash
   docker compose logs -f main_service
   ```

5. **Stop the services**:
   ```bash
   docker compose down
   ```

### Running Demo Scripts

**Discord Chat Demo:**
```bash
export DISCORD_BOT_TOKEN="your_token"
export DISCORD_CHANNEL_ID="your_channel_id"
uv run python discord_main.py
```

**Ticket Operations Demo:**
```bash
uv run python tickets_wrapper.py
```

**OpenAI Quickstart:**
```bash
export OPENAI_API_KEY="your_key"
uv run python quickstart_openai.py
```

## Deployment

The project uses Terraform for infrastructure deployment to Google Cloud Run. The deployment process is automated via the `deploy.sh` script.

### Prerequisites for Deployment

1. **Google Cloud Project** with billing enabled
2. **Required APIs enabled**:
   - Cloud Run API
   - Secret Manager API
   - Cloud Monitoring API
   - Container Registry API (or Artifact Registry API)
3. **Google Cloud SDK** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
4. **Terraform** >= 1.0 installed
5. **Docker** installed and running

### Deployment Steps

1. **Configure Terraform variables**:
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform/terraform.tfvars`** and fill in:
   - `project_id`: Your GCP project ID
   - `region`: GCP region (e.g., `us-central1`)
   - `image`: Docker image URL (will be set by deploy script)
   - `tasks_client_id`: Google Tasks OAuth Client ID
   - `tasks_client_secret`: Google Tasks OAuth Client Secret
   - `tasks_refresh_token`: Google Tasks OAuth Refresh Token
   - `openai_api_key`: OpenAI API key

3. **Run the deployment script**:
   ```bash
   ./deploy.sh
   ```

   The script will:
   - Check prerequisites (gcloud, docker, terraform)
   - Enable required GCP APIs
   - Set up Secret Manager secrets (Discord bot token, channel ID)
   - Build and push Docker images
   - Deploy infrastructure with Terraform
   - Display the service URL

4. **Verify deployment**:
   ```bash
   # Get service URL
   cd terraform
   terraform output service_url
   
   # View logs
   gcloud run services logs read main-service --region=us-central1
   ```

For detailed Terraform documentation, see [terraform/README.md](terraform/README.md).

For detailed main_service documentation, see [src/main_service/README.md](src/main_service/README.md).

## Development Workflow

All commands should be run from the project root with the virtual environment activated.

### Running the Toolchain

-   **Linting & Formatting (Ruff):**
    The project uses Ruff with comprehensive rules configured in `pyproject.toml`.
    ```bash
    # Check for issues
    uv run ruff check .
    # Automatically fix issues
    uv run ruff check . --fix
    # Check formatting
    uv run ruff format --check .
    # Apply formatting
    uv run ruff format .
    ```

-   **Static Type Checking (MyPy):**
    ```bash
    uv run mypy src tests
    ```

-   **Testing (Pytest):**

    I'd recommend only running: `uv run pytest src/ tests/ -m "not local_credentials" -v` for simplicity.

    The project uses a comprehensive testing strategy with different test categories.
    ```bash
    # Run all tests (includes unit, integration, and e2e tests)
    uv run pytest

    # Run only unit tests (fast, no external dependencies - from src/ directories)
    uv run pytest src/

    # Run all tests except those requiring local credential files
    uv run pytest src/ tests/ -m "not local_credentials"

    # Run only integration tests (requires environment variables or credentials)
    uv run pytest -m integration

    # Run only end-to-end tests (requires credentials)
    uv run pytest -m e2e

    # Run only CircleCI-compatible tests (CI/CD environment)
    uv run pytest -m circleci

    # Run tests with coverage reporting
    uv run pytest --cov=src --cov-report=term-missing
    ```

### Viewing Documentation

This project uses MkDocs for documentation.
```bash
# Start the live-reloading documentation server
uv run mkdocs serve
```
Open your browser to `http://127.0.0.1:8000` to view the site.

## Testing Infrastructure

The project implements a sophisticated testing strategy designed for both local development and CI/CD environments:

### Test Categories

- **Unit Tests** (`src/*/tests/`): Fast, isolated tests with mocked dependencies
- **Integration Tests** (`tests/integration/`): Tests that verify component interactions
- **End-to-End Tests** (`tests/e2e/`): Full application workflow tests
- **CircleCI Tests**: CI/CD-compatible tests that handle missing credentials gracefully
- **Local Credentials Tests**: Tests that require `credentials.json` or `token.json` files

### Test Markers

The project uses pytest markers to categorize tests:
```bash
@pytest.mark.unit              # Fast unit tests
@pytest.mark.integration       # Integration tests
@pytest.mark.e2e              # End-to-end tests
@pytest.mark.circleci         # CI/CD compatible
@pytest.mark.local_credentials # Requires local auth files
```

### Authentication in Tests

The testing infrastructure handles different authentication scenarios:
- **Local Development**: Uses `credentials.json` and `token.json` files
- **CI/CD Environment**: Uses environment variables (`GTASK_CLIENT_ID`, `GTASK_CLIENT_SECRET`, `GTASK_REFRESH_TOKEN`)
- **Missing Credentials**: Tests fail fast with clear error messages (no hanging)

## Continuous Integration

The project includes a comprehensive CircleCI configuration (`.circleci/config.yml`) with:

- **All Branches**: Unit tests, linting, and CI-compatible tests
- **Main/Develop**: Additional integration tests with real Google Tasks API calls
- **Artifacts**: Coverage reports, test results, and build summaries

See `docs/circleci-setup.md` for detailed CI/CD setup instructions.

### Quick Start
1. **Install dependencies**: `uv sync --all-packages --extra dev`
2. **Run tests**: `uv run pytest src/ tests/ -m "not local_credentials" -v`
3. **Check code quality**: `uv run ruff check . && uv run ruff format --check .`
4. **Fix formatting**: `uv run ruff format .`
5. **View documentation**: `uv run mkdocs serve`

### Best Practices
- Run unit tests (`uv run pytest src/`) during development for fast feedback
- Use integration tests (`uv run pytest -m integration`) to verify component interactions
- Run full test suite (`uv run pytest`) before pushing to ensure CI compatibility
- The CircleCI pipeline provides automated validation on every push
- Use `docker compose up` for local main_service development and testing
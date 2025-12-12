# OSS-APP: Ticketing Integration with AI and Chatbot

[![CircleCI](https://circleci.com/gh/ivanearisty/oss-taapp.svg?style=shield)](https://circleci.com/gh/ivanearisty/oss-taapp)
[![Coverage](https://img.shields.io/badge/coverage-85%2B%25-brightgreen)](https://circleci.com/gh/ivanearisty/oss-taapp)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

This repository is a professional-grade Python application that integrates ticketing systems with AI and chatbot capabilities. Currently, the project includes the core ticketing integration built on a component-based architecture using Google Tasks as the backend.

**Current Status**: The ticketing integration is complete and functional. AI and chatbot features are planned for future development.

The project emphasizes a strict separation of concerns, dependency injection, and a comprehensive, automated toolchain to enforce code quality and best practices.

## Architectural Philosophy

This project is built on the principle of "programming integrated over time." The architecture is designed to combat complexity and ensure the system is maintainable and evolvable.

-   **Component-Based Design:** The system is broken down into distinct, self-contained components. Each component has a single responsibility and can be "forklifted" out of this project to be used in another with minimal effort.
-   **Interface-Implementation Separation:** Every piece of functionality is defined by an abstract **contract** implemented as an ABC (the "what") and fulfilled by a concrete **implementation** (the "how"). This decouples our business logic from specific technologies (like Google Tasks).
-   **Dependency Injection:** Implementations are "injected" into the abstract contracts at runtime. This means consumers of the API only ever depend on the stable interface, not the volatile implementation details.

## Core Components

The project is a `uv` workspace containing the following primary packages:

### Ticketing Components
-   **`tickets_api`**: Defines the abstract `TicketInterface` and `Ticket` base classes (ABC). This is the contract for ticketing operations (e.g., `create_ticket`, `search_tickets`, `update_ticket`).
-   **`tickets_client_impl`**: Provides the `TicketsClient` class, a concrete implementation that uses Google Tasks as the backend for ticketing operations.

### Task Management Components
-   **`task_client_api`**: Defines the abstract `Client` base class (ABC) for task and tasklist operations.
-   **`gtask_client_impl`**: Provides the `GTaskClient` class, a concrete implementation that uses the Google Tasks API.
-   **`task_client_service`**: FastAPI service implementation for task operations over HTTP.
-   **`task_client_adapter`**: Adapter pattern implementation for service-based task operations.
-   **`task_client_service_client`**: Auto-generated service client for interacting with the task service.

## Project Structure

```
oss-app/
├── src/                          # Source packages (uv workspace members)
│   ├── tickets_api/              # Abstract ticketing interface (ABC)
│   ├── tickets_client_impl/      # Google Tasks-based ticket implementation
│   ├── task_client_api/          # Abstract task client base class (ABC)
│   ├── gtask_client_impl/        # Google Tasks API implementation
│   ├── task_client_service/      # FastAPI service for task operations
│   ├── task_client_adapter/      # Adapter for service-based task operations
│   └── task_client_service_client/ # Auto-generated service client
├── tests/                        # Integration and E2E tests
│   ├── gtask_integration/        # Google Tasks integration tests
│   └── e2e/                      # End-to-end application tests
├── docs/                         # Documentation source files
├── tickets_wrapper.py            # Main application entry point (ticketing demo)
├── pyproject.toml               # Project configuration (dependencies, tools)
├── uv.lock                      # Locked dependency versions
├── mkdocs.yml                   # MkDocs configuration
├── token.json                   # OAuth token (local only)
└── README.md
```

## Project Setup

### 1. Prerequisites

-   Python 3.11 or higher
-   `uv` – A fast, all-in-one Python package manager.

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

## Development Workflow

All commands should be run from the project root with the virtual environment activated.

### Running the Application

To run the main ticketing demonstration script:
```bash
uv run python tickets_wrapper.py
```

This will demonstrate the ticketing integration by creating, searching, updating, and managing tickets using Google Tasks as the backend.

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

## Development Workflow

### Quick Start
1. **Install dependencies**: `uv sync --all-packages --extra dev`
2. **Run tests**: `uv run pytest tests/ -v` or `uv run pytest src/ tests/ -m "not local_credentials" -v`
3. **Check code quality**: `uv run ruff check . && uv run ruff format --check .`
4. **Fix formatting**: `uv run ruff format .`
5. **View documentation**: `uv run mkdocs serve`

### Best Practices
- Run unit tests (`uv run pytest src/`) during development for fast feedback
- Use integration tests (`uv run pytest -m integration`) to verify component interactions
- Run full test suite (`uv run pytest`) before pushing to ensure CI compatibility
- The CircleCI pipeline provides automated validation on every push
# CONTRIBUTING.md

# Homework 1: Review — Contributor Guide

> ⚠️ **Historical Note:** This document describes the architecture of an earlier version of the repository that focused on mail client functionality. The current application is **OSS-APP: Ticketing Integration with AI and Chatbot**, which focuses on ticketing operations using Google Tasks as the backend. The architectural patterns and principles described here still apply, but the current components are:
> - **Ticketing**: `tickets_api`, `tickets_client_impl`
> - **Task Management**: `task_client_api`, `gtask_client_impl`, `task_client_service`, `task_client_adapter`, `task_client_service_client`
>
> For current component documentation, see [the main documentation index](index.md).

### Summary

This document serves as the **Contributor Guide** for the base Teaching Assistant (TA) repository. It is designed to onboard new contributors by explaining the repository's **architecture, interfaces, design patterns, development workflow, and best practices**.

> ⚠️ **Note:** This document covers **only the base repository**. New components (e.g., FastAPI service, generated client, adapter) will be documented separately in `DESIGN.md`.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
   - [Components](#components)
   - [Interface Design](#interface-design)
   - [Implementation Details](#implementation-details)
   - [Dependency Injection](#dependency-injection)
2. [Repository Structure](#repository-structure)
   - [Project Organization](#project-organization)
   - [Configuration Files](#configuration-files)
   - [Package Structure](#package-structure)
   - [Import Guidelines](#import-guidelines)
3. [Testing Strategy](#testing-strategy)
   - [Testing Philosophy](#testing-philosophy)
   - [Test Organization](#test-organization)
   - [Test Abstraction Levels](#test-abstraction-levels)
   - [Code Coverage](#code-coverage)
4. [Development Tools](#development-tools)
   - [Workspace Management](#workspace-management)
   - [Static Analysis and Code Formatting](#static-analysis-and-code-formatting)
   - [Documentation Generation](#documentation-generation)
   - [CI](#ci)

## Architecture Overview

### Components

#### gmail_client_impl

- Gmail Client handles
  - OAuth2 sign in and gmail scope permissions
  - Gmail api integration
  - Automatic Dependency injection and defines abstract classes of:
    - `mail_client_api.client`
    - `mail_client_api.message`

#### mail_client_api

- **Mail Client API** is a abstract base class composed of:
  - **Abstraction** of both **mail client**, and **email message**
  - **Factory hook**: globally call instances of the mail client
- Does not have defined logic in these abstractions, since they are meant to be defined by a mail client's dependency injection (e.g **gmail_client_impl**)

---

### Interface Design

#### **Client**

- **Purpose:** Unified mailbox façade for fetching and mutating message state.
- **Surface:**
  - get_message(message_id: str) -> Message — returns a domain Message object for the given ID.
  - delete_message(message_id: str) -> bool — removes the message; True on success, False on failure.
  - mark_as_read(message_id: str) -> bool — idempotently clears “unread”; True if the message is (now) read.
  - get_messages(max_results: int = 10) -> Iterator[Message] — lazily yields recent messages as Message objects.
- **Creation:** get_client(\*, interactive: bool = False) -> Client — returns a concrete provider-bound client (e.g., Gmail) with provider-specific auth handled internally.

#### **Message**

- **Purpose:** Provider-agnostic, read-only view of an email’s essential fields.
- **Surface (properties):**
  - id: str — unique identifier.
  - from\_: str — sender address.
  - to: str — recipient(s).
  - date: str — sent date; normalized when possible, else raw.
  - subject: str — decoded subject (handles RFC 2047).
  - body: str — best-effort plain-text body (multipart/MIME-aware).
- **Creation:** get_message(msg_id: str, raw_data: str) -> Message : factory that hydrates a Message from provider payload, hiding MIME/decoding details.

#### **Justification**

**Gmail Client**

- **Deep interface, small surface:** A few obvious verbs hide significant provider complexity (OAuth, pagination, rate limits). This reduces cognitive load and change amplification in callers.
- **Return domain objects, not payloads:** Message is returned instead of provider JSON, preventing leakage of provider schemas and consistnent and predictable object structure and fields.
- **Boolean results for operational mutations:** `delete_message/mark_as_read` return `bool` to normalize common transient failures without forcing callers to handle provider exceptions for routine control flow.
- **Iterator Return Type:** `get_messages` uses an iterator for time and memory efficient handling of possibly large amounts of email messages returned from `get_messages`
- **Factory indirection (get_client)**: Separates how the client is created and authenticated from how it’s used, allowing both CI tests and manual interactions without changing the API.

**Message**

- **Read-only, minimal shape:** Immutable, essential fields only. Data stays consistent and only needed fields are kept.
- **String date for simplicity:** Returns a ready-to-use date string, hiding timezone details and allowing future changes without affecting users.
- **Factory (get_message) to absorb provider quirks:** Construction centralizes decoding/validation, ensuring consistent objects regardless of source service.

### Implementation Details

#### Gmail Message

**Abstract contracts (`Client`)**

```python
# Abstract contracts with abc
from abc import ABC, abstractmethod

class Client(ABC):
    @abstractmethod
    def get_message(self, message_id: str): ...
    @abstractmethod
    def delete_message(self, message_id: str) -> bool: ...
```

- Defines the interface with `abc.ABC` and `@abstractmethod`, forcing subclasses to implement `get_message` and `delete_message`.
- Keeps the public API stable while letting concrete classes choose how to interact with providers.

**Concrete Gmail client (`GmailClient`)**

```python
# Concrete implementation with Google API
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class GmailClient(Client):
    def __init__(self):
        creds = Credentials.from_authorized_user_file("token.json")
        self.service = build("gmail", "v1", credentials=creds)
```

- `GmailClient` implements `Client` using Gmail; it loads `Credentials` and builds a Gmail `Resource` via `build`.
- Auth/session setup is hidden behind `GmailClient`, so callers only depend on the `Client` interface.

**Environment and token handling (`_auth_from_env`)**

```python
# Environment and token handling
import os
from pathlib import Path

def _auth_from_env():
    client_id = os.getenv("GMAIL_CLIENT_ID")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    # Returns Credentials if all values are present
```

- `_auth_from_env` reads `GMAIL_CLIENT_ID` and `GMAIL_REFRESH_TOKEN` (and related vars) from `os.environ` to construct/refresh `Credentials`.
- Supports CI and local development without changing how the `Client` is used.

**`Client.get_message` mapped to Gmail API**

```python
# Method implementation mapping interface to Gmail API
def get_message(self, message_id: str):
    msg_data = (
        self.service.users()
        .messages()
        .get(userId="me", id=message_id, format="raw")
        .execute()
    )
    return message.get_message(msg_id=message_id, raw_data=msg_data.get("raw"))
```

- `get_message` calls Gmail `.users().messages().get(..., format="raw")` and hands the `raw` payload to `message.get_message`.
- This returns a provider-agnostic `Message`, hiding Gmail response details from callers.

**Factory indirection (`get_client_impl`)**

```python
# Factory indirection for flexibility
def get_client_impl(*, interactive: bool = False) -> Client:
    return GmailClient(interactive=interactive)
```

- `get_client_impl` creates a configured `GmailClient`.
- This decouples construction/auth from usage, so switching providers or auth strategies doesn’t change the `Client` API.

---

#### Gmail Message

**Base64 decode and parse (`_parse_raw`)**

```python
# Base64 decode + stdlib email parsing
import base64, email
from email.message import Message as EmailMessage

def _parse_raw(raw_data: str) -> EmailMessage:
    decoded = base64.urlsafe_b64decode(raw_data.encode("utf-8"))
    return email.message_from_bytes(decoded)
```

- `_parse_raw` converts Gmail `raw` to bytes with `base64.urlsafe_b64decode` and parses it into an `EmailMessage` via `email.message_from_bytes`.
- This hides wire-format handling behind a simple helper.

**Defensive parsing (`_safe_parse`)**

```python
# Defensive parsing and fallbacks
def _safe_parse(raw_data: str) -> EmailMessage:
    try:
        msg = _parse_raw(raw_data)
        if not any(msg.keys()) and not msg.get_payload():
            raise ValueError("empty payload")
        return msg
    except Exception:
        m = EmailMessage()
        m["Subject"] = "Error Parsing Message"
        m["From"] = "Unknown Sender"
        m["To"] = "Unknown Recipient"
        m["Date"] = "Unknown Date"
        return m
```

- `_safe_parse` wraps `_parse_raw` and substitutes sentinel headers on failure.
- Ensures property accessors like `subject`/`from_` never crash callers.

**Subject decoding (`_decode_subject`)**

```python
# RFC 2047 subject decoding
import email.header

def _decode_subject(value: str) -> str:
    if '=?' not in value:
        return value
    parts = email.header.decode_header(value)
    out = []
    for chunk, enc in parts:
        out.append(chunk.decode(enc or "utf-8", errors="replace") if isinstance(chunk, bytes) else chunk)
    return "".join(out) or value
```

- `_decode_subject` uses `email.header.decode_header` to normalize RFC 2047-encoded subjects into Unicode.
- Hides charset quirks behind the `subject` property.

**Extract text body (`_extract_body`)**

```python
# Multipart traversal to extract text/plain body
TEXT_PLAIN = "text/plain"
ATTACHMENT = "attachment"
CONTENT_DISPOSITION = "Content-Disposition"

def _extract_body(msg: EmailMessage) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == TEXT_PLAIN and ATTACHMENT not in part.get(CONTENT_DISPOSITION, ""):
                payload = part.get_payload(decode=True)
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace") if isinstance(payload, bytes) else "[Non-bytes payload found in text/plain part]"
        return "[No plain text body found]"
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if isinstance(payload, bytes) else "[Non-bytes payload found]"
```

- `_extract_body` prefers inline `text/plain` parts (excluding `attachment`) and decodes bytes with the part’s charset or `utf-8`.
- Returns clear sentinel strings if the desired text content isn’t available.

**Date normalization (`_format_date`)**

```python
# Date normalization with graceful fallback
from email.utils import parsedate_to_datetime

DATE_FORMAT = "%m/%d/%Y"

def _format_date(raw: str) -> str:
    if not raw:
        return "Unknown Date"
    try:
        return parsedate_to_datetime(raw).strftime(DATE_FORMAT)
    except Exception:
        return raw  # keep original if unparseable
```

- `_format_date` converts header dates to `MM/DD/YYYY` using `parsedate_to_datetime`.
- Falls back to the original header when parsing fails, keeping the `date` property reliable.

**Detect binary garbage (`_is_binary_garbage`)**

```python
# Binary-garbage heuristic to detect non-email payloads
def _is_binary_garbage(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return False
    except UnicodeDecodeError:
        pass
    non_printable = sum(
        1 for b in data
        if (b < 32 and b not in (9, 10, 13)) or b > 126
    )
    return (non_printable / max(len(data), 1)) > 0.5
```

- `_is_binary_garbage` counts non-printable bytes to avoid treating random/binary blobs as valid emails.
- Improves robustness without exposing this heuristic to consumers.

**Message factory + registration (`GmailMessage`, `get_message_impl`, `register`)**

```python
# Message factory + registration indirection
from mail_client_api import message as msg_api

class GmailMessage(msg_api.Message):
    def __init__(self, msg_id: str, raw_data: str):
        parsed = _safe_parse(raw_data)
        self._id = msg_id
        self._parsed = parsed
        self._raw_data = raw_data
    # properties: id, from_, to, date, subject, body → using helpers above

def get_message_impl(msg_id: str, raw_data: str) -> msg_api.Message:
    return GmailMessage(msg_id=msg_id, raw_data=raw_data)

def register() -> None:
    msg_api.get_message = get_message_impl
```

- `GmailMessage` implements `msg_api.Message`; properties `id`, `from_`, `to`, `date`, `subject`, and `body` are backed by the helpers above.
- `get_message_impl` constructs `GmailMessage` and `register` assigns `msg_api.get_message = get_message_impl`, so callers use the stable `message.get_message` factory.

## Dependency Injection

#### Gmail

**Code: Client factory injection (`gmail_impl.py`)**

```python
def register() -> None:
    """Register the Gmail client implementation with the mail client API."""
    mail_client_api.get_client = get_client_impl
```

- Replaces the abstract factory `mail_client_api.get_client` with the concrete `get_client_impl`
- After this assignment, any call to `get_client(...)` returns a configured `GmailClient`

**Code: Usage pattern (Gmail client)**

```python
import gmail_client_impl  # Triggers DI registration at import

from mail_client_api import get_client  # Abstract factory name
client = get_client(interactive=False)  # Returns a concrete GmailClient instance
```

- Importing `gmail_client_impl` performs registration
- The abstract `get_client` now returns a `GmailClient` thanks to the runtime binding

---

#### Message

**Code: Message factory injection (`message_impl.py`)**

```python
def register() -> None:
    """Register the Gmail message implementation with the message abstraction."""
    message.get_message = get_message_impl
    mail_client_api.get_message = get_message_impl
```

- Binds both `message.get_message` and `mail_client_api.get_message` to the concrete `get_message_impl`
- Ensures callers receive a `GmailMessage` via the stable factory API

**Code: Usage pattern (Message factory)**

```python
import gmail_client_impl  # Triggers DI registration at import

from mail_client_api import get_message  # Abstract factory name
msg = get_message(msg_id="123", raw_data="...")  # Returns a concrete GmailMessage instance
```

- Import-time registration wires the abstract `get_message` to `get_message_impl`
- Callers stay provider-agnostic and receive a `GmailMessage`

### Abstract Factory Definitions (Interface Layer)

**Code: Abstract client factory (`mail_client_api/client.py`)**

```python
def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of a Mail Client."""
    raise NotImplementedError
```

- `get_client` is the abstract entry point; it raises `NotImplementedError` until a provider registers
- Implementations overwrite this symbol at import time via `register()`

**Code: Abstract message factory (`mail_client_api/message.py`)**

```python
def get_message(msg_id: str, raw_data: str) -> Message:
    """Return an instance of a Message.

    Args:
        msg_id (str): The unique identifier for the message.
        raw_data (str): The raw data used to construct the message.

    Returns:
        Message: An instance conforming to the Message contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.
    """
    raise NotImplementedError
```

- `get_message` is the abstract constructor for `Message` objects
- Providers replace it with a bound implementation (e.g., `get_message_impl`) during `register()`

## Where Both Get Injected (Import-Time Registration)

**Code: Primary injection point (`gmail_client_impl/__init__.py`)**

```python
def register() -> None:
    """Register the Gmail client and message implementations."""
    _register_client()
    _register_message()

# Dependency Injection happens at import time
register()
```

- Importing the package calls `register()`, which triggers `_register_client()` and `_register_message()`
- This performs runtime binding so calls to the abstract factories resolve to the Gmail implementations after import

### How It Works (at a glance)

- **Before import:** The abstract factories `get_client` and `get_message` intentionally raise `NotImplementedError`
- **During import:** `import gmail_client_impl` triggers `register()`, which assigns concrete functions to the abstract names
- **After binding:** Calls to `get_client(...)` and `get_message(...)` use the concrete Gmail implementations without callers knowing the provider

### What this pattern enables (for contributors)

- Swap or add providers by implementing `register()` and wiring `get_client` / `get_message`—no API changes required
- Test wiring independently of credentials by asserting factory return types after import-time registration
- Evolve implementations behind stable interfaces, minimizing change amplification for downstream users

## Repository Structure

### Project Organization

- <h3>Directory Tree</h3>

```
.
├─ src/
│  ├─ mail_client_api/        # Interface/contract (ABCs)
│  └─ gmail_client_impl/      # Gmail implementation of the interface
├─ tests/
│  ├─ integration/            # Component integration tests
│  └─ e2e/                    # End-to-end tests
├─ docs/                      # MkDocs documentation source
├─ .circleci/                 # CI pipeline configuration
├─ main.py                    # Demo entry point
├─ pyproject.toml             # Tooling & dependency metadata
├─ uv.lock                    # Reproducible dependency lockfile
├─ mkdocs.yml                 # Docs site config
├─ .env.example               # Sample environment variables
├─ .gitignore
├─ .python-version
└─ README.md

```

The src/ folder holds the app code as a uv workspace with two parts: mail_client_api/, which defines the mail-client interface (the contract), and gmail_client_impl/, a concrete Gmail implementation of that interface. Tests live in tests/, split into integration/ for component checks and e2e/ for full end-to-end runs. Project docs are in docs/ and built with MkDocs, and CI is configured in .circleci/. At the root, main.py is a small entry point you can run to demo the auth/run flow; pyproject.toml declares tooling and dependencies; uv.lock pins versions for reproducible installs; and mkdocs.yml configures the docs site. You’ll also find .env.example for local environment variables plus the usual housekeeping: .gitignore, .python-version, and a README.md that explains setup and architecture.

### Configuration Files

- **Role of root `pyproject.toml`:**

  • Workspace & Python: Marks the repo as a uv workspace and sets the global Python/runtime setup

  • Shared tooling: One place to configure Ruff, Mypy, Pytest, MkDocs, etc., so every package follows the same rules.

  • Deps: Lists common runtime/dev/test/docs dependencies. Exact versions get locked in uv.lock for reproducible installs.

  • Tasks/scripts (if any): Handy commands so everyone runs the app, tests, and docs the same way.

- **Role of component-level `pyproject.toml`**

  • Package identity: Name, Verison, Description, and packaging info so each part can be built/installed on its own

  • Scoped dependencies: Only what that specific package needs (e.g., gmail_client_impl depends on mail_client_api and Gmail stuff; the API package stays super light).

  • Build settings: What code gets included, supported Python versions, and how it’s packaged.

  • Optional tool tweaks: Per-package lint/typing overrides if a component needs stricter/different rules.

**In short:
The root standardizes tooling and shared deps for the whole workspace, while each component pyproject.toml defines that package’s own metadata and minimal, package-specific requirements.**

### Package Structure

- \***\*init**.py exists in:**
  • src/mail_client_api/**init**.py
  • src/gmail_client_impl/**init\*\*.py
  These files mark each directory as a Python package so imports like import mail_client_api and import gmail_client_impl work. They’re also the place to define the public API surface by re-exporting the symbols users should import from the top level.

- **Meaning of “keeping `__init__.py` slim”**
  • Light re-exports of key classes/func
  • Simple metadata of brief package docs
  • No heavy work at important time: avoid I/O, network calls, environment loading, starting threads, or pulling in large optional deps
  Importance of “slim”:
  • Faster imports and test startup.
  • Fewer circular-import issues.
  • Clear, stable top-level API for users.

- **Contributers** should follow the “slim **init**.py” convention because it put real logic in module files and only re-export what consumers should use from the package root.

### Import Guidelines

- **Purpose:** Provide import conventions.
- **What to include:**
  - Absolute vs. relative imports
  - Examples of preferred style

## Testing Strategy

### 1. General Testing Principles

**Testing Approach:**

- **Method**: Testing should be conducted throughout the entire process, with unit/integration tests introduced early on.
- **Requirements**: Tests should be automatable, repeatable, and run relatively quickly to facilitate reproducibility and help deliver projects as soon as possible.
- **Quality Standards**: Good tests should have consistent results.

### 2. Test Directory Structure and Execution

**Testing Approach:**

- **Location**: All unit tests are located under the `src/` directory.
- **Execution**: Can be run using the command `uv run pytest src/`.
- **Structure**: The main `tests/` directory contains both integration and end-to-end (e2e) tests, specifically under `tests/integration/` and `tests/e2e/` respectively.
- **Design**: The absence of an `__init__.py` file in the `tests/` directory signifies that the test directory is not an import package. This design can reduce path conflicts and unintended dependencies, leading to better test execution consistency.

### 3. Abstraction Levels for Different Test Types

**Testing Approach:**

- **Unit Tests**: The abstraction level for unit tests is the smallest boundary, like a class (an abstract class in `client.py` in `mail_client_api`), a method, or a function. Unit tests ensure that the smallest parts are working well.
- **Integration Tests**: Integration tests cover the interaction between different components. For example, verifying if an API call like "delete email" can correctly delete an email from an external email service like Gmail.
- **E2E Tests**: An E2E test's abstraction level encompasses the full workflow from a user's perspective, such as OAuth authentication combined with real delete/get/post operations. While integration tests may use mock data, E2E tests utilize real environments and data.

### 4. Test Coverage Measurement

**Testing Approach:**

- **Tools**: Test coverage is measured using `pytest` and `pytest-cov`, as configured in `pyproject.toml`.
- **Thresholds**: The minimum acceptable coverage threshold is 85%, also specified in `pyproject.toml`.
- **Command**: To run all tests with coverage and generate an HTML report, use the command: `uv run pytest --cov=src --cov-report=html`.

### Testing Philosophy

- **Purpose:** Communicate the testing mindset.
- **What to include:**
  - Core principles from Prof. Nikolai’s lecture
  - Quality and maintainability goals

### Test Organization

- **Purpose:** Explain where tests live.
- **What to include:**
  - Structure for unit, integration, and E2E tests
  - Conventions for `__init__.py` in test directories

### Test Abstraction Levels

- **Purpose:** Clarify what each level of test focuses on.
- **What to include:**
  - Unit: low-level, function/class
  - Integration: multi-component interaction
  - E2E: full system validation

### Code Coverage

- **Purpose:** Document testing standards.
- **What to include:**
  - Coverage tool used (e.g., `coverage.py`)
  - Minimum thresholds
  - Commands to run tests and generate reports

## Development Tools

### Workspace Management

- **Workspace management (uv):**
  The repo is a single uv workspace that groups the packages under src/ (e.g., mail_client_api, gmail_client_impl) so they share one environment, lockfile, and tooling.
- **Essential uv commands:**
  • uv sync – create/refresh the workspace venv and install deps.
  • uv run python main.py – run the demo/entry point.
  • uv run pytest – run tests.
  • uv add <pkg> / uv add --dev <pkg> – add runtime or dev deps.
  • uv lock – (re)generate uv.lock.
  • uv tree – show the resolved dependency graph.
- **pyproject.toml roles (root vs component):**
  • Root pyproject.toml: declares the uv workspace, sets global Python/tooling (Ruff, Mypy, Pytest, MkDocs), and defines shared deps that are pinned in uv.lock.
  • Component pyproject.toml (if present): holds that package’s own metadata and minimal, package-specific deps so it can be built/installed independently.
  • This repo today: config is centralized at the root; there aren’t per-component pyproject.toml files.

### Static Analysis and Code Formatting

- **Tools used**
  • Ruff — linting + formatting (configured in pyproject.toml).
  • Mypy — static type checking (configured in pyproject.toml).
- **How to run**

  **Lint (report issues):**

  ```shell
    uv run ruff check .
  ```

  **Auto-format:**

  ```shell
  uv run ruff format
  ```

  **Format check (CI-style, no changes written):**

  ```shell
  uv run ruff format --check
  ```

  **Type check:**

  ```shell
  uv run mypy .
  ```

- **Why it matters here**

  - Keeps a consistent code style across mail_client_api and gmail_client_impl.

  - Catches bugs early (unused imports, dead code, type mismatches).

  - Speeds up reviews and reduces “style-only” churn in PRs.

  - Makes the public API contracts (interfaces) safer to evolve.

- **uv integration**

  - Integrated via pyproject.toml and run through uv run … so they use the workspace environment and lockfile.

  - They can run in CI (via .circleci/) the same way, but they’re not special uv plugins—just standard tools executed with uv.

### Documentation Generation

- Tool: [MkDocs] (configured by mkdocs.yml, sources in docs/).

- Live preview:

```shell

  uv sync

  uv run mkdocs serve

  # Then open the local URL printed in the terminal.
```

- Build static site:

```shell

  uv run mkdocs build

  # Output goes to site.
```

- Edit docs: add/modify Markdown files under docs/; navigation and theme are managed in mkdocs.yml.

### CI

- Jobs

  - setup – checks out the repo, restores cache, runs uv sync to build the workspace env.
  - lint – runs Ruff (uv run ruff check . and/or uv run ruff format --check .).
  - typecheck – runs MyPy (uv run mypy src tests).
  - test – runs the test suite with Pytest (uv run pytest), typically with cache for .venv/uv and test artifacts.
  - docs – builds the docs to ensure MkDocs config is valid (uv run mkdocs build).

- Triggers
  - On push to any branch (validates commits before merging).
  - On pull requests (runs the full workflow for gated reviews).
  - Manual reruns from CircleCI UI when needed (e.g., after flaky failures).
  - (If tags/schedules are added, they would build on tag push or a cron schedule; otherwise the above are the defaults.)

---

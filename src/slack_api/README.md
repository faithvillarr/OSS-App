# slack_api

A clean, typed **contract package** defining the public interfaces and models for a Slack‑like chat service used across this project.  
This package is intentionally dependency‑free (no HTTP, no env access) and ships with validators and utilities to enable rich **offline unit tests**.

---

## Why this package exists

Other components (like `slack_impl`, `slack_service`, and `slack_adapter`) import contracts from **`slack_api`** to stay decoupled:
- `ChatClient` protocol — the surface that concrete clients/adapters must satisfy.
- Lightweight models — `Channel`, `User`, `Message` — with validation and round‑trip helpers.
- Robust validators and small utilities (`sanitize_text`, `utc_ts`) to make tests deterministic and pure.

This separation keeps higher‑level packages swappable and easy to test.

---

## Public API

```python
from slack_api import (
    ChatClient,
    Channel,
    User,
    Message,
    ValidationError,
    InvalidIdError,
    sanitize_text,
    utc_ts,
    is_valid_channel_id,
    is_valid_user_id,
    is_non_empty_text,
    require_channel_id,
    require_user_id,
    require_text,
)
```

**Contract methods (Protocol):**
- `health() -> bool`
- `list_channels() -> Iterable[Channel]`
- `post_message(channel_id: str, text: str) -> Message`

---

## Package layout

```
src/slack_api/
  pyproject.toml
  README.md
  src/slack_api/
    __init__.py
    client.py            # ChatClient Protocol
    types.py             # Channel, User, Message (dataclasses)
    validators.py        # id/text validators (pure, tested)
    utils.py             # sanitize_text, utc_ts
    errors.py            # ValidationError, InvalidIdError
    token_store.py       # TokenStore Protocol (abstract only)
    py.typed             # PEP 561 type marker
  tests/
    ...
```

This package follows a **src‑layout** and is **PEP 561 typed** (ships `py.typed`).

---

## Installation (editable, from monorepo root)

> Use the same Python/venv as HW1/HW2 (Python 3.12.x).

```bash
python -m pip install -e src/slack_api
```

If you need only the package itself (outside the monorepo), ensure you keep the same src‑layout:
- `pyproject.toml` declares `package-dir = {"" = "src"}`
- `py.typed` is included via `package-data`

---

## Development commands

From repo root (with your HW1/HW2 venv activated):

```bash
# Lint & format (no config changes needed)
python -m ruff check --fix src/slack_api
python -m ruff check src/slack_api

# Type check
python -m mypy src/slack_api

# Run tests
python -m pytest -q src/slack_api/tests
```

---

## Versioning

- Start with `0.1.0` in `pyproject.toml` (or `setup.py` if you prefer).
- Bump minor/patch versions when changing contracts or adding validators.
- Keep imports stable at the package root (`slack_api.__init__`) to avoid breaking dependents.

---

## Design notes

- **Pure & offline:** No network calls, filesystem, or env reads.
- **Protocol over ABC:** `ChatClient` is a `Protocol` so any object with the required methods is accepted; this improves testability and decoupling.
- **Validation at boundaries:** `from_dict` enforces id/text shape; `to_dict` is lossless.
- **Type fidelity:** `py.typed` is shipped; mypy is strict‑friendly (no `Any` leaks).

---

## License

MIT (or your course’s default). Update this field to match your repository’s license.
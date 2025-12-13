from __future__ import annotations

import pytest

from slack_api import (
    is_valid_channel_id,
    is_valid_user_id,
    is_non_empty_text,
    require_channel_id,
    require_user_id,
    require_text,
    InvalidIdError,
    ValidationError,
)


def test_id_validators() -> None:
    assert is_valid_channel_id("C12")
    assert is_valid_channel_id("C0AZ9")
    assert not is_valid_channel_id("general")
    assert not is_valid_channel_id("U123")

    assert is_valid_user_id("U12")
    assert is_valid_user_id("U0AZ9")
    assert not is_valid_user_id("user123")
    assert not is_valid_user_id("C123")


def test_require_helpers() -> None:
    assert require_channel_id("C123") == "C123"
    with pytest.raises(InvalidIdError):
        require_channel_id("general")

    assert require_user_id("U999") == "U999"
    with pytest.raises(InvalidIdError):
        require_user_id("user999")

    assert require_text("  hello   world  ", max_len=100) == "hello world"
    with pytest.raises(ValidationError):
        require_text(" \n\t  ")
    # Truncation enforced
    assert len(require_text("a" * 5000, max_len=50)) == 50


def test_is_non_empty_text() -> None:
    assert is_non_empty_text("  ok ")
    assert not is_non_empty_text(" \n\t ")

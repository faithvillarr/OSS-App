"""Tests for OpenAI implementation."""

import os
from unittest.mock import patch

import ai_api
import pytest
from ai_api import AIInterface

import openai_impl
from openai_impl.openai_impl import OpenAIClient


def _fake_choice(content: str = "ok") -> object:
    return type("Choice", (), {"message": type("Msg", (), {"content": content})()})


def _fake_response(content: str = "ok") -> object:
    return type("Resp", (), {"choices": [_fake_choice(content)]})()


class _FakeCompletions:
    def create(self, *args: object, **kwargs: object) -> object:
        return _fake_response()


class _FakeOpenAI:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions()})()


def test_register_sets_get_client() -> None:
    """Register wires ai_api.get_client to return OpenAIClient."""
    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": "test"}),
        patch("openai_impl.openai_impl.OpenAI", _FakeOpenAI),
    ):
        openai_impl.register()
        client = ai_api.get_client()
        assert isinstance(client, AIInterface)
        assert client.generate_response("hi", "be short") == "ok"


def test_missing_api_key_raises() -> None:
    """Initialization fails when no API key is provided."""
    with patch.dict(os.environ, {}, clear=True), pytest.raises(RuntimeError) as exc:
        openai_impl.OpenAIClient()  # type: ignore[arg-type]
    assert "OpenAI API key" in str(exc.value)


def test_generate_response_conversational_path() -> None:
    """Generate_response returns content for conversational path."""
    fake_resp = _fake_response("hello!")
    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": "k"}),
        patch(
            "openai_impl.openai_impl.OpenAI",
        ) as mock_openai,
    ):
        mock_openai.return_value.chat.completions.create.return_value = fake_resp
        client = OpenAIClient()
        assert client.generate_response("hi", "be short") == "hello!"


def test_generate_response_schema_path() -> None:
    """Generate_response returns parsed JSON when schema is provided."""
    fake_resp = _fake_response('{"a": 1}')
    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": "k"}),
        patch(
            "openai_impl.openai_impl.OpenAI",
        ) as mock_openai,
    ):
        mock_openai.return_value.chat.completions.create.return_value = fake_resp
        client = OpenAIClient()
        assert client.generate_response("hi", "be json", {"type": "object"}) == {"a": 1}
